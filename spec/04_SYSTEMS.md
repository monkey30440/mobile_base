# System Architecture

本文件定義 `mobile_base` 目前之系統層級架構，包含系統邊界、操作模式、Implementation Area 責任、跨系統資料流與控制鏈、動態 TF 權限契約，以及全系統核心架構規範。

---

## 1. Purpose and Authority

### 1.1 上游產品需求基準 (Normative Product Inputs)
本架構文件嚴格以下列規範性文件為 **唯一 Normative Product Inputs**：
- [`spec/01_USE_CASES.md`](./01_USE_CASES.md)
- [`spec/02_CAPABILITIES.md`](./02_CAPABILITIES.md)
- [`spec/03_REQUIREMENTS.md`](./03_REQUIREMENTS.md)

本架構為 `mobile_base` 目前 as-built 系統架構的**單一權威來源 (Single Canonical Authority)**。

### 1.2 下游實作關係 (Downstream Implementation Authority)
本文件統籌定義全系統與子系統層級之架構責任與介面邊界，各子系統內部實作與配置以現行原始碼（`src/*`）、Launch 檔與參數 YAML 為準。

### 1.3 架構職權範圍 (Architecture Authority Boundaries)

| 系統架構（spec/04_SYSTEMS.md）決定 | 不應由架構決定（保留至 Source / Config / Verification） |
|---|---|
| Implementation Areas 的責任與介面邊界 | Class / Struct / Function 內部程式碼實作細節 |
| 跨子系統之資料流、控制流與生命週期依賴關係 | Launch 檔與 YAML 配置之細部數值與調校表格 |
| 座標框架 TF Tree 的唯一動態與靜態發布權限契約 | 驅動程式內部暫存器編號與 Modbus 封包細部編解碼 |
| 速度命令鏈（Command Chain）與多層停止安全架構 | 操作命令指南、開發日誌與除錯記錄 |
| Route-assisted 導航編排與 Station 導航架構 | 測試案例執行記錄、細部除錯記錄與暫態調校數據 |
| 場域資源（Map / Route Graph / Station Catalog）所有權與解析界線 | 導航演算法細部超參數調校與推測性根本原因分析 |

---

## 2. System Context

`mobile_base` 為基於 ROS 2 Jazzy 開發的自主移動機器人（AMR）底盤系統。系統邊界涵蓋 10 個 Implementation Areas 及其運行的軟體責任。

### 2.1 外部實體 (External Entities)
- **使用者 / 操作員 (Operator / User)**：提交建圖與儲存命令、操作鍵盤手動移動巡覽（透過外部 `teleop_twist_keyboard`）、提交導航目標（Station ID 或 Goal Pose）或發出取消請求。
- **實體感測器 (Physical Sensors)**：
  - 前左（Front-Left）與後右（Rear-Right）雙 SICK picoScan150 2D 激光雷達。
  - TDK IIM-42652 6 軸慣性測量單元（IMU）。
- **底盤動力硬體 (M1 Drive Hardware & Motors)**：
  - M1 雙驅動器差速動力總成，透過 RS-485 Modbus RTU 接收輪速控制命令並回傳實體編碼器量測狀態。
- **場域資源資料夾 (Site Artifacts)**：
  - 存放於 `maps/<site_name>/` 之二維佔據網格地圖（`map.pgm`, `map.yaml`）、路網圖（`route_graph.geojson`）與站點目錄（`stations.yaml`）。
- **Observability Server**：位於 AMR 外部，接收並保存 Logs / Events 與 Key Telemetry，提供歷史時間範圍與來源查詢；不參與 Navigation、Localization、Control 或 Safety 執行路徑。

### 2.2 系統脈絡圖 (System Context Diagram)

```text
       使用者 / 上層客戶端 (Operator / User)
          │                    │                     │
          │ 提交導航目標 / 取消 │ 啟動建圖 / 儲存      │ 操作鍵盤遙控 (Teleop)
          ▼                    ▼                     ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                        mobile_base                          │
    │                                                             │
    │  ┌────────────────┐      ┌────────────────┐                 │
    │  │ Robot Model    │      │Sensor Ingestion│◄─┼── 實體感測器 (LiDAR / IMU)
    │  └───────┬────────┘      └───────┬────────┘  │              │
    │          │                       │           │              │
    │          ▼                       ▼           │              │
    │  ┌────────────────┐      ┌────────────────┐  │              │
    │  │ Mapping        │      │State Estimation│  │              │
    │  └───────┬────────┘      └───────┬────────┘  │              │
    │          │                       │           │              │
    │          ▼ (Map Package)         ▼           │              │
    │  ┌────────────────┐      ┌────────────────┐  │              │
    │  │ Localization   │─────►│ Navigation Areas│  │              │
    │  └────────────────┘      └───────┬────────┘  │              │
    │                                  │           │              │
    │                                  ▼           │              │
    │                          ┌────────────────┐  │              │
    │                          │ Base Control   │◄─┴──────────────┘ (手動 TwistStamped)
    │                          └───────┬────────┘
    │                                  │
    │                                  ▼
    │                                  底盤動力硬體 (M1 Motors)
    │                                                             │
    │  Implementation Areas Runtime Information / Logs / Events ──► Observability
    └─────────────────────────────────────────────────────────────┘
                        ▲
                        │ 載入 Map Package / Route Graph / Station Catalog
           ┌────────────┴───────────┐
           │ 場域資源 (Site Artifacts)│
           └────────────────────────┘

    Observability ── Logs / Events / Key Telemetry ──► Observability Server
```

---

## 3. Operational Modes

`mobile_base` 目前定義兩種**嚴格互斥 (Mutually Exclusive)** 的系統操作模式：

```text
Shared Areas: Robot Model / Sensor Ingestion / State Estimation / Base Control
        │
        ├── Mapping Mode: Mapping + Teleop
        │                 Mapping owns map → odom
        │
        └── Navigation Mode: Localization + Navigation Target Admission
                             + Route-Assisted Navigation + Precision Docking
                             Localization owns map → odom
```

Observability 為兩種模式共用、與核心功能隔離的觀察旁路；其啟動、停止或故障不改變 Mapping Mode 或 Navigation Mode 的成立條件。

### 3.1 Mapping Mode
- **目的**：巡覽未知環境，即時建立二維佔據網格地圖，並持久化儲存為 Map Package。
- **活躍區域**：Robot Model、Sensor Ingestion、State Estimation、Mapping、Base Control。
- **運動控制輸入**：操作員透過外部 `teleop_twist_keyboard` 發布手動速度命令（`geometry_msgs/msg/TwistStamped`）直接至 Base Control（`/diff_drive_controller/cmd_vel`）。未操作或命令停止時底盤停等，建圖程序維持運行。
- **動態 TF 權限**：由 Mapping 的 `slam_toolbox` 動態發布 `map -> odom` TF；由 State Estimation 的 `robot_localization` EKF 動態發布 `odom -> base_footprint` TF。
- **互斥邊界**：Localization、Navigation Target Admission、Route-Assisted Navigation 與 Precision Docking **嚴格禁止啟動**。全系統僅存在單一手動運動命令源，不引入 `twist_mux` 或額外模式仲裁節點。

### 3.2 Navigation Mode
- **目的**：載入已建置地圖與路網資源，依據使用者提交之 Station 或 Goal Pose 目標執行三階段自主導航，或透過視覺標記執行 AprilTag Direct Docking。
- **活躍區域**：Robot Model、Sensor Ingestion、State Estimation、Localization（包含 `map_server` 地圖載入與 `amcl` 定位）、Navigation Target Admission、Route-Assisted Navigation、Precision Docking、Base Control。Mapping 處於非活躍狀態（Inactive）。
- **運動控制輸入**：由 Route-Assisted Navigation 的 `controller_server` 或 Precision Docking 的 `docking_server` 運算自主軌跡，依任務狀態互斥輸出至 Base Control（`/diff_drive_controller/cmd_vel`）。
- **動態 TF 權限**：由 Localization 的 `nav2_amcl` 唯一發布 `map -> odom` TF；由 State Estimation 的 `robot_localization` EKF 唯一發布 `odom -> base_footprint` TF。
- **互斥邊界**：Mapping 的 `slam_toolbox` 建圖節點與外部 `teleop_twist_keyboard` **嚴格禁止啟動**。

---

## 1. Robot Model

### Responsibility

Robot Model 負責提供 AMR 的車體幾何、感測器安裝外參、關節結構與輪端運動學配置，並透過 `robot_state_publisher` 將機器人模型描述（`robot_description`）載入系統，同時發布機器人本體之靜態座標轉換與隨關節狀態更新的動態輪端座標轉換。

### Interfaces and Flow

```text
mobile_base.urdf.xacro (URDF/Xacro)
       │
       ▼ (xacro command parsing)
/robot_description (Topic & Node Parameter)
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
robot_state_publisher                     ros2_control (controller_manager)
       │                                         │
       │                                         ▼ (讀取硬體狀態並發布)
       │◄──────── /joint_states ─────────────────┘ (sensor_msgs/msg/JointState)
       │
       ├──► /tf_static (tf2_msgs/msg/TFMessage, Latched)
       │    ├── base_footprint -> base_link
       │    ├── base_link -> base_lidar_link_FL -> base_lidar_link_FL_1
       │    ├── base_link -> base_lidar_link_BR -> base_lidar_link_BR_1
       │    └── base_link -> base_imu_link
       │
       └──► /tf (tf2_msgs/msg/TFMessage, Dynamic)
            ├── base_link -> driving_wheel_link_L
            └── base_link -> driving_wheel_link_R
```

- **模型載入與發布**：在底盤啟動程序中，`robot_description.launch.py` 調用 `xacro` 解析 `mobile_base.urdf.xacro`，產出 URDF XML 字串並作為節點參數與 `/robot_description` 主題提供給系統。
- **靜態幾何發布**：`robot_state_publisher` 根據 URDF 定義，透過 `/tf_static` 一次性廣播底盤本體、感測器安裝位置與光達掃描參考框架之靜態座標轉換。
- **動態關節轉換**：`robot_state_publisher` 訂閱來自 Base Control（`joint_state_broadcaster`）發布的 `/joint_states`，依據目前左右輪位置，計算並於 `/tf` 發布隨關節狀態更新之左右驅動輪動態變換（目前實作配置為 30 Hz）。
- **TF 所有權邊界**：Robot Model 與 `robot_state_publisher` 僅負責 `base_footprint` 以下的機器人本體 link/joint TF。`robot_state_publisher` 不發布、亦不擁有世界座標到機器人本體的動態座標轉換（如 `odom -> base_footprint` 或 `map -> odom`）。

