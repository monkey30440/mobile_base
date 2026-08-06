# Subsystem Design

## SUB-001 底盤控制

### 目的

底盤控制子系統負責接收 AMR 運動命令，控制左右輪驅動器完成車體運動，並提供底盤運動資訊作為定位、建圖與導航之基礎。

---

## 對應需求

| Requirement |
|-------------|
| SYS-002 |
| SYS-005 |

---

## 系統邊界

| 項目 | 規格 |
|------|------|
| 運算平台 | Jetson AGX Orin Developer Kit |
| 馬達驅動器 | DEXMART M1C-N016RE ×2 |
| 通訊介面 | RS-485 |
| 通訊協議 | Modbus Multi-drive 2.0 |
| 裝置 | `/dev/ttyUSB0` |
| ROS | ROS 2 Jazzy |

---

## 系統職責

- 接收 AMR 運動命令。
- 執行差速運動學計算。
- 控制左右輪速度。
- 讀取左右輪運動回授。
- 發布底盤運動資訊。
- 提供驅動器狀態。

---

## 邏輯架構

```text
                cmd_vel
                   │
                   ▼
          Differential Kinematics
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 Left Wheel Command     Right Wheel Command
        │                     │
        └──────────┬──────────┘
                   ▼
         Modbus Multi-drive 2.0
                   │
             RS-485 Bus
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
     Left Driver         Right Driver
        │                     │
        └──────────┬──────────┘
                   ▼
          Wheel Feedback
                   │
                   ▼
          ROS 2 Interface
```

---

## ROS Interface

### Subscribe

| Topic | Type |
|------|------|
| `/cmd_vel` | `geometry_msgs/Twist` |

### Publish

| Topic | 說明 |
|------|------|
| `/odom/raw` | 底盤運動資訊 |
| `/wheel_states` | 左右輪運動回授 |
| `/driver/status` | Driver 狀態 |

---

## External Interface

| 裝置 | 介面 |
|------|------|
| DEXMART M1 Driver | RS-485 |
| Multi-drive 2.0 | Modbus RTU |

---

## 系統參數

### Vehicle Parameters

| 參數 | 初版來源 |
|------|----------|
| Wheel Radius | 現有專案 Baseline |
| Wheel Separation | 現有專案 Baseline |
| Gear Ratio | 現有專案 Baseline |

上述參數於 Hardware Bring-up 完成後，以實機量測結果更新。

### Driver Parameters

以下參數依驅動器設定決定：

- Driver ID
- Baud Rate
- Control Mode
- Encoder Resolution
- Maximum Motor RPM
- Acceleration
- Deceleration
- Torque Limit

初版依官方文件建立設定，Hardware Bring-up 以驅動器實際設定為準。

---

## 設計依據

SUB-001 設計依下列順序完成：

1. 官方文件
2. 既有實作
3. Hardware Bring-up
4. 實機量測
5. Hardware Configuration

---

## 軟體組成

```text
mobile_base_driver
├── driver
├── modbus
├── kinematics
├── odometry
└── parameter
```

Package 結構於 Implementation 階段確認。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|------|------|
| Driver 通訊 | 可建立 RS-485 通訊 |
| Driver 控制 | 左右輪可獨立控制 |
| 差速控制 | AMR 可完成直行與原地旋轉 |
| Wheel Feedback | 可持續取得左右輪回授 |
| Odometry | 可持續發布底盤運動資訊 |
| 長時間運轉 | 建圖期間穩定運作 |

---

## Traceability

| Requirement | Subsystem |
|-------------|-----------|
| SYS-002 | SUB-001 |
| SYS-005 | SUB-001 |

## SUB-002 LiDAR 感知

### 目的

LiDAR 感知子系統負責取得兩顆 SICK picoScan150 的環境掃描資料，發布標準 ROS 2 LaserScan Topic，並提供下游建圖、雷射里程估測與導航使用。

---

### 對應需求

| Requirement |
|---|
| SYS-003 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| LiDAR | SICK picoScan150 ×2 |
| 通訊介面 | Ethernet |
| 資料來源 | 前方 LiDAR、後方 LiDAR |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 座標模型 | 既有 URDF |