### Implementation

1. **核心模型與執行元件**：
   - **Xacro / URDF Entrypoint**：`src/mobile_base_description/urdf/mobile_base.urdf.xacro`
     - 幾何定義：`src/mobile_base_description/urdf/mobile_base_geometry.xacro`
     - 傳動介面：`src/mobile_base_description/urdf/mobile_base_ros2_control.xacro`
   - **發布節點**：`robot_state_publisher`（標準 ROS 2 套件），由 `src/mobile_base_description/launch/robot_description.launch.py` 啟動，套用配置檔 `src/mobile_base_description/config/robot_state_publisher.yaml`（`publish_frequency: 30.0`）。

2. **核心幾何與輪端配置**：
   - **底盤參考與本體關係**：
     - 地面投影參考點為 `base_footprint`（REP-120），底盤本體 `base_link` 透過固定關節 `base_joint` 連結於其上方。
   - **差速驅動輪運動學參數**：
     - 輪半徑（`wheel_radius`）：`0.0800 m`。
     - 輪距（`wheel_separation`）：`0.5545 m`。
     - 左右輪關節：`driving_wheel_joint_L` 與 `driving_wheel_joint_R`（連續旋轉關節），分別連結左輪 `driving_wheel_link_L` 與右輪 `driving_wheel_link_R`，提供差速運動學計算與動態姿態呈現。
   - 精確幾何尺寸與詳細安裝外參數值以 `src/mobile_base_description/urdf/mobile_base_geometry.xacro` 為權威來源。

3. **感測器安裝框架與倒置補償**：
   - **前左 2D LiDAR（SICK picoScan150）**：
     - 機構安裝框架：`base_lidar_link_FL`（透過固定關節 `base_lidar_joint_FL` 掛載於 `base_link`，為倒置安裝）。
     - 修正掃描框架：`base_lidar_link_FL_1`（透過固定關節 `base_lidar_joint_FL_1` 連結於 `base_lidar_link_FL`）。此 scan frame 藉由旋轉變換抵消實體機構倒置的 roll 角度，向 ROS 感測串流與下游演算法提供 Z 軸朝上（z-up）、水平順向的標準二維掃描參考基準。
   - **後右 2D LiDAR（SICK picoScan150）**：
     - 機構安裝框架：`base_lidar_link_BR`（透過固定關節 `base_lidar_joint_BR` 掛載於 `base_link`，為倒置安裝）。
     - 修正掃描框架：`base_lidar_link_BR_1`（透過固定關節 `base_lidar_joint_BR_1` 連結於 `base_lidar_link_BR`），同樣抵消倒置 roll 角度以提供 Z 軸朝上之標準掃描參考基準。
   - **慣性測量單元（TDK IIM-42652 IMU）**：
     - 安裝框架：`base_imu_link`（透過固定關節 `base_imu_joint` 掛載於 `base_link`）。

4. **啟動流程與關節狀態串聯**：
   - 在 canonical bringup（`src/mobile_base_bringup/launch/mobile_base.launch.py`）中，啟動時透過 `base_control.launch.py` 啟動 `robot_description.launch.py`。
   - `robot_state_publisher` 節點啟動後訂閱 `/joint_states` 主題。
   - 當 `ros2_control` 之 `controller_manager` 載入並激活 `joint_state_broadcaster` 後，自底盤馬達回授發布左右輪的實際關節狀態（`driving_wheel_joint_L`、`driving_wheel_joint_R`），由 `robot_state_publisher` 換算為輪端動態 TF。

### Expected Normal Behavior

- 啟動完成後，系統提供 `/robot_description` 主題與節點參數供其他子系統讀取使用。
- `/tf_static` 發布包含 `base_footprint -> base_link`、雙光達機構與 scan 框架、以及 IMU 框架之靜態幾何關係，且在整個生命週期中穩定可查。
- 輪端動態座標轉換（`base_link -> driving_wheel_link_L` 與 `base_link -> driving_wheel_link_R`）隨 `/joint_states` 持續更新並發布於 `/tf`。
- Robot Model 僅負責 `base_footprint` 以下的機器人本體 link/joint 座標轉換；`odom -> base_footprint` 與 `map -> odom` 不屬於 Robot Model，不與 State Estimation（EKF）或 Localization（AMCL / SLAM Toolbox）的動態 TF 權限發生衝突。

### Implementation References

- URDF Entrypoint: `src/mobile_base_description/urdf/mobile_base.urdf.xacro`
- Geometry Definition: `src/mobile_base_description/urdf/mobile_base_geometry.xacro`
- ros2_control Hardware Tag: `src/mobile_base_description/urdf/mobile_base_ros2_control.xacro`
- Description Launch: `src/mobile_base_description/launch/robot_description.launch.py`
- Description Config: `src/mobile_base_description/config/robot_state_publisher.yaml`
- Base Control Launch (Integration): `src/mobile_base_control/launch/base_control.launch.py`
- Base Control Config: `src/mobile_base_control/config/base_control_params.yaml`
- Canonical Bringup Launch: `src/mobile_base_bringup/launch/mobile_base.launch.py`

## 2. Sensor Ingestion

### Responsibility

Sensor Ingestion 負責自實體感測器硬體（雙 2D 激光雷達與 6 軸 IMU）讀取原始觀測量，透過對應之硬體驅動程式發布為標準 ROS 2 感測主題（`/scan_front`、`/scan_rear` 與 `/imu/data_raw`），供下游狀態估測、建圖、定位與導航等子系統消耗。

### Interfaces and Flow

```text
Physical Front LiDAR (SICK picoScan150)
       │ (Ethernet / UDP)
       ▼
front_lidar_node (sick_scan_xd)
       │
       ▼
/scan_front (sensor_msgs/msg/LaserScan, frame_id: base_lidar_link_FL_1)
       ├──► State Estimation
       ├──► Mapping
       ├──► Localization
       └──► Navigation

Physical Rear LiDAR (SICK picoScan150)
       │ (Ethernet / UDP)
       ▼
rear_lidar_node (sick_scan_xd)
       │
       ▼
/scan_rear (sensor_msgs/msg/LaserScan, frame_id: base_lidar_link_BR_1)
       └──► Navigation

Physical IMU (TDK IIM-42652)
       │ (USB Serial)
       ▼
imu_driver_node (tdk_ros2_imu)
       │
       ▼
/imu/data_raw (sensor_msgs/msg/Imu, frame_id: base_imu_link)
       └──► State Estimation
```

- **雙光達獨立資料流**：前左與後右光達分別由獨立的驅動節點讀取並發布至 `/scan_front` 與 `/scan_rear`。生產環境中不存在虛擬雷達合併節點（`dual_laser_merger`），亦無全域合併主題（`/scan`）；下游消費者直接依需求訂閱所需之雷達主題。
- **感測框架參照**：發布之感測訊息分別標註對應之 `frame_id`（`base_lidar_link_FL_1`、`base_lidar_link_BR_1`、`base_imu_link`），其空間安裝外參與靜態 TF 轉換由 Robot Model 負責發布，Sensor Ingestion 本身不發布 TF。
- **下游資料流邊界**：
  - `/scan_front` 由 State Estimation、Mapping、Localization 與 Navigation 訂閱。
  - `/scan_rear` 由 Navigation 訂閱。
  - `/imu/data_raw` 由 State Estimation 訂閱。

### Implementation

1. **雙 2D 光達驅動（Dual SICK picoScan150）**：
   - **套件與節點**：使用 `sick_scan_xd` 套件之 `sick_generic_caller`，於 Launch 檔具現化兩個獨立節點：
     - 前左光達：節點名稱 `front_lidar_node`，經 Ethernet / UDP 接收資料，輸出主題為 `/scan_front`（`sensor_msgs/msg/LaserScan`）。
     - 後右光達：節點名稱 `rear_lidar_node`，經 Ethernet / UDP 接收資料，輸出主題為 `/scan_rear`（`sensor_msgs/msg/LaserScan`）。
   - **Frame 命名與發布行為**：
     - Launch 引數 `publish_frame_id` 分別配置為 `base_lidar_link_FL` 與 `base_lidar_link_BR`。
     - 驅動程式內部依圖層索引發布 `header.frame_id` 為 `base_lidar_link_FL_1` 與 `base_lidar_link_BR_1`，直接對齊 Robot Model 定義之 Z 軸朝上校正掃描框架。
   - **TF 權限配置**：
     - 驅動參數設定 `tf_publish_rate:=0.0`，光達驅動不發布 TF；所有感測器靜態 TF 由 Robot Model 的 `robot_state_publisher` 統一負責。

2. **慣性測量單元驅動（TDK IIM-42652 IMU）**：
   - **套件與節點**：使用 `tdk_ros2_imu` 套件之 `tdk_imu_node`，節點名稱為 `imu_driver_node`。
   - **硬體傳輸與配置**：透過 USB Serial 介面讀取實體 IMU，精確連線設定依 `src/mobile_base_perception/config/tdk_imu.yaml`。
   - **主題映射與 Frame**：
     - 節點預設主題經 Launch 重新映射為 `/imu/data_raw`（`sensor_msgs/msg/Imu`）。
     - 座標框架標註為 `frame_id: "base_imu_link"`。

3. **系統整合啟動（Canonical Bringup Integration）**：
   - 在標準系統啟動流程（`src/mobile_base_bringup/launch/mobile_base.launch.py`）中，`tdk_imu.launch.py` 與 `sick_dual_lidar.launch.py` 納入通用實體清單（`common_entities`），於 Mapping Mode 與 Navigation Mode 下皆保持運行。

### Expected Normal Behavior

- 系統啟動後，`/scan_front` 持續提供前光達 LaserScan 訊息。
- 系統啟動後，`/scan_rear` 持續提供後光達 LaserScan 訊息。
- 系統啟動後，`/imu/data_raw` 持續提供原始 IMU 量測訊息。
- 運行期各感測訊息之 `header.frame_id` 與 Robot Model 定義之感測器座標框架（`base_lidar_link_FL_1`、`base_lidar_link_BR_1`、`base_imu_link`）一致。
- 前後雙光達感測串流維持完全獨立，系統無 `dual_laser_merger` 亦無合併 `/scan` 主題。
- Sensor Ingestion 不負責任何 TF 廣播、里程推算或位姿估算。

### Implementation References

- Dual LiDAR Launch: `src/mobile_base_perception/launch/sick_dual_lidar.launch.py`
- IMU Launch: `src/mobile_base_perception/launch/tdk_imu.launch.py`
- IMU Parameter Config: `src/mobile_base_perception/config/tdk_imu.yaml`
- Canonical Bringup Launch: `src/mobile_base_bringup/launch/mobile_base.launch.py`

## 3. State Estimation

### Responsibility

State Estimation 負責在不依賴全域地圖的前提下，持續估測機器人在二維平面上的運動狀態與連續里程，並透過分層架構結合雷達匹配與感測融合：由 Kinematic-ICP 以輪速里程為運動學先驗配準二維雷達點雲，產出雷達里程估算；再由擴展卡爾曼濾波器（EKF）融合雷達里程與 IMU 偏航角速度，輸出連續的平面濾波狀態（`/odometry/filtered`），並發布 `odom -> base_footprint` 動態座標轉換。

### Interfaces and Flow

```text
/diff_drive_controller/odom ────┐ (nav_msgs/msg/Odometry, Wheel Motion Prior)
(Base Control)                  │
                                ▼
/scan_front ───────────────► kinematic_icp_online_node (kinematic_icp)
(sensor_msgs/msg/LaserScan)     │
(Sensor Ingestion)              ▼
                         /lidar_odometry (nav_msgs/msg/Odometry)
                                │ (odom0: x, y, yaw)
                                ▼
/imu/data_raw ─────────────► ekf_filter_node (robot_localization)
(sensor_msgs/msg/Imu)           │ (imu0: vyaw)
(Sensor Ingestion)              │
                                ├──► /odometry/filtered (nav_msgs/msg/Odometry)
                                │
                                └──► /tf (Dynamic TF)
                                     └── odom -> base_footprint
```

- **輸入資料流**：
  - `/scan_front`（`sensor_msgs/msg/LaserScan`）：來自 Sensor Ingestion，由前左 2D 光達提供平面掃描量測（`frame_id: base_lidar_link_FL_1`），供 Kinematic-ICP 進行點雲配準。
  - `/diff_drive_controller/odom`（`nav_msgs/msg/Odometry`）：來自 Base Control，提供輪端差速里程估算，作為 Kinematic-ICP 幀間點雲配準的運動學先驗（Kinematic Prior）。
  - `/imu/data_raw`（`sensor_msgs/msg/Imu`）：來自 Sensor Ingestion，由 6 軸 IMU 提供慣性量測（`frame_id: base_imu_link`），供 EKF 融合繞 Z 軸之偏航角速度（`vyaw`）。
- **輸出資料流**：
  - `/lidar_odometry`（`nav_msgs/msg/Odometry`）：由 `kinematic_icp_online_node` 輸出之雷達里程估計，包含相對於 `odom` 框架的平面位姿（$x, y, \text{yaw}$）。
  - `/odometry/filtered`（`nav_msgs/msg/Odometry`）：由 `ekf_filter_node` 發布之濾波狀態估測結果，供下游 Mapping、Localization 與 Navigation 模組使用。
  - 動態 TF（`odom -> base_footprint`）：由 `ekf_filter_node` 於 `/tf` 上發布。
- **TF 所有權與邊界**：
  - `diff_drive_controller` 配置 `enable_odom_tf: false`。
  - `kinematic_icp_online_node` 配置 `publish_odom_tf: false`。
  - `ekf_filter_node` 配置 `publish_tf: true`。
  - 在目前 production 執行路徑中，EKF 是 `odom -> base_footprint` 動態 TF 的唯一 publisher。
  - 下游邊界劃分：機器人本體與感測器內部幾何（`base_footprint` 以下）由 Robot Model（`robot_state_publisher`）負責；全域地圖到里程框架之轉換（`map -> odom`）由 Mapping Mode 下的 Mapping（`slam_toolbox`）或 Navigation Mode 下的 Localization（`amcl`）發布；State Estimation 不發布 `map -> odom`，亦不執行地圖載入或全域重定位。

### Implementation

1. **Kinematic-ICP 雷達里程估測（Kinematic-ICP Online Node）**：
   - **套件與節點**：使用 `kinematic_icp` 套件之 `kinematic_icp_online_node`，由 `src/kinematic_icp/ros/launch/kinematic_icp.launch.py` 啟動，套用配置檔 `src/kinematic_icp/ros/config/kinematic_icp_ros.yaml`。
   - **二維點雲配準**：配置 `use_2d_lidar: true`，訂閱前光達 `/scan_front`。節點將 2D 雷達掃描轉換為局部點雲並執行體素化降採樣（`voxel_size: 0.1`）與點雲配準。
   - **輪速先驗整合（Kinematic Prior）**：訂閱輪式里程計 `/diff_drive_controller/odom`，以輪速里程之運動增量作為點雲配準初值先驗。
   - **座標框架與輸出**：設定 `lidar_odom_frame: "odom"` 與 `base_frame: "base_footprint"`，輸出未濾波之雷達里程計主題 `/lidar_odometry`；配置 `publish_odom_tf: false`，不發布 TF。

2. **擴展卡爾曼濾波融合（EKF State Estimation）**：
   - **套件與節點**：使用 `robot_localization` 套件之 `ekf_node`，具現化為節點 `ekf_filter_node`，由 `src/mobile_base_state_estimation/launch/ekf.launch.py` 啟動，套用配置檔 `src/mobile_base_state_estimation/config/ekf.yaml`。
   - **運行模式與頻率**：配置 `two_d_mode: true`，約束於二維平面運動；目前配置之運行頻率為 50 Hz（`frequency: 50.0`）。
   - **觀測量融合配置**：
     - `odom0`（`/lidar_odometry`）：融合平面位置與航向角（$x, y, \text{yaw}$）。
     - `imu0`（`/imu/data_raw`）：融合繞 Z 軸之偏航角速度（`vyaw`）。
   - **輸出狀態**：發布濾波里程主題 `/odometry/filtered`（`nav_msgs/msg/Odometry`）。

3. **動態 TF 所有權（Dynamic TF Ownership）**：
   - `diff_drive_controller` 配置 `enable_odom_tf: false`。
   - `kinematic_icp_online_node` 配置 `publish_odom_tf: false`。
   - `ekf_filter_node` 配置 `publish_tf: true`，指定 `odom_frame: "odom"`、`base_link_frame: "base_footprint"` 與 `world_frame: "odom"`。
   - 在目前 production 執行路徑中，EKF 是 `odom -> base_footprint` 動態 TF 的唯一 publisher。

4. **系統整合與模式通用性（Canonical Bringup Integration）**：
   - 在標準系統啟動流程（`src/mobile_base_bringup/launch/mobile_base.launch.py`）中，`kinematic_icp.launch.py` 與 `ekf.launch.py` 均註冊於共通實體清單（`common_entities`）。
   - State Estimation 在 Mapping Mode 與 Navigation Mode 下皆保持運作，提供一致的里程推算基底。

### Expected Normal Behavior

- `/lidar_odometry` 持續提供 local LiDAR odometry。
- `/odometry/filtered` 持續提供 filtered planar odometry。
- EKF 持續發布 `odom -> base_footprint` 動態 TF。
- 系統無第二個 `odom -> base_footprint` publisher。
- State Estimation 不發布 `map -> odom`。
- Mapping Mode 與 Navigation Mode 皆使用同一 State Estimation ownership。

### Implementation References

- Kinematic-ICP Launch: `src/kinematic_icp/ros/launch/kinematic_icp.launch.py`
- Kinematic-ICP Parameter Config: `src/kinematic_icp/ros/config/kinematic_icp_ros.yaml`
- State Estimation Launch: `src/mobile_base_state_estimation/launch/ekf.launch.py`
- State Estimation Parameter Config: `src/mobile_base_state_estimation/config/ekf.yaml`
- Base Control Parameter Config (Wheel Odometry Source): `src/mobile_base_control/config/base_control_params.yaml`
- Canonical Bringup Launch: `src/mobile_base_bringup/launch/mobile_base.launch.py`

## 4. Mapping

### Responsibility

Mapping 負責在 Mapping Mode 下，依據前向 2D 激光雷達掃描與系統座標轉換（TF），即時建立並更新二維佔據網格地圖（Occupancy Grid），於 Mapping Mode 期間發布 `map -> odom` 動態座標轉換，並透過專案儲存流程將建立之地圖持久化為包含 `map.yaml` 與 `map.pgm` 的 Map Package，供後續 Localization 載入使用。

### Interfaces and Flow

#### A. 運行期建圖資料流（Runtime Mapping Flow）

```text
/scan_front (sensor_msgs/msg/LaserScan) ──┐
(Sensor Ingestion)                         │
                                           ▼
TF: odom -> base_footprint ──────────► async_slam_toolbox_node (slam_toolbox)
(State Estimation)                         │
                                           ├─► /map (nav_msgs/msg/OccupancyGrid)
TF: base_footprint -> ... -> scan_frame ──┘
(Robot Model, /tf_static)                  └─► /tf (Dynamic TF)
                                                └── map -> odom
```

- **輸入資料與座標轉換相依**：
  - `/scan_front`（`sensor_msgs/msg/LaserScan`）：來自 Sensor Ingestion，由前左 2D 光達提供平面掃描量測（`frame_id: base_lidar_link_FL_1`），為 SLAM 演算法唯一消耗之感測主題。
  - 動態 TF `odom -> base_footprint`：由 State Estimation 發布；SLAM Toolbox 不直接訂閱 `/odometry/filtered` 主題，而是透過 TF 緩衝區查詢此座標轉換以獲取本體里程。
  - 靜態 TF `base_footprint -> ... -> base_lidar_link_FL_1`：由 Robot Model 於 `/tf_static` 發布，提供雷達安裝外參。
- **輸出資料流**：
  - `/map`（`nav_msgs/msg/OccupancyGrid`）：即時二維佔據網格地圖，目前配置解析度為 0.05 m。
  - `/map_metadata`（`nav_msgs/msg/MapMetaData`）：地圖元數據（尺寸、解析度與原點）。
  - 動態 TF（`map -> odom`）：由 `async_slam_toolbox_node` 於 `/tf` 發布。
- **TF 所有權與邊界**：
  - 在 Mapping Mode 下，`async_slam_toolbox_node` 是 `map -> odom` 動態 TF 的唯一 publisher。
  - State Estimation 獨立維護 `odom -> base_footprint`，Robot Model 維護 `base_footprint` 以下的本體幾何。
  - 模式互斥原則：Navigation Mode 下的 Localization（AMCL）在 Mapping Mode 下不啟動；Navigation Mode 的 `map -> odom` 不屬於 Mapping。