---

### 系統職責

- 建立兩顆 LiDAR Ethernet 通訊。
- 接收兩顆 LiDAR 掃描資料。
- 發布標準 ROS 2 LaserScan Topic。
- 為每顆 LiDAR 指定固定 Frame ID。
- 提供 LiDAR 裝置狀態。

---

### 邏輯架構

```text
 Front picoScan150                 Rear picoScan150
         │                                 │
         ▼                                 ▼
 Front LiDAR Driver               Rear LiDAR Driver
         │                                 │
         ▼                                 ▼
   /scan_front                    /scan_rear
         │                                 │
         ▼                                 ▼
 front_laser_frame               rear_laser_frame
```

---

### ROS Interface

#### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/scan_front` | `sensor_msgs/msg/LaserScan` | 前方 LiDAR 掃描資料 |
| `/scan_rear` | `sensor_msgs/msg/LaserScan` | 後方 LiDAR 掃描資料 |

---

### TF Interface

| Parent Frame | Child Frame | 來源 |
|---|---|---|
| `base_link` | `front_laser_frame` | URDF |
| `base_link` | `rear_laser_frame` | URDF |

LiDAR 安裝位置與座標方向以既有 URDF 為初版 Baseline，並透過實機掃描確認。

---

### 資料內容

| 欄位 | 初版處理 |
|---|---|
| `header.stamp` | 使用 Driver 產生之訊息時間 |
| `header.frame_id` | 對應 LiDAR Frame |
| `angle_min` | Driver Baseline |
| `angle_max` | Driver Baseline |
| `angle_increment` | Driver Baseline |
| `time_increment` | Driver Baseline |
| `scan_time` | Driver Baseline |
| `range_min` | Driver Baseline |
| `range_max` | Driver Baseline |
| `ranges` | LiDAR 距離資料 |
| `intensities` | LiDAR 強度資料（依 Driver 支援） |

---

### 系統參數

| 參數 | 初版來源 |
|---|---|
| Device IP | LiDAR 現有設定 |
| Host IP | 網路設定 |
| Scan Profile | Driver Baseline |
| Scan Frequency | Driver Baseline |
| Angular Resolution | Driver Baseline |
| Frame ID | `front_laser_frame`、`rear_laser_frame` |
| Topic | `/scan_front`、`/scan_rear` |

LiDAR 網路設定與掃描參數於 Hardware Bring-up 完成後，以實機設定為準。

---

### 設計依據

SUB-002 依下列順序完成設計確認：

1. SICK 官方文件。
2. 既有 ROS Driver。
3. Hardware Bring-up。
4. 實機 Topic 與 TF 驗證。
5. 下游應用需求。

官方文件用於確認裝置能力與通訊方式；既有 Driver 用於建立初版通訊與參數 Baseline；兩者皆透過實機驗證完成最終確認。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| 網路通訊 | Jetson 可連線兩顆 LiDAR |
| Driver 啟動 | 前後 LiDAR Driver 可持續運作 |
| 前方掃描 | `/scan_front` 持續發布有效資料 |
| 後方掃描 | `/scan_rear` 持續發布有效資料 |
| 訊息格式 | `sensor_msgs/msg/LaserScan` |
| Frame ID | Frame 與實際安裝位置一致 |
| 掃描方向 | 雷射掃描方向與實際安裝方向一致 |
| 持續運轉 | 建圖期間持續發布有效資料 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-003 | SUB-002 |

## SUB-003 IMU 感知

### 目的

IMU 感知子系統負責取得 TDK IIM-42652 的角速度與線性加速度資料，轉換為標準 ROS 2 IMU 訊息，並提供下游運動估測使用。

---

### 對應需求

| Requirement |
|---|
| SYS-004 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| IMU | TDK IIM-42652 |
| 感測能力 | 3 軸陀螺儀、3 軸加速度計 |
| 連接介面 | USB Serial |
| 裝置 | `/dev/ttyACM0` |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 座標模型 | 既有 URDF |

IIM-42652 為六軸慣性感測器，提供三軸角速度與三軸線性加速度量測。:contentReference[oaicite:0]{index=0}