#### B. 地圖包保存流程（Map Package Save Flow）

```text
/map (nav_msgs/msg/OccupancyGrid, Transient Local)
       │
       ▼ (save_map.sh)
map_saver_cli (nav2_map_server)
       │
       ├──► map.yaml (地圖參數設定)
       └──► map.pgm  (二維佔據網格光柵影像)
               │
               ▼
validate_map_readback (mobile_base_mapping / MapIO)
       │
       ▼ (loadMapFromYaml 驗證成功)
Map Package (maps/<timestamp>/)
```

- **地圖包產物邊界**：
  - 儲存流程僅產生並驗證 Map Package 實體檔案（`map.yaml` 與 `map.pgm`）。
  - 站點目錄（`stations.yaml`）與路網圖（`route_graph.geojson`）不屬於 Mapping 產物，Mapping 亦不擁有整個場域目錄。

### Implementation

1. **SLAM 即時建圖節點（SLAM Toolbox Lifecycle Node）**：
   - **套件與節點**：使用 `slam_toolbox` 套件之 `async_slam_toolbox_node`（以 Lifecycle 節點管理），由 `src/mobile_base_mapping/launch/mapping.launch.py` 啟動，套用配置檔 `src/mobile_base_mapping/config/slam_toolbox.yaml`。
   - **啟動狀態轉換**：在 Mapping Mode 啟動時，Launch 事件處理器自動觸發節點之 `configure` 與 `activate` 狀態轉換，進入活躍運行狀態。
   - **感測輸入與解析度**：配置 `scan_topic: "/scan_front"`（僅使用前光達，不使用後光達）；網格解析度為 `resolution: 0.05`（0.05 m）。
   - **里程相依機制**：節點不訂閱 `/odometry/filtered` 主題，直接透過 TF 查詢 `odom -> base_footprint` 與雷達安裝外參。

2. **動態 TF 所有權（Mapping Mode map -> odom Ownership）**：
   - 座標框架配置：`map_frame: "map"`、`odom_frame: "odom"`、`base_frame: "base_footprint"`。
   - 發布週期：配置 `transform_publish_period: 0.05`（以 20 Hz 發布 `map -> odom` 動態 TF）。
   - 在 Mapping Mode 期間，`async_slam_toolbox_node` 是系統中 `map -> odom` 的唯一 publisher。

3. **地圖持久化與儲存流程（Map Package Save Flow）**：
   - **儲存腳本**：`src/mobile_base_bringup/scripts/save_map.sh`（安裝於 `lib/mobile_base_bringup/save_map.sh`）。
   - **輸出路徑**：預設於專案目錄之 `maps/<timestamp>/` 建立輸出結構，並以 `map` 為基礎檔名。
   - **執行元件與參數**：調用 `nav2_map_server` 之 `map_saver_cli` 訂閱 `/map` 主題（`map_subscribe_transient_local:=true`，逾時時間 10.0 秒），匯出 `map.yaml` 與 `map.pgm`。

4. **讀回反序列化驗證（MapIO Read-Back Verification）**：
   - **驗證元件**：`src/mobile_base_mapping/test/validate_map_readback.cpp` 編譯產出並安裝為套件執行檔 `validate_map_readback`。
   - **驗證邏輯**：使用 `nav2_map_server::loadMapFromYaml` 重新載入剛產生的 `map.yaml`，確認 Map Package 可被成功反序列化讀回。
   - **流程串接**：`save_map.sh` 在 `map_saver_cli` 結束後直接調用 `validate_map_readback "${map_yaml}"`，檢驗通過後方回報成功。

### Expected Normal Behavior

- 系統於 Mapping Mode 啟動後，`async_slam_toolbox_node` 完成 configure 與 activate 進入活躍狀態。
- `/map` 持續提供目前建立之二維佔據網格地圖。
- `async_slam_toolbox_node` 持續發布 `map -> odom` 動態 TF。
- State Estimation 繼續獨立發布 `odom -> base_footprint` 動態 TF。
- 執行 `save_map.sh` 後，於 `maps/<timestamp>/` 產生 `map.yaml` 與 `map.pgm`，並成功通過 MapIO read-back。
- 成功保存之 Map Package 可供後續 Navigation Mode 之 Localization 載入。

### Failure Behavior

- 若 `map_saver_cli` 逾時（10.0 秒）未取得地圖或未產出 `map.yaml` 與 `map.pgm`，`save_map.sh` 輸出錯誤訊息並以 exit code 1 終止。
- 若 `validate_map_readback` 反序列化讀回失敗，回傳 exit code 2，`save_map.sh` 立即中斷終止，不回報儲存成功。

### Implementation References

- Mapping Launch: `src/mobile_base_mapping/launch/mapping.launch.py`
- SLAM Toolbox Parameter Config: `src/mobile_base_mapping/config/slam_toolbox.yaml`
- Map Save Script: `src/mobile_base_bringup/scripts/save_map.sh`
- Map Readback Validator Source: `src/mobile_base_mapping/test/validate_map_readback.cpp`
- Canonical Bringup Launch: `src/mobile_base_bringup/launch/mobile_base.launch.py`
- Mapping Compatibility Wrapper Launch: `src/mobile_base_bringup/launch/mapping.launch.py`

## 5. Localization

### Responsibility

Localization 負責在 Navigation Mode 下：
載入所選定之 Map Package → 發布二維佔據網格靜態地圖 → 結合前向光達掃描與系統里程估測 AMR 於地圖中之位姿 → 作為唯一權威發布 Navigation Mode 下之 `map -> odom` 動態坐標轉換與定位位姿。

本區域不包含：
- 地圖建圖（Mapping）
- 導航目標接收與驗證（Navigation Target Admission）
- 路網規劃與導航控制（Route-Assisted Navigation）
- 底盤運動控制（Base Control）
- 精準對接（Precision Docking）

### Interfaces and Flow

```text
Map Package (map.yaml, map.pgm)
       │
       ▼ (site_resolution.py / launch CLI)
   map_server (nav2_map_server)
       │
       ├─────────────────────────────────────────► /map (nav_msgs/msg/OccupancyGrid)
       │
       ▼ (地圖佔據網格)
      amcl (nav2_amcl) ◄─────── /initialpose (geometry_msgs/msg/PoseWithCovarianceStamped)
       ▲           ▲            (外部可選初始位姿覆寫)
       │           │
       │           └─────────── 動態 TF: odom -> base_footprint (State Estimation EKF)
       │                        靜態機構 TF: base_footprint -> ... -> base_lidar_link_FL_1
       │
       └─────────────────────── /scan_front (sensor_msgs/msg/LaserScan, Sensor Ingestion)
       │
       ├─────────────────────────────────────────► 動態 TF: map -> odom
       ├─────────────────────────────────────────► /amcl_pose (geometry_msgs/msg/PoseWithCovarianceStamped)
       └─────────────────────────────────────────► /particle_cloud (nav2_msgs/msg/ParticleCloud)
```

1. **輸入介面與資料流**：
   - **Map Package**：包含 `map.yaml` 與 `map.pgm`。於系統啟動時透過 `site_resolution.py` 解析（依 `site` 參數）或由 CLI 引數 `map` 顯式傳入，由 `map_server` 讀取並反序列化。
   - `/scan_front` (`sensor_msgs/msg/LaserScan`)：來自 Sensor Ingestion 之前向光達測距掃描（`frame_id: base_lidar_link_FL_1`）。AMCL 僅訂閱前向光達，不使用後向光達。
   - **動態 TF `odom -> base_footprint`**：由 State Estimation（EKF）發布。AMCL 透過 TF Buffer 查詢此轉換以及底盤至感測器之靜態機構 TF（`base_footprint -> ... -> base_lidar_link_FL_1`），不直接訂閱 `/odometry/filtered` 主題。
   - **Initial Pose**：
     - **預設初始位姿**：由部署設定提供（`set_initial_pose: true`，預設為 `x=0.0`、`y=0.0`、`z=0.0`、`yaw=0.0`）。
     - **外部覆寫位姿**：`/initialpose` (`geometry_msgs/msg/PoseWithCovarianceStamped`)，供 RViz2 或上層系統在預設不適用時顯式發布，重設粒子群分佈。

2. **輸出介面與資料流**：
   - `/map` (`nav_msgs/msg/OccupancyGrid`，QoS: Transient Local）：由 `map_server` 發布已知環境之二維佔據網格地圖。
   - **動態 TF `map -> odom`**：由 `amcl` 節點週期性廣播。在 Navigation Mode 下，AMCL 是 `map -> odom` 動態坐標轉換的唯一權威發布者。
   - `/amcl_pose` (`geometry_msgs/msg/PoseWithCovarianceStamped`）：AMCL 估測之機器人全局位姿與協方差矩陣。
   - `/particle_cloud` (`nav2_msgs/msg/ParticleCloud`）：AMCL 當前粒子群分佈狀態。

### Implementation

1. **節點組成與生命週期管理**：
   - `map_server` (`nav2_map_server/map_server`，Lifecycle Node）：負責解析 `map.yaml` 並提供地圖資料主題與服務。
   - `amcl` (`nav2_amcl/amcl`，Lifecycle Node）：自適應蒙地卡羅粒子濾波定位節點，採用似然場模型（`laser_model_type: "likelihood_field"`）與差速運動模型（`nav2_amcl::DifferentialMotionModel`）。
   - `lifecycle_manager_localization` (`nav2_lifecycle_manager/lifecycle_manager`）：統籌管理 `map_server` 與 `amcl` 生命週期狀態轉換（`autostart: true`）。

2. **坐標框架與配置事實**：
   - `global_frame_id`: `map`
   - `odom_frame_id`: `odom`
   - `base_frame_id`: `base_footprint`
   - `scan_topic`: `/scan_front`
   - `tf_broadcast`: `true`
   - `set_initial_pose`: `true`，`initial_pose: {x: 0.0, y: 0.0, z: 0.0, yaw: 0.0}`

### Expected Normal Behavior

- 系統於 Navigation Mode 啟動後，`lifecycle_manager_localization` 將 `map_server` 與 `amcl` 轉至 ACTIVE 狀態。
- `map_server` 發布具備 Transient Local 特性之 `/map` 佔據網格。
- `amcl` 依配置之預設初始位姿完成粒子初始化，或於收到 `/initialpose` 時重設粒子分佈。
- 當機器人移動且前向光達接收掃描資料時，`amcl` 依據差速模型與似然場連續更新粒子權重，並持續廣播 `map -> odom` 動態 TF。
- 結合 State Estimation 維護之 `odom -> base_footprint`，下游導航演算法可完整解析 `map -> base_footprint` 之全局坐標鏈。

### Failure Behavior

- 若指定之 `map.yaml` 檔案不存在或損毀，`map_server` 無法通過 configure 階段，生命週期管理器回報錯誤，定位子系統無法進入活躍（ACTIVE）狀態。
- 若前向光達掃描 `/scan_front` 中斷或 TF `odom -> base_footprint` 丟失，`amcl` 無法更新粒子權重；若超過轉換容許逾時（`transform_tolerance`），`amcl` 輸出警告日誌並停止發布最新之 `map -> odom` 動態坐標轉換與 `/amcl_pose`。

### Implementation References

- Localization Launch: `src/mobile_base_localization/launch/localization.launch.py`
- AMCL Configuration: `src/mobile_base_localization/config/amcl_params.yaml`
- Site Resolution Module: `src/mobile_base_bringup/launch/site_resolution.py`
- Canonical Bringup Launch: `src/mobile_base_bringup/launch/mobile_base.launch.py`

## 6. Navigation Target Admission

### Responsibility

Navigation Target Admission 負責在導航任務發起前處理站點目標（Station Target）：
接收外部站點目標請求（Station ID） → 透過 Station Catalog 查表解析站點坐標（Station Resolution） → 坐標框架正規化（Frame Normalization） → 幾何與數值合法性驗證（Validation） → 產出標準規範位姿（Canonical Goal Pose）並發送至 Nav2 `/navigate_to_pose` Action Server。

關於通用位姿目標（Generic Pose Target）：
外部客戶端（如 RViz2 或上層系統）可直接發送位姿至 Nav2 原生 `/navigate_to_pose` Action Server，該路徑屬於 Nav2 與外部系統之生產邊界（External Production Boundary），不經過 `mobile_base` 的 `TargetAdmission` 模組，亦不具備本模組提供之提前驗證。

本區域責任範圍終止於 Station Target 之 Canonical Goal Pose 驗證通過並送達 Nav2 Action Server，不包含後續路徑規劃、避障、運動追蹤或對接執行。

### Interfaces and Flow

```text
[導航目標輸入]
  ├─ Station Target: CLI 引數 --station <ID> --catalog <path> ─┐
  │                                                            ▼
  │                                                navigate_to_station (CLI 應用程式)
  │                                                            │ (調用 TargetAdmission C++ 模組)
  │                                                            ├─ 載入 Station Catalog (stations.yaml)
  │                                                            ├─ 解析 station_id 坐標 (x, y, yaw)
  │                                                            ├─ 四元數姿態正規化
  │                                                            └─ 數值有限性與 frame_id 驗證
  │                                                            │
  │                                                            ▼ (Canonical Goal Pose)
  └─ Generic Pose Target (外部生產邊界): 外部客戶端 / RViz2 ──► /navigate_to_pose (Action)
                                                                 (nav2_msgs/action/NavigateToPose)
```

1. **目標輸入介面**：
   - **Station Target**：透過 CLI 應用程式 `navigate_to_station` 傳入 `--station <station_id> --catalog <stations.yaml>`。
   - **Generic Pose Target（外部邊界）**：外部客戶端（如 RViz2 或外部調度系統）直接向 Nav2 原生 Action `/navigate_to_pose` (`nav2_msgs/action/NavigateToPose`) 發送目標，此路徑不經過 `TargetAdmission` 處理。
   - **Station Catalog**：站點目錄 YAML 檔案（`stations.yaml`），定義站點名稱、`x`、`y` 與 `yaw`（弧度），坐標系基準為 `map`。

2. **驗證與正規化介面（僅限 Station Target）**：
   - 經由 `TargetAdmission` 模組驗證：坐標為有限實數（`std::isfinite`）、坐標系為 `map`、四元數非零且長度正規化。

3. **目標輸出介面**：
   - `/navigate_to_pose` (`nav2_msgs/action/NavigateToPose`)：Station Target 經由 `navigate_to_station` 驗證通過後，產出之標準規範位姿（`geometry_msgs/msg/PoseStamped`，`frame_id: "map"`）封裝為 Action Goal 提交至 Nav2。

### Implementation

1. **核心程式庫 `TargetAdmission`** (`src/mobile_base_navigation/src/target_admission.cpp`, `include/mobile_base_navigation/target_admission.hpp`)：
   - **Station Catalog 解析**：`load_station_catalog()` 解析 YAML 結構，載入站點清單。
   - **站點查表**：`resolve_station()` 依據給定之 `station_id` 於目錄中進行精確字串比對，提取 `(x, y, yaw)` 坐標。
   - **位姿正規化**：`normalize_goal_pose()` 將 Euler yaw 轉換為正規化之四元數姿態 `(x, y, z, w)`。
   - **位姿驗證**：`validate_canonical_pose()` 嚴格校驗坐標是否為有限數值、`frame_id` 是否為 `map`、四元數是否滿足非零且接近單位長度。

2. **執行應用程式 `navigate_to_station`** (`src/mobile_base_navigation/src/navigate_to_station_app.cpp`, `src/mobile_base_navigation/src/navigate_to_station_main.cpp`)：
   - 提供命令列操作介面，強制要求 `--station` 與 `--catalog` 參數。
   - 透過 `TargetAdmission` 依序執行目錄載入、站點查詢與位姿驗證。
   - 驗證成功後建立 `/navigate_to_pose` Action Client，設定時間戳並非同步發送 Action Goal，同時監聽回傳之反饋資訊（`distance_remaining`、`current_pose`）。

3. **生產環境介面邊界說明**：
   - **Station Target**：具備專屬生產級 CLI 應用程式（`navigate_to_station`）與 `TargetAdmission` 核心程式庫，執行目錄載入、站點查詢、位姿轉換與數值/幾何合法性提前驗證，並提供明確狀態碼輸出。
   - **Generic Pose Target**：屬於外部生產邊界（External Production Boundary），`mobile_base` 現行實作未為 Generic Pose Target 設置自訂 CLI、轉接節點或提前驗證邏輯，外部客戶端直接對接 Nav2 原生 `/navigate_to_pose` Action Server 介面。

### Expected Normal Behavior

- 操作者執行 `navigate_to_station --station <ID> --catalog <path>`。
- 程式成功解析目錄，比對取得站點位姿，校驗數值為有限實數且姿態有效，坐標系確立為 `map`。
- 程式連線至 `/navigate_to_pose` Action Server，發送目標並持續輸出反饋，待機器人到達目標並完成導航後以 exit code 0 正常退出。

### Failure / Cancel Behavior

- **站點目錄或解析失敗**：若目錄檔案不存在、格式損毀或查無指定 `station_id`，`navigate_to_station` 輸出錯誤訊息並以 exit code 3 (`kExitResolutionFailure`) 終止，不發送任何導航目標。
- **目標位姿校驗失敗**：若坐標包含 NaN/Inf 或四元數非法，判定為驗證不通過，以 exit code 3 終止。
- **Nav2 服務不可用**：若連線 `/navigate_to_pose` 逾時，以 exit code 4 (`kExitNav2Unavailable`) 終止。
- **下游導航執行失敗**：若 Nav2 回報導航終止或失敗，以 exit code 5 (`kExitNavigationFailure`) 退出。
- **使用者取消**：若於提交前或執行中收到取消信號（如 SIGINT），向伺服器發起取消並以 exit code 130 (`kExitCanceled`) 退出。

### Implementation References

- Target Admission Library: `src/mobile_base_navigation/include/mobile_base_navigation/target_admission.hpp`, `src/mobile_base_navigation/src/target_admission.cpp`
- Navigate to Station App: `src/mobile_base_navigation/src/navigate_to_station_app.cpp`, `src/mobile_base_navigation/src/navigate_to_station_main.cpp`

## 7. Route-Assisted Navigation

### Responsibility

Route-Assisted Navigation 負責在接收已驗證之 Canonical Goal Pose（經由 `/navigate_to_pose` Action）後：
計算拓撲路網導引（Topological Route Computation） → 規劃起點至路網的第一哩接駁路徑（First Mile Connector，必要時） → 沿路網圖行進（On Route） → 規劃路網至終點目標的最後一哩接駁路徑（Last Mile Connector，必要時） → 串接路徑之運動控制追蹤（Path Tracking） → 終點減速煞停確認與結果回報。

本區域不包含導航目標接收（Target Admission）與精準對接（Precision Docking）。

### Interfaces and Flow

```text
Canonical Goal Pose (geometry_msgs/msg/PoseStamped)
       │
       ▼
/navigate_to_pose Action Server (bt_navigator)
       │
       ▼ (route_assisted_nav.xml 行為樹管線)
       ├─► ComputeRoute (route_server) ◄─── route_graph.geojson (路網拓撲圖)
       │         │
       │         ▼ (raw_route_path)
       ├─► First Mile 判定與規劃 (planner_server, NavfnPlanner) ──┐
       │         │                                               ▼
       │         ▼                                      first_connected_path
       ├─► Last Mile 判定與規劃 (planner_server, NavfnPlanner) ───┤
       │         │                                               ▼
       │         ▼                                       final_route_path
       └─► FollowPath (controller_server, MPPIController)
                 │
                 ├──► 障礙物避障監控 (local_costmap, global_costmap)
                 ├──► 到點煞停檢查 (StoppedGoalChecker)
                 │
                 ▼
       /diff_drive_controller/cmd_vel (geometry_msgs/msg/TwistStamped)
                 │
                 ▼
           Base Control
```

1. **Action 介面**：
   - `/navigate_to_pose` (`nav2_msgs/action/NavigateToPose`)：主要任務入口，由 `bt_navigator` 提供 Action Server。

2. **內部節點協作與服務/Action**：
   - **拓撲路網計算**：由 `bt_navigator` 調用 `route_server` 之 `ComputeRoute`，以離線路網圖 `route_graph.geojson` 產出拓撲軌跡 `raw_route_path`。
   - **接駁路徑規劃**：由 `bt_navigator` 調用 `planner_server`（`nav2_navfn_planner::NavfnPlanner`，Plugin ID `GridBased`）之 `ComputePathToPose`，於代價地圖上計算第一哩與最後一哩接駁路徑。
   - **路徑追蹤控制**：由 `bt_navigator` 調用 `controller_server` 之 `FollowPath`，將串接後之完整路徑 `final_route_path` 交由 MPPI 控制器追蹤。

3. **代價地圖與感知輸入**：
   - `global_costmap`：基於 `map` 坐標系，包含靜態圖層（`StaticLayer`，訂閱 `/map`）、障礙物圖層（`ObstacleLayer`，訂閱 `/scan_front` 與 `/scan_rear`）與膨脹圖層（`InflationLayer`）。
   - `local_costmap`：基於 `odom` 坐標系之滑動窗口（3m × 3m），訂閱 `/scan_front` 與 `/scan_rear` 進行即時避障。

4. **速度指令輸出**：
   - `/diff_drive_controller/cmd_vel` (`geometry_msgs/msg/TwistStamped`)：由 `controller_server` 重映射並發布至 Base Control 的時戳速度指令。

### Implementation

1. **行為樹管線結構** (`src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml`)：
   - 採用 `PipelineSequence`（名稱為 `NavigateRouteAssisted`），以 1.0 Hz 頻率循環評估與更新路徑：
     - **第一步：Topological Route (`ComputeRoute`)**：`route_server` 根據全局目標與當前位姿在 `route_graph.geojson` 拓撲圖上搜尋最優節點路徑，產出 `raw_route_path`。
     - **第二步：First Mile Connector**：檢驗當前機器人位姿與 `raw_route_path` 起點（索引 0）之距離。若距離小於等於容許值 0.2 m（`ArePosesNear tolerance="0.2"`），則跳過第一哩接駁；否則調用 `planner_server` 規劃當前位姿至路網起點之無碰撞路徑，並透過 `ConcatenatePaths` 拼接於路網前段（產出 `first_connected_path`）。
     - **第三步：Last Mile Connector**：檢驗 `first_connected_path` 終點（索引 -1）與目標 Goal 之距離。若距離小於等於 0.2 m，跳過最後一哩；否則調用 `planner_server` 規劃路網終點至目標 Goal 之路徑，拼接產出 `final_route_path`。
     - **第四步：FollowPath 與停止校驗**：由 `controller_server` 執行 MPPI 演算法追蹤 `final_route_path`。配置 `StoppedGoalChecker`（`xy_goal_tolerance: 0.25` m，`yaw_goal_tolerance: 0.5236` rad，`trans_stopped_velocity: 0.05` m/s，`rot_stopped_velocity: 0.10` rad/s），確保機器人不僅在幾何容許誤差內到達目標，且完全煞停後方回報成功。

2. **核心架構原則與事實**：
   - **三段式架構構成**：First Mile、On Route 與 Last Mile 均為 Route-Assisted Navigation 之常態組成環節，非降級備援機制（Not Fallbacks）。
   - **無全局自由空間自動備援**：當前生產實作未提供獨立或自動之全局自由空間備援規劃。若拓撲路網無法計算（例如目標點無法對應至路網圖）或接駁路徑受阻，行為樹序列直接終止並回報 FAILURE。

### Expected Normal Behavior

- 接收 Canonical Goal Pose 後，`bt_navigator` 啟動行為樹。
- `route_server` 產出拓撲路徑，系統依幾何距離自動計算第一哩與最後一哩接駁路徑，拼接產出完整路徑（`final_route_path`）。
- 由 `controller_server` 之 MPPI 控制器沿軌跡計算平移與旋轉速度指令，發布至 `/diff_drive_controller/cmd_vel`。
- 底盤沿軌跡行進；在接近目標位姿時，控制器依減速參數調節速度。
- 滿足 `StoppedGoalChecker` 之位姿誤差與靜止速度門檻後，`/navigate_to_pose` Action 回傳 SUCCEEDED。

### Failure / Cancel Behavior

- **拓撲路網計算失敗**：若 `ComputeRoute` 無法於路網圖建立路徑，行為樹直接失敗終止，不嘗試自由空間直達規劃。
- **接駁規劃失敗**：若第一哩或最後一哩遭遇障礙阻擋導致 `ComputePathToPose` 無法成路，導航任務失敗。
- **前進停滯（Progress Failure）**：若 `SimpleProgressChecker` 偵測在 30.0 秒內機器人位移未達 0.05 m，判定為受困，控制器終止並回報失敗。
- **任務取消**：客戶端發送取消請求時，行為樹立即中斷執行，`controller_server` 輸出全零速度指令並回傳 CANCELED。

### Implementation References

- Navigation Launch: `src/mobile_base_navigation/launch/navigation.launch.py`
- Nav2 Parameter Config: `src/mobile_base_navigation/config/nav2_params.yaml`
- Behavior Tree XML: `src/mobile_base_navigation/behavior_trees/route_assisted_nav.xml`
- Site Resolution Module: `src/mobile_base_bringup/launch/site_resolution.py`

## 8. Precision Docking

### Responsibility

Precision Docking 負責在接收外部明確的對接請求後：
結合外部視覺感知持續提供之對接標靶位姿 → 轉換並鎖定標靶幾何位姿於固定坐標系 → 執行局部閉迴路逼近與位姿對齊 → 於預定幾何間隙處煞停 → 回報對接成功、失敗或取消。

本區域為獨立之局部對接任務，不包含視覺標靶偵測（AprilTag/Image Perception）、對接發起時機決策、遠場導航或充電確認交握。

### Interfaces and Flow

```text
上身 (Upper Body) 視覺系統
       │
       ▼ (以約 10 Hz 持續發布標靶位姿)
/detected_dock_pose (geometry_msgs/msg/PoseStamped, frame_id: base_link)
       │
       ▼
docking_server (opennav_docking / apriltag_dock) ◄─── /dock_robot Action Goal
       │                                               (外部調度發起 DockRobot)
       ├─► TF Buffer: 將標靶鎖定至 fixed_frame (odom)
       ├─► 施加幾何停止間隙 (-0.7 m 沿標靶軸向)
       ├─► local_costmap 局部避障檢驗
       │
       ▼ (閉迴路控制速度指令)
/diff_drive_controller/cmd_vel (geometry_msgs/msg/TwistStamped)
       │
       ▼
  Base Control
```

1. **Action 觸發介面**：
   - `/dock_robot` (`nav2_msgs/action/DockRobot`)：由外部任務調度系統顯式發起。外部視覺標靶之存在或偵測不會自動觸發對接動作。

2. **對接標靶輸入**：
   - `/detected_dock_pose` (`geometry_msgs/msg/PoseStamped`，`frame_id: "base_link"`）：由上身（Upper Body）視覺系統持續以約 10 Hz 發布之 AprilTag 偵測位姿。

3. **環境安全輸入**：
   - `local_costmap/costmap_raw` 與 `local_costmap/published_footprint`：提供即時局部障礙物資訊，用於逼近過程之碰撞預檢。

4. **速度指令輸出**：
   - `/diff_drive_controller/cmd_vel` (`geometry_msgs/msg/TwistStamped`）：由 `docking_server` 重映射並發布至 Base Control 的時戳速度指令。

### Implementation

1. **節點與外掛架構**：
   - `docking_server` (`opennav_docking/opennav_docking`，Lifecycle Node，納入 `lifecycle_manager_navigation` 管理）。
   - 對接外掛採用 `opennav_docking::SimpleNonChargingDock`（外掛識別名稱 `apriltag_dock`）。

2. **配置與運作事實**：
   - `base_frame`: `base_link`
   - `fixed_frame`: `odom`
   - `use_external_detection_pose`: `true`
   - `dock_backwards`: `false`（採車頭前向對接進入）
   - `external_detection_translation_x`: `-0.7`（幾何預留間隙：車體停止於標靶前方 70 cm 處）
   - `docking_threshold`: `0.05`（對接成功位移誤差門檻 5 cm）
   - `controller_frequency`: `20.0` Hz
   - `use_collision_detection`: `true`（`dock_collision_threshold: 0.3`）
   - `enable_stamped_cmd_vel`: `true`

3. **關鍵架構界限**：
   - **無充電交握機制**：當前外掛為非充電對接器（`SimpleNonChargingDock`），無任何充電握手協議、BMS 狀態查詢或充電確認流程；AMR 於達到幾何誤差門檻停止後即判定任務完成。
   - **純局部對接**：任務參數配置 `navigate_to_staging_pose: false` 與 `use_dock_id: false`，完全依賴當前局部視野與外掛閉迴路控制。

### Expected Normal Behavior

- 上身視覺節點持續發布 `/detected_dock_pose`。
- 外部任務發送 `DockRobot::Goal` 至 `/dock_robot`。
- `docking_server` 接收任務，擷取最新標靶位姿，利用 TF Buffer 轉換並鎖定至 `odom` 坐標系，並施加 -0.7 m 的幾何位移偏移量作為目標停留點。
- 閉迴路控制器以最大 0.15 m/s 線速度與 0.5 rad/s 角速度驅動底盤靠近並對齊標靶，同時監控局部代價地圖避障。
- 當 AMR 與停留點之距離收斂至 `docking_threshold`（0.05 m）以內時，控制器輸出零速度煞停，`/dock_robot` Action 回報 SUCCEEDED。

### Failure / Cancel Behavior

- **初始標靶超時**：若於目標發起後 `initial_perception_timeout`（5.0 秒）內未收到 `/detected_dock_pose`，對接任務失敗終止。
- **標靶遺失超時**：若逼近過程中標靶丟失且超過 `external_detection_timeout`（2.0 秒），對接任務中斷失敗。
- **對接逾時**：若總逼近時間超過 `dock_approach_timeout`（30.0 秒），強制終止並回報失敗。
- **碰撞風險**：若局部代價地圖於預測軌跡上偵測到小於 `dock_collision_threshold`（0.3 m）之障礙物，即刻停車並回報失敗。
- **取消任務**：外部客戶端請求取消時，`docking_server` 立即發布全零速度停止底盤運動，並回傳 CANCELED。

### Implementation References

- Docking Server Launch: `src/mobile_base_navigation/launch/navigation.launch.py`
- Docking Parameter Config: `src/mobile_base_navigation/config/nav2_params.yaml`
- Docking Integration Test: `src/mobile_base_navigation/test/test_apriltag_docking_integration.py`

## 9. Base Control

### Responsibility

Base Control 負責底盤運動控制與硬體介面抽象：
接收時戳速度指令 → 經差速運動學轉換與加速度/速度限幅 → ros2_control 硬體抽象層 → 透過 Modbus RTU 與 M1 雙馬達驅動器進行即時通訊 → 讀取輪速與編碼器回授 → 產出輪式里程計（Odometry Source）與關節狀態 → 執行指令超時處置、馬達致能管理與安全煞停。

安全防護與煞停機制直接落實於 Base Control 內部，不另設獨立架構層。

### Interfaces and Flow

```text
/diff_drive_controller/cmd_vel (geometry_msgs/msg/TwistStamped)
(來源: teleop_twist_keyboard / controller_server / docking_server，無 twist_mux)
       │
       ▼
diff_drive_controller (ros2_control, update_rate: 30 Hz)
       │
       ├─► 差速運動學換算與加速度/速度限幅 (cmd_vel_timeout: 3600.0 s)
       │
       ▼
M1Hardware (hardware_interface::SystemInterface 外掛)
       │
       ▼ (調用 M1Driver)
Modbus RTU over /dev/ttyUSB0 (230400 bps, 廣播 Group 0x65, FC17 單一交易交換)
       │
       ├──► 同時寫入: 馬達 1 (右輪) 與馬達 2 (左輪) 目標轉速
       └──► 同時讀回: 馬達 1 (右輪) 與馬達 2 (左輪) 編碼器位置與轉速
       │
       ├─────────────────────────────────────────► /diff_drive_controller/odom (nav_msgs/msg/Odometry)
       │                                           (輪式里程計先驗，enable_odom_tf: false)
       │
       └─────────────────────────────────────────► /joint_states (sensor_msgs/msg/JointState)
                                                   (由 joint_state_broadcaster 發布至 TF)
```

1. **速度指令輸入介面**：
   - `/diff_drive_controller/cmd_vel` (`geometry_msgs/msg/TwistStamped`)。
   - 生產環境中未部署 `twist_mux`，所有指令來源（Mapping Mode 之手動遙控、Navigation Mode 之 `controller_server` 或 `docking_server`）直接對接此單一主題。

2. **回授輸出介面**：
   - `/diff_drive_controller/odom` (`nav_msgs/msg/Odometry`）：以 30 Hz 發布輪式里程計估測，作為 State Estimation 中 Kinematic-ICP 之運動先驗（Motion Prior）。
   - `/joint_states` (`sensor_msgs/msg/JointState`）：由 `joint_state_broadcaster` 以 30 Hz 發布左輪（`driving_wheel_joint_L`）與右輪（`driving_wheel_joint_R`）關節位置與速度，供 `robot_state_publisher` 更新機構動態轉換。

3. **硬體通訊介面**：
   - 序列埠 `/dev/ttyUSB0`，鮑率 230400 bps，Modbus RTU 協定。
   - 廣播群組位址 `0x65`，對應 M1 雙軸無刷馬達驅動器：右輪馬達驅動 ID 為 1（`DriveId::Right = 1`，關聯 `driving_wheel_joint_R`），左輪馬達驅動 ID 為 2（`DriveId::Left = 2`，關聯 `driving_wheel_joint_L`）。

### Implementation

1. **控制器堆疊與生命週期**：
   - `controller_manager` (`ros2_control_node`）：主控週期為 30 Hz（`update_rate: 30`）。
   - `diff_drive_controller` (`diff_drive_controller/DiffDriveController`）：
     - 輪系關節：`driving_wheel_joint_L`、`driving_wheel_joint_R`。
     - 幾何參數：輪距 `0.5545` m，輪半徑 `0.080` m。
     - 速度與加速度限制：最大線速度 1.0 m/s，最小線速度 -0.5 m/s，最大線加速度 0.5 m/s²，最大減速度 -1.0 m/s²；最大角速度 1.5 rad/s，最大角加速度 1.0 rad/s²，最大角減速度 -2.0 rad/s²。
     - `use_stamped_vel: true`。
     - `enable_odom_tf: false`：嚴格禁止由控制器發布 TF，避免與 State Estimation 之 EKF 產生衝突。
     - `cmd_vel_timeout: 3600.0`：當前實作之配置參數值為 3600.0 秒。
   - `joint_state_broadcaster` (`joint_state_broadcaster/JointStateBroadcaster`）：讀取硬體狀態並發布 `/joint_states`。

2. **硬體介面外掛與驅動封裝**：
   - `M1Hardware` (`hardware_interface::SystemInterface` 外掛）：實作 ros2_control 之生命週期（`on_init`, `on_configure`, `on_activate`, `on_deactivate` 等）與即時讀寫迴圈（`read()`, `write()`）。
   - `M1Driver`：以私有封裝之 `libmodbus` 實作序列通訊。採用 Modbus FC17（`FC_READ_WRITE_MULTIPLE`，`0x17` 功能碼）進行單一交易交換（Single Transaction Exchange）：在同一次通訊來回中同時寫入右輪（ID 1）與左輪（ID 2）目標速度並讀回輪端編碼器計數與轉速，以廣播群組 `0x65` 確保雙輪動作同步並壓低通訊延遲。
   - M1-owned configuration 由 `M1Driver` 在 configure 階段以標準 FC03 個別讀取，`M1Hardware` 僅在左右驅動器皆讀取成功後保留完整 snapshot；即時 read/write 迴圈不重讀設定。ROS 僅提供連線、機構與操作限制參數，不提供 encoder resolution 或 `motor_steps_per_rev`。
   - Encoder resolution 與 Multi-drive position-feedback scale 為不同語意。尚未建立有效位置換算時，硬體介面保持不可運動，activation 在 Servo-On 前回報失敗；實機位置回授目前仍受此條件阻擋。證據與待驗項目見 [M1 configuration and feedback evidence](../m1_settings/README.md)。

### Expected Normal Behavior

- 啟動 `base_control.launch.py` 後，`ros2_control_node` 載入 `M1Hardware`，開啟 `/dev/ttyUSB0` 並讀取兩台 M1 設定。只有位置回授格式與比例已建立且其他 activation 條件滿足時才致能；以下運轉行為以成功 activation 為前提。
- 當 `/diff_drive_controller/cmd_vel` 收到時戳速度指令時，控制器根據差速幾何計算輪速命令並施加限幅。
- `M1Hardware` 於每週期（30 Hz）調用 `M1Driver` 發送 FC17 指令至馬達驅動器，並同步讀回最新編碼器讀數。
- 控制器發布 `/diff_drive_controller/odom`，廣播器發布 `/joint_states`，底盤依指令順暢運行。

### Failure / Safety Behavior

- **指令超時處置**：若超過 `cmd_vel_timeout`（當前實作配置為 3600.0 秒）未收到新速度指令，`diff_drive_controller` 自動向硬體介面下達零速度命令。
- **序列通訊異常**：若發生 CRC 錯誤或讀寫超時（逾時門檻 50 ms），`M1Driver::exchange()` 回傳通訊失敗，`M1Hardware::write()`（或 `read()`）記錄錯誤日誌並向 `controller_manager` 回傳 `hardware_interface::return_type::ERROR`。系統未實作自主多重失敗復原狀態機（No autonomous multi-failure recovery sequencer）。
- **節點關閉與反致能**：當硬體介面進入 deactivation 或程序關閉（`on_deactivate` / `on_cleanup` / `on_shutdown`）時，`M1Hardware` 調用 `M1Driver::stop()`（發送 `CMD_JG` 速度 0）與 `M1Driver::disable()`（發送 `CMD_SVOFF` 馬達釋放），隨後關閉序列埠。

### Implementation References

- Launch File: `src/mobile_base_control/launch/base_control.launch.py`
- Base Control Parameter Config: `src/mobile_base_control/config/base_control_params.yaml`
- Hardware Plugin Source: `src/mobile_base_control/src/m1_hardware.cpp`, `include/mobile_base_control/m1_hardware.hpp`
- M1 Driver Source: `src/mobile_base_control/src/m1_driver.cpp`, `include/mobile_base_control/m1_driver.hpp`

## 10. Observability

### Responsibility

Observability 負責底盤運行資料之收集與轉發：
採集 AMR 運行過程中選定之核心指標、系統日誌與診斷事件 → 附加精確時戳與來源環境標記 → 透過有界記憶體佇列（Bounded Volatile Memory Buffer）暫存 → 非同步轉發至外部伺服器端點（InfluxDB 用於遙測時序指標，OpenSearch 用於系統日誌） → 供維運人員進行事後觀測與異常診斷。

本區域不具備自動化根因診斷功能。Observability 屬於獨立非關鍵功能，其網路中斷、轉發延遲或異常崩潰嚴格不得干擾底盤運動控制、狀態估測、導航安全或感測運作。

### Interfaces and Flow

```text
[AMR 運行資料來源]
  ├─ /odometry/filtered (nav_msgs/msg/Odometry) ────────┐
  ├─ /joint_states (sensor_msgs/msg/JointState) ────────┼──► ros_observability_adapter
  ├─ /diagnostics (diagnostic_msgs/msg/DiagnosticArray) ┘     │
  │                                                           ├─ 1.0 Hz 採樣五項核心遙測指標
  │                                                           ├─ BoundedTelemetryQueue (RAM 容量 60 筆, drop oldest)
  │                                                           │
  │                                                           ▼ (非同步 HTTP POST)
  │                                                       InfluxDB 伺服器端點 (時序指標)
  │
  └─ ROS 2 節點輸出與系統日誌 ─────────────────────────────► Fluent Bit 守護行程
                                                              │
                                                              ▼ (TCP/HTTP 轉發)
                                                          OpenSearch 伺服器端點 (日誌與事件)
```

1. **AMR 運行採集來源**：
   - `/odometry/filtered` (`nav_msgs/msg/Odometry`)：提取過濾後之線速度與角速度。
   - `/joint_states` (`sensor_msgs/msg/JointState`)：提取左、右驅動輪之轉速。
   - `/diagnostics` (`diagnostic_msgs/msg/DiagnosticArray`)：提取控制器硬體活動診斷狀態（`controller_manager: Hardware Components Activity`）。
   - 本地系統日誌：ROS 2 節點日誌與標準輸出串流。

2. **轉發輸出介面**：
   - **時序遙測指標**：透過 HTTP POST 協定發送至 InfluxDB 伺服器端點。
   - **系統日誌與事件**：透過 Fluent Bit 守護行程發送至 OpenSearch 伺服器端點。

### Implementation

1. **元件組成**：
   - `ros_observability_adapter` (`mobile_base_observability/observability_adapter_node.py`，Python ROS 2 節點）：
     - 訂閱 `/odometry/filtered`、`/joint_states` 與 `/diagnostics`。
     - 由內部計時器以配置頻率（`sample_rate_hz: 1.0` Hz）採樣最新觀測值。
     - 採用 `BoundedTelemetryQueue`（固定容量 60 筆記錄）於 RAM 中緩衝資料，實作 FIFO 溢位淘汰（Drop Oldest），嚴格不寫入本機硬碟 Spool 檔案。
     - 透過獨立執行緒 `TelemetrySender` 調用 `InfluxHttpWriter` 進行非同步 HTTP POST 批次推送（`http_timeout_seconds: 2.0` 秒）。
   - `Fluent Bit` (`mobile_base_observability/launch/fluent_bit.launch.py`，基於 `fluent-bit.conf`）：
     - 獨立行程，負責收集節點日誌並流式傳輸至 OpenSearch。

2. **啟動邊界事實**：
   - Observability 子系統並未納入規範啟動入口 `mobile_base.launch.py` 之中。
   - 其啟動分別由獨立之 launch 檔案（`observability_adapter.launch.py` 與 `fluent_bit.launch.py`）管理，屬於外部部署維運邊界。

3. **故障隔離與保護特性**：
   - **記憶體有界性**：緩衝佇列容量固定（預設 60 筆），記憶體佔用恆定。
   - **無本地磁碟耗損**：採純記憶體暫存，不向本機硬碟寫入快取檔案，避免嵌入式儲存損耗。
   - **單向無阻斷**：遙測發送過程於獨立背景執行緒進行，網路超時、伺服器離線或 HTTP 錯誤絕不阻斷 ROS 回呼函式或影響控制迴圈。

### Expected Normal Behavior

- 獨立啟動 `observability_adapter.launch.py` 與 `fluent_bit.launch.py` 並配置正確伺服器連線參數後，節點以 1.0 Hz 採樣五項核心遙測指標並傳送至 InfluxDB。
- Fluent Bit 監控系統日誌並持續轉發至 OpenSearch。

### Failure Behavior

- **伺服器斷線或網路逾時**：若 InfluxDB 端點無法連線，HTTP 發送於 2.0 秒後超時。緩衝佇列達到 60 筆上限後自動拋棄最舊數據，程序維持運作且不拋出未捕獲例外。當網路恢復後，後續採樣數據恢復正常推送。

### Implementation References

- Observability Adapter Launch: `src/mobile_base_observability/launch/observability_adapter.launch.py`
- Fluent Bit Launch: `src/mobile_base_observability/launch/fluent_bit.launch.py`
- Node Source: `src/mobile_base_observability/mobile_base_observability/observability_adapter_node.py`
- Telemetry & Queue Source: `src/mobile_base_observability/mobile_base_observability/telemetry.py`
- Influx Client Source: `src/mobile_base_observability/mobile_base_observability/influx.py`
- Fluent Bit Config: `src/mobile_base_observability/config/fluent-bit.conf`

## 11. System References

### 11.1 Runtime Availability

| 實作區域 (Implementation Area) | Mapping Mode | Navigation Mode | 啟動邊界與管理機制 |
|---|---|---|---|
| **1. Robot Model** | 啟用 (Active) | 啟用 (Active) | 納入 Common Bringup，由 `base_control.launch.py` 啟動 `robot_description.launch.py` |
| **2. Sensor Ingestion** | 啟用 (Active) | 啟用 (Active) | 納入 Common Bringup (`tdk_imu.launch.py`, `sick_dual_lidar.launch.py`) |
| **3. State Estimation** | 啟用 (Active) | 啟用 (Active) | 納入 Common Bringup (`kinematic_icp.launch.py`, `ekf.launch.py`) |
| **4. Mapping** | 啟用 (Active) | 未啟用 (Inactive) | `mobile_base.launch.py` 於 `mode:='mapping'` 時啟動 (`mapping.launch.py`) |
| **5. Localization** | 未啟用 (Inactive) | 啟用 (Active) | `mobile_base.launch.py` 於 `mode:='navigation'` 時啟動 (`localization.launch.py`) |
| **6. Navigation Target Admission** | 未啟用 (Inactive) | 可用 (Available) | 獨立 CLI 工具 (`navigate_to_station`) 或外部 Action Client |
| **7. Route-Assisted Navigation** | 未啟用 (Inactive) | 啟用 (Active) | `mobile_base.launch.py` 於 `mode:='navigation'` 時啟動 (`navigation.launch.py`) |
| **8. Precision Docking** | 未啟用 (Inactive) | 啟用 (Active) | 納入 `navigation.launch.py` 作為受管生命週期節點 (`docking_server`) |
| **9. Base Control** | 啟用 (Active) | 啟用 (Active) | 納入 Common Bringup，由 `base_control.launch.py` 啟動 |
| **10. Observability** | 可用 (Available) | 可用 (Available) | 獨立啟動邊界 (`observability_adapter.launch.py`, `fluent_bit.launch.py`)，非 canonical bringup 自動啟動 |

### 11.2 Production Resources

| 生產資源 (Resource) | 格式與規格 | 生產者 (Producer) | 主要消費者 (Consumer) | 執行期解析機制 (Runtime Resolution) |
|---|---|---|---|---|
| **Map Package** | `map.yaml` 與 `map.pgm` | Mapping (`save_map.sh` 調用 `map_saver_cli`) | Localization (`nav2_map_server`) | `site_resolution.py`（依 `site` 引數定位）或 CLI `map` 參數覆寫 |
| **Station Catalog** | `stations.yaml` | 離線場域工程定義 | Target Admission (`navigate_to_station`) | CLI 引數 `--catalog` 顯式傳入 |
| **Route Graph** | `route_graph.geojson` | 離線路網拓撲工程定義 | Route-Assisted Navigation (`route_server`) | `site_resolution.py`（依 `site` 引數定位）或 CLI `route_graph` 參數覆寫 |
| **Robot Description** | URDF / Xacro | 機器人機構模型 | `robot_state_publisher`, `controller_manager`, 代價地圖 | Launch 階段由 `xacro` 動態解析生成 |

說明：場域資源未由單一執行期節點進行集中代理；`site_resolution.py` 負責解析 launch 參數路徑，而 `stations.yaml` 則由操作端直接指定予目標接收工具。

### 11.3 TF Ownership

| 坐標轉換邊 (Transform Edge) | 父坐標 (Parent) | 子坐標 (Child) | 權威發布節點 (Authority Publisher) | 生效模式與生命週期 (Active Mode / Lifecycle) |
|---|---|---|---|---|
| `map -> odom` | `map` | `odom` | `slam_toolbox` (`async_slam_toolbox_node`) | 僅限 Mapping Mode |
| `map -> odom` | `map` | `odom` | `nav2_amcl` (`amcl`) | 僅限 Navigation Mode |
| `odom -> base_footprint` | `odom` | `base_footprint` | `robot_localization` (`ekf_node`) | Common（所有模式共用） |
| `base_footprint -> base_link` | `base_footprint` | `base_link` | `robot_state_publisher` | Common（靜態 URDF 描述） |
| `base_link -> base_lidar_link_FL` | `base_link` | `base_lidar_link_FL` | `robot_state_publisher` | Common（靜態 URDF 描述） |
| `base_lidar_link_FL -> base_lidar_link_FL_1` | `base_lidar_link_FL` | `base_lidar_link_FL_1` | `robot_state_publisher` | Common（靜態 URDF 描述） |
| `base_link -> base_lidar_link_BR` | `base_link` | `base_lidar_link_BR` | `robot_state_publisher` | Common（靜態 URDF 描述） |
| `base_lidar_link_BR -> base_lidar_link_BR_1` | `base_lidar_link_BR` | `base_lidar_link_BR_1` | `robot_state_publisher` | Common（靜態 URDF 描述） |
| `base_link -> base_imu_link` | `base_link` | `base_imu_link` | `robot_state_publisher` | Common（靜態 URDF 描述） |
| `base_link -> driving_wheel_link_L` | `base_link` | `driving_wheel_link_L` | `robot_state_publisher` | Common（基於 `/joint_states` 即時動態計算） |
| `base_link -> driving_wheel_link_R` | `base_link` | `driving_wheel_link_R` | `robot_state_publisher` | Common（基於 `/joint_states` 即時動態計算） |

權威發布唯一性事實：
- **`map -> odom` 互斥性**：Mapping Mode 與 Navigation Mode 屬於嚴格互斥之啟動模式，`slam_toolbox` 與 `amcl` 絕不同時運行，確保全域坐標轉換具備唯一權威發布者。
- **`odom -> base_footprint` 唯一性**：`diff_drive_controller` 配置 `enable_odom_tf: false`，不廣播 TF；`odom -> base_footprint` 唯一由 EKF 廣播。

### 11.4 Motion Command Flow

底盤運動控制拓撲如下：

```text
[Mapping Mode]
手動鍵盤遙控 (teleop_twist_keyboard)
      │
      │ (geometry_msgs/msg/TwistStamped)
      ▼
/diff_drive_controller/cmd_vel
      │
      ▼
diff_drive_controller (ros2_control)
      │
      ▼ (Modbus FC17 @ 230400 bps)
M1 馬達驅動器與輪系 (ID 1: 右輪, ID 2: 左輪)

[Navigation Mode]
路網導航: controller_server (MPPI) ──┐
                                     ├──► /diff_drive_controller/cmd_vel
精準對接: docking_server (對接控制) ─┘    (geometry_msgs/msg/TwistStamped)
                                                 │
                                                 ▼
                                      diff_drive_controller (ros2_control)
                                                 │
                                                 ▼ (Modbus FC17 @ 230400 bps)
                                      M1 馬達驅動器與輪系 (ID 1: 右輪, ID 2: 左輪)
```

架構運作事實：
- **直通主題無多路複用器**：當前架構未部署 `twist_mux` 節點，所有指令來源均重映射並直接發布至 `/diff_drive_controller/cmd_vel`。
- **操作流程互斥（Operational Exclusivity）**：底盤速度指令來源之互斥性屬於作業流程與運算節點調度的設計約定，而非底層節點或硬體層面之自動互鎖/仲裁機制（系統未部署 `twist_mux` 或類似之優先權仲裁節點）。在正常操作流程中，Mapping Mode 下僅由手動遙控發布指令；Navigation Mode 下，路網導航（`controller_server`）與精準對接（`docking_server`）屬於相繼觸發之不同任務階層，不同時發布指令。
- **指令超時保護**：`diff_drive_controller` 配置有 `cmd_vel_timeout: 3600.0` 秒，於指令串流中止且超時後自動向硬體介面下達零速度停機。
- **主動煞停控制**：正常任務結束時（導航抵達目標或對接就位），各上層控制器主動輸出全零之 `TwistStamped` 指令完成煞停。