---

### 系統職責

- 建立 `/dev/ttyACM0` 通訊。
- 接收 IMU 資料封包。
- 驗證封包完整性。
- 解析三軸角速度資料。
- 解析三軸線性加速度資料。
- 將量測資料轉換為 SI 單位。
- 發布標準 ROS 2 IMU Topic。
- 為 IMU 訊息提供時間戳記與 Frame ID。

---

### 邏輯架構

```text
TDK IIM-42652
      │
      ▼
 /dev/ttyACM0
      │
      ▼
 IMU Driver
      │
      ├── Packet Validation
      ├── Angular Velocity
      ├── Linear Acceleration
      ├── Unit Conversion
      ├── Timestamp
      └── Frame ID
      │
      ▼
 /imu/data_raw
 ```

 ## SUB-004 Wheel Odometry

### 目的

Wheel Odometry 子系統負責根據底盤左右輪回授資訊計算 AMR 運動狀態，發布標準 ROS 2 Odometry 訊息，提供 Robot Localization EKF 使用。

---

### 對應需求

| Requirement |
|---|
| SYS-005 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| 資料來源 | SUB-001 底盤控制 |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 運動模型 | Differential Drive |
| 座標模型 | 既有 URDF |

---

### 系統職責

- 接收左右輪運動回授。
- 執行差速輪運動學計算。
- 推算車體線速度。
- 推算車體角速度。
- 推算車體位姿增量。
- 發布標準 ROS 2 Odometry。
- 發布 Wheel Odometry TF。

---

### 邏輯架構

```text
Left Wheel Feedback
          │
Right Wheel Feedback
          │
          ▼
 Differential Drive Kinematics
          │
          ▼
 Wheel Odometry
          │
     ┌────┴────┐
     ▼         ▼
 /wheel_odom   TF
```

---

### ROS Interface

#### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/wheel_states` | 自定義訊息 | 左右輪運動回授 |

#### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/wheel_odom` | `nav_msgs/msg/Odometry` | Wheel Odometry |

---

### TF Interface

| Parent | Child |
|---|---|
| `odom` | `base_footprint` |

TF 發布策略於 Robot Localization 整合時統一確認。

---

### 資料內容

| 欄位 | 初版處理 |
|---|---|
| Position | Differential Drive 推算 |
| Orientation | Differential Drive 推算 |
| Linear Velocity | 左右輪速度計算 |
| Angular Velocity | 左右輪速度計算 |
| Covariance | 初版使用 Baseline |

---

### 系統參數

| 參數 | 初版來源 |
|---|---|
| Wheel Radius | Vehicle Baseline |
| Wheel Separation | Vehicle Baseline |
| Gear Ratio | Vehicle Baseline |
| Encoder Resolution | Driver Baseline |

Vehicle 幾何參數沿用既有 Baseline，並於 Hardware Bring-up 完成實機確認。

---

### 設計依據

SUB-004 依下列順序完成設計確認：

1. Differential Drive 運動模型。
2. 既有 Driver Baseline。
3. Hardware Bring-up。
4. Wheel Odometry 實機驗證。
5. Robot Localization 輸入需求。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Wheel Feedback | 可持續取得左右輪回授 |
| Topic 發布 | `/wheel_odom` 持續發布 |
| 訊息格式 | `nav_msgs/msg/Odometry` |
| 直線運動 | 里程方向與實際一致 |
| 原地旋轉 | 角速度方向與實際一致 |
| Frame | TF 關係正確 |
| 持續運轉 | 建圖期間持續發布資料 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-005 | SUB-004 |

## SUB-005 RF2O Odometry

### 目的

RF2O Odometry 子系統負責根據單一 LiDAR Scan Topic 估測 AMR 平面運動，發布標準 ROS 2 Odometry 訊息，並提供 Robot Localization EKF 使用。

---

### 對應需求

| Requirement |
|---|
| SYS-003 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| 演算法 | RF2O Laser Odometry |
| 資料來源 | SUB-002 LiDAR 感知 |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 運動模型 | 平面運動 |
| 輸入型別 | `sensor_msgs/msg/LaserScan` |
| 輸出型別 | `nav_msgs/msg/Odometry` |

RF2O 以連續二維雷射掃描估測相對運動，初版作為獨立里程資訊來源。:contentReference[oaicite:0]{index=0}

---

### 系統職責

- 接收指定 LiDAR Scan Topic。
- 依連續掃描資料估測平面位姿變化。
- 計算 AMR 線速度與角速度。
- 發布標準 ROS 2 Odometry 訊息。
- 為輸出訊息提供時間戳記與 Frame ID。

---

### 邏輯架構

```text
/scan_front 或 /scan_rear
          │
          ▼
 RF2O Laser Odometry
          │
          ├── Position
          ├── Orientation
          ├── Linear Velocity
          └── Angular Velocity
          │
          ▼
     /rf2o_odom
```

## SUB-006 Robot Localization EKF

### 目的

Robot Localization EKF 子系統負責融合 Wheel Odometry、RF2O Odometry 與 IMU 資料，建立 AMR 連續且一致的平面里程資訊，並提供建圖與導航使用。

---

### 對應需求

| Requirement |
|---|
| SYS-003 |
| SYS-004 |
| SYS-005 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| 套件 | `robot_localization` |
| 濾波器 | Extended Kalman Filter |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 運動模型 | 平面運動 |
| 輸出型別 | `nav_msgs/msg/Odometry` |

---

### 系統職責

- 接收 Wheel Odometry。
- 接收 RF2O Odometry。
- 接收 IMU 原始量測資料。
- 融合平面位置、速度與角速度資訊。
- 發布系統里程資訊。
- 發布系統里程 TF。
- 提供連續運動估測供 SLAM Toolbox 與 Navigation 使用。

---

### 邏輯架構

```text
/wheel_odom
      │
/rf2o_odom
      │
/imu/data_raw
      │
      ▼
Robot Localization EKF
      │
      ├── Position
      ├── Orientation
      ├── Linear Velocity
      └── Angular Velocity
      │
      ▼
    /odom
      │
      ▼
odom → base_footprint
```

## SUB-007 SLAM Toolbox

### 目的

SLAM Toolbox 子系統負責根據 LiDAR 掃描資料與系統里程資訊建立二維 Occupancy Grid 地圖，並提供地圖資料與座標轉換。

---

### 對應需求

| Requirement |
|---|
| SYS-001 |
| SYS-006 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| 套件 | slam_toolbox |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 地圖型式 | Occupancy Grid |
| 建圖模式 | Online Mapping |

---

### 系統職責

- 接收 LiDAR 掃描資料。
- 接收系統里程資訊。
- 執行二維同步定位與建圖。
- 建立 Occupancy Grid。
- 發布地圖 Topic。
- 發布 Map TF。
- 提供地圖儲存服務。

---

### 邏輯架構

```text
/scan_front 或 /scan_rear
            │
            │
          /odom
            │
            ▼
      SLAM Toolbox
            │
      ┌─────┴─────┐
      ▼           ▼
    /map     map → odom
```

---

### ROS Interface

#### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| Scan Topic | `sensor_msgs/msg/LaserScan` | LiDAR 掃描資料 |
| `/odom` | `nav_msgs/msg/Odometry` | 系統里程資訊 |

#### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/map` | `nav_msgs/msg/OccupancyGrid` | 二維地圖 |

---

### TF Interface

| Parent | Child |
|---|---|
| `map` | `odom` |

`map → odom` TF 由 SLAM Toolbox 單一發布。

---

### 輸入資料

| 項目 | 初版來源 |
|---|---|
| Scan Topic | Hardware Bring-up 選定之 LiDAR Topic |
| Odometry | `/odom` |

LiDAR Scan Topic 依 SUB-005 完成之實機測試結果決定。

---

### 系統參數

| 參數 | 初版設定 |
|---|---|
| Mapping Mode | Online |
| Scan Topic | Hardware Bring-up 決定 |
| Odom Topic | `/odom` |
| Map Frame | `map` |
| Odom Frame | `odom` |
| Base Frame | `base_footprint` |

其餘 SLAM 參數採用 slam_toolbox Baseline，並於實機建圖完成後調整。

---

### 設計依據

SUB-007 依下列順序完成設計確認：

1. slam_toolbox 文件。
2. SUB-002 LiDAR。
3. SUB-006 Robot Localization。
4. Hardware Bring-up。
5. 建圖結果驗證。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Scan 接收 | 持續接收 LiDAR Topic |
| Odometry 接收 | 持續接收 `/odom` |
| 地圖建立 | `/map` 持續更新 |
| Topic 格式 | `nav_msgs/msg/OccupancyGrid` |
| TF 發布 | `map → odom` 持續發布 |
| 建圖品質 | 地圖與實際環境一致 |
| 長時間建圖 | 建圖期間持續穩定運作 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-001 | SUB-007 |
| SYS-006 | SUB-007 |

## SUB-008 Map Management

### 目的

Map Management 子系統負責管理二維地圖之儲存與載入，提供建圖成果保存與後續導航使用。

---

### 對應需求

| Requirement |
|---|
| SYS-007 |
| SYS-008 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| ROS 套件 | nav2_map_server |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 地圖格式 | Occupancy Grid |

---

### 系統職責

- 接收目前地圖。
- 儲存地圖。
- 載入地圖。
- 管理地圖檔案。
- 提供地圖服務。

---

### 邏輯架構

```text
        /map
          │
          ▼
  Map Management
      │       │
      ▼       ▼
 Save Map  Load Map
      │       │
      └──┬────┘
         ▼
 map.yaml
 map.pgm
```

---

### ROS Interface

#### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/map` | `nav_msgs/msg/OccupancyGrid` | 建圖結果 |

#### Service

| Service | 說明 |
|---|---|
| Save Map | 儲存目前地圖 |
| Load Map | 載入指定地圖 |

---

### 地圖格式

| 檔案 | 說明 |
|---|---|
| `map.yaml` | 地圖設定 |
| `map.pgm` | Occupancy Grid |

---

### 儲存位置

初版採固定目錄：

```text
maps/
```

每張地圖包含：

```text
maps/
└── map_name/
    ├── map.yaml
    └── map.pgm
```

---

### 系統參數

| 參數 | 初版設定 |
|---|---|
| Map Format | Occupancy Grid |
| Save Path | `maps/` |
| File Name | 使用者指定 |
| Overwrite | 允許覆寫同名地圖 |

---

### 設計依據

SUB-008 依下列順序完成設計確認：

1. nav2_map_server 文件。
2. SUB-007 SLAM Toolbox。
3. Hardware Bring-up。
4. 地圖儲存驗證。
5. 地圖載入驗證。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| 地圖接收 | 可接收 `/map` |
| 地圖儲存 | 成功產生 `map.yaml` 與 `map.pgm` |
| 地圖載入 | 成功載入指定地圖 |
| 地圖一致性 | 載入後內容與儲存前一致 |
| 多次操作 | 可重複執行儲存與載入 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-007 | SUB-008 |
| SYS-008 | SUB-008 |

## SUB-009 Task Interface

### 目的

Task Interface 子系統負責接收使用者透過終端提交之路網站點移動任務，將任務交付導航系統執行，並提供任務狀態與完成結果。

---

### 對應需求

| Requirement |
|---|
| SYS-012 |
| SYS-017 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| 操作者 | 開發人員、測試人員 |
| 操作方式 | 終端命令 |
| 任務類型 | 路網站點移動任務 |
| 任務輸入 | Target Station |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |

---

### 系統職責

- 接收使用者指定之目標站點。
- 建立路網站點移動任務。
- 將目標站點交付 Goal Management。
- 啟動導航任務。
- 接收導航任務狀態。
- 顯示任務執行狀態。
- 顯示任務完成結果。

---

### 邏輯架構

```text
使用者
  │
  ▼
終端命令
  │
  ▼
Task Interface
  │
  ├── Target Station
  ├── Task Identifier
  └── Task Status
  │
  ▼
Goal Management
  │
  ▼
Navigation System
  │
  ▼
Task Result
  │
  ▼
使用者
```

