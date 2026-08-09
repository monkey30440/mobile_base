# Subsystem Design

本文件定義 `mobile_base` 各子系統之目的、職責、系統邊界、介面、設計依據與驗證方式，作為系統實作、整合測試與維護之依據。

子系統依功能劃分如下：

| ID | Subsystem |
|---|---|
| SUB-001 | Drive Hardware Interface |
| SUB-002 | LiDAR Perception |
| SUB-003 | IMU Perception |
| SUB-004 | Differential Drive Controller |
| SUB-005 | RF2O Odometry |
| SUB-006 | Robot Localization EKF |
| SUB-007 | SLAM Toolbox |
| SUB-008 | Map Management |
| SUB-009 | Task Interface |
| SUB-010 | Target Resolution |
| SUB-011 | Navigation |
| SUB-012 | Robot Description |

---

# SUB-001 Drive Hardware Interface

## 目的

Drive Hardware Interface 子系統負責 DEXMART M1 驅動器之通訊與生命週期管理，
向 ros2_control 框架提供左右輪之輪端狀態與速度命令介面。

本子系統為 ros2_control 之硬體層，不含差速運動學與里程計算；
該部分由 **SUB-004 Differential Drive Controller** 以 `diff_drive_controller` 完成。

---

## 對應需求

| Requirement |
|---|
| SYS-022 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 底盤型式 | Differential Drive |
| 馬達驅動器 | DEXMART M1C-N016RE ×2 |
| 通訊介面 | RS-485 |
| 通訊協議 | Modbus Multi-drive 2.0 |
| Device | `/dev/ttyUSB0` |
| 控制框架 | ros2_control |
| 元件型式 | `hardware_interface::SystemInterface` 插件 |

---

## 系統職責

- 建立並維持 RS-485 Multi-drive 2.0 通訊。
- 管理驅動器生命週期（組態驗證、激磁、解除激磁）。
- 讀取左右輪運動回授並解碼為輪端物理量。
- 處理編碼器 turns 繞回，提供單調連續之輪端位置。
- 接收輪端速度命令並轉為馬達端命令下達驅動器。
- 提供驅動器狀態與警報。

Base Control 不負責：

- 差速運動學（`cmd_vel` ↔ 輪速換算）。
- 里程計算與 `/odom` 發布。
- TF 發布。

上述由 **SUB-004 Differential Drive Controller** 負責。

---

## 邏輯架構

```text
        controller_manager
                │
   read()  ┌────┴────┐  write()
           ▼         ▼
     State If.   Command If.
   (輪端 rad,    (輪端 rad/s)
    rad/s)           │
           ▲         ▼
           └────┬────┘
                │
       SUB-001 Drive Hardware Interface
       ┌────────┴────────┐
       │  Encoder 解碼   │
       │  turns 繞回累加 │
       │  單位換算       │
       │  驅動器生命週期 │
       └────────┬────────┘
                ▼
     Modbus Multi-drive 2.0
                │
             RS-485
                │
      ┌─────────┴─────────┐
      ▼                   ▼
 Left Driver         Right Driver
```

---

## ros2_control Interface

本子系統不直接發布或訂閱 Topic，而是向 `controller_manager`
匯出下列介面；Topic 層由上層 controller 與 broadcaster 提供。

### State Interfaces

| Joint | Interface | 單位 | 說明 |
|---|---|---|---|
| `driving_wheel_joint_L` | `position` | rad | 輪端累積角位置 |
| `driving_wheel_joint_L` | `velocity` | rad/s | 輪端角速度 |
| `driving_wheel_joint_R` | `position` | rad | 輪端累積角位置 |
| `driving_wheel_joint_R` | `velocity` | rad/s | 輪端角速度 |

位置為單調連續值，已完成 turns 繞回處理；
位置與速度皆為輪端（減速機輸出端）物理量，並已套用方向修正。

### Command Interfaces

| Joint | Interface | 單位 |
|---|---|---|
| `driving_wheel_joint_L` | `velocity` | rad/s |
| `driving_wheel_joint_R` | `velocity` | rad/s |

### 生命週期

| ros2_control 狀態轉換 | 動作 |
|---|---|
| `on_init` / `on_configure` | 開啟序列埠、驗證驅動器組態（`02-14`、`01-06`） |
| `on_activate` | 解除 FREE、SERVO-EN ON |
| `on_deactivate` | 停止運動、SERVO-EN OFF |
| `on_cleanup` / `on_shutdown` | 關閉序列埠 |

解除激磁為安全關鍵動作，左右輪獨立嘗試並重試，單顆失敗不得中斷另一顆。

### 驅動器狀態

驅動器警報與通訊狀態以 `diagnostic_msgs/msg/DiagnosticArray`
發布於 `/driver/status`，供操作人員與診斷工具使用。

---

## External Interface

| 裝置 | 介面 |
|---|---|
| Left Driver | RS-485 |
| Right Driver | RS-485 |

Driver Register、Control Word 與 Status Word 已於 2026-08-07 實機確認。

左右輪以 Multi-drive 2.0 FC17h 群組讀寫，單一封包同時下達雙輪速度命令並讀回回授；
個別驅動器參數以 FC03／FC06 存取。

---

## 系統參數

### 傳動參數

| 參數 | 採用值 | 來源 |
|---|---|---|
| Gear Ratio | 20.0 | 既有 Baseline，尚未經實機量測驗證 |

Gear Ratio 用於馬達端與輪端之換算，為 SUB-001 之唯一車體相關參數。

Wheel Radius 與 Wheel Separation **不屬於本子系統**，
由 **SUB-004 Differential Drive Controller** 單一持有，
使兩者不致於兩處各自設定而產生無聲不一致。

---

### Driver Parameters

下列參數已於 2026-08-07 實機確認：

| 參數 | 值 |
|---|---|
| Driver ID | 右輪 1、左輪 2 |
| Baud Rate | 230400（8N1） |
| Encoder Resolution（`01-06`） | 2500 pulse/rev（單相） |
| 位置命令格式（`02-14`） | 0：Index(turns) + pulse |
| PDO Mapping（`09-26`） | 0 |

下列參數依實機調校決定，Stage 3 確認：

- Control Mode
- Maximum Motor RPM
- Acceleration / Deceleration
- Torque Limit

---

### Encoder 位置解碼

驅動器維持出廠預設 `02-14 = 0`，位置以 Index(turns) 與 pulse 兩個 word 表示。

輪端位置計算方式：

```text
position = turns × (Encoder Resolution × 4) + pulse
```

設計原則：

- 驅動器端不做持久化設定，行為完全由本專案決定，更換驅動器可直接使用。
- 每轉步數由 `01-06` 推導，不寫死常數。
- 啟動時讀取並驗證 `02-14` 與 `01-06`；`02-14` 非 0 時視為組態錯誤並回報，
  避免驅動器更換或重置後產生無聲之里程誤差。

#### Turns 溢位處理

turns 欄位為 signed 16-bit（−32768 ~ +32767）。驅動器 `05-03` = 2
（關閉 Overflow 保護，實機確認）時不觸發警報，計數器靜默繞回。

以本車參數計算，繞回發生於約 823 m 行駛距離（0.5 m/s 約 27 分鐘），
落在單次建圖任務時間內，故必須處理。

SUB-001 以軟體偵測繞回並累加，對外提供單調連續之輪端位置，
下游子系統無須自行處理繞回或加裝位移跳變濾除。

---

## 軟體組成

```text
base_control
├── Modbus Transport      RS-485 封包、CRC、收發
├── Driver Interface      寄存器語意、生命週期、警報
├── Encoder Decoder       turns 繞回累加、單位換算
├── Hardware Interface    ros2_control SystemInterface 插件
└── Diagnostics           /driver/status
```

實作為 `hardware_interface::SystemInterface` 插件（C++，pluginlib 匯出），
由 `controller_manager` 載入，不獨立成為 ROS 節點。

---

## 設計依據

SUB-001 依下列順序完成設計確認：

1. DEXMART Driver 官方文件。
2. Modbus Multi-drive 2.0 通訊協議。
3. 現有專案 Baseline。
4. Hardware Bring-up 與協議實機驗證。
5. ros2_control `hardware_interface` 介面規範。
6. Driver Configuration 確認。

設計原則：

- 不重新設計 Driver Protocol，沿用既有成熟 Driver 設定。
- 不自行實作差速運動學、里程積分與控制迴圈排程，
  改由 ros2_control 與 `diff_drive_controller` 提供。
- 自訂程式碼僅限於 ros2_control 未涵蓋之 M1 專屬協議部分。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Driver 通訊 | 可建立 RS-485 通訊 |
| Driver 控制 | 左右輪可獨立控制 |
| Hardware Interface 載入 | `controller_manager` 可載入並啟用本插件 |
| State Interface | 輪端 position／velocity 持續更新且數值正確 |
| Position 連續性 | 跨 turns 繞回邊界後位置仍單調連續 |
| Command Interface | 輪端速度命令可正確驅動左右輪 |
| 生命週期 | activate 激磁、deactivate 解除激磁，皆可重複執行 |
| 異常關閉 | SIGTERM 下仍完成解除激磁 |
| 警報處理 | 驅動器警報可被偵測、回報並回復 |
| 長時間運轉 | 建圖與導航期間持續穩定運作 |

Stage 1／Stage 2 已於手搓實作上驗證通訊協議、編碼器解碼、繞回處理與
關閉行為（2026-08-07）；上述項目須於 ros2_control 實作完成後重新驗證。

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-022 | SUB-001 |

# SUB-002 LiDAR Perception

## 目的

LiDAR Perception 子系統負責取得前後兩顆 LiDAR 的原始掃描資料，轉換為標準 ROS 2 `LaserScan` 訊息，提供雷射里程估測、建圖、定位與導航使用。

---

## 對應需求

| Requirement |
|---|
| SYS-003 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| LiDAR | SICK picoScan150 ×2 |
| 安裝方式 | 對角配置（前左、後右） |
| 通訊介面 | Ethernet |
| Coordinate Frame | SUB-012 Robot Description |

---

## 系統職責

- 建立前左 LiDAR 通訊。
- 建立後右 LiDAR 通訊。
- 接收兩顆 LiDAR 掃描資料。
- 分別發布標準 ROS 2 `LaserScan` Topic。
- 提供各 LiDAR 裝置狀態。
- 保留並提供原始 LiDAR 量測資料。

LiDAR Perception 僅負責提供原始 LiDAR 資料。

是否需要資料融合，由下游子系統依介面能力與實機需求決定。

---

## 邏輯架構

```text
Front-Left picoScan150                    Back-Right picoScan150
        │                                    │
        ▼                                    ▼
Front-Left LiDAR Driver                   Back-Right LiDAR Driver
        │                                    │
        ▼                                    ▼
  /scan_front_left                          /scan_back_right
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
              Downstream Consumers
```

兩顆 LiDAR 分別發布 `/scan_front_left` 與 `/scan_back_right`。

初版維持兩個獨立原始 Topic。

### 對角安裝

兩顆 LiDAR 採對角配置：一顆位於車體前左，一顆位於車體後右。
/home/zzz/mobile_base/ref/FIH_AMR_ROBOT_V2.0_0731
此配置使兩顆 LiDAR 之視野互補，涵蓋車體四周並消除單側盲區；
各顆本身不足以單獨涵蓋全周，故下游若僅取用單一來源，
須確認該來源之視野足以滿足其功能需求。

---

## LiDAR 資料使用原則

- SUB-002 持續發布原始 `/scan_front_left` 與 `/scan_back_right`。
- 下游可直接接收多個原始 LiDAR Topic 時，直接使用原始資料。
- 下游僅需單一來源且單一原始 Topic 可滿足需求時，使用選定之原始 Topic。
- 僅於下游介面無法直接接收所需原始資料，且單一來源無法滿足功能需求時，才評估 LaserScan Fusion。
- LaserScan Fusion 屬於依下游需求導入之相容層，不屬於 SUB-002 預設功能。

---

## ROS Interface

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/scan_front_left` | `sensor_msgs/msg/LaserScan` | 前左 LiDAR 原始掃描資料 |
| `/scan_back_right` | `sensor_msgs/msg/LaserScan` | 後右 LiDAR 原始掃描資料 |

SUB-002 不發布預設融合後 Scan Topic。

---

## TF Interface

| Parent Frame | Child Frame |
|---|---|
| `base_link` | `base_lidar_link_FL` |
| `base_link` | `base_lidar_link_BR` |

LiDAR 安裝位置與姿態由 **SUB-012 Robot Description** 管理。

初版沿用既有 URDF Baseline，Hardware Bring-up 完成後以實機掃描確認。

---

## LaserScan

每顆 LiDAR 獨立發布一組 `sensor_msgs/msg/LaserScan`。

| 欄位 | 初版處理 |
|---|---|
| `header.stamp` | 使用 Driver 產生之訊息時間 |
| `header.frame_id` | 對應 LiDAR Frame |
| `angle_min` | Driver 原始設定 |
| `angle_max` | Driver 原始設定 |
| `angle_increment` | Driver 原始設定 |
| `time_increment` | Driver 原始設定 |
| `scan_time` | Driver 原始設定 |
| `range_min` | Driver 原始設定 |
| `range_max` | Driver 原始設定 |
| `ranges` | 原始距離資料 |
| `intensities` | Driver 支援時提供 |

SUB-002 不額外修改量測內容。

---

## 系統參數

### Device Parameters

| 參數 | 初版來源 |
|---|---|
| Device IP | 現有 Baseline |
| Host IP | 網路設定 |
| Front-Left Frame ID | `base_lidar_link_FL` |
| Back-Right Frame ID | `base_lidar_link_BR` |
| Front-Left Topic | `/scan_front_left` |
| Back-Right Topic | `/scan_back_right` |

### Scan Parameters

下列參數依 Driver 與 LiDAR 設定決定：

- Scan Frequency
- Angular Resolution
- Angle Range
- Range Min
- Range Max
- Time Increment
- Scan Time

初版沿用官方 Driver Baseline，Hardware Bring-up 完成後確認。

---

## 軟體組成

```text
lidar_perception
├── Front-Left LiDAR Driver
├── Back-Right LiDAR Driver
├── Ethernet Transport
├── Parameter Manager
└── Diagnostics
```

初版優先採用官方 ROS Driver，不重新實作 LiDAR 通訊與資料解析。

Package 結構於 Implementation 階段確認。

---

## 設計依據

SUB-002 依下列順序完成設計確認：

1. SICK picoScan150 官方文件。
2. 官方 ROS Driver。
3. 現有專案 Baseline。
4. Hardware Bring-up。
5. TF 與掃描方向驗證。
6. 下游應用輸入能力確認。
7. 實機功能驗證。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Front-Left Driver | 可持續接收前左 LiDAR |
| Back-Right Driver | 可持續接收後右 LiDAR |
| Front-Left Topic | `/scan_front_left` 持續發布 |
| Back-Right Topic | `/scan_back_right` 持續發布 |
| Message Type | 兩個 Topic 均為 `sensor_msgs/msg/LaserScan` |
| Frame ID | 與 SUB-012 定義一致 |
| Scan Direction | 與實際安裝方向一致 |
| Raw Data | 下游可直接取得兩個原始 Topic |
| Downstream Input | 完成各下游應用之輸入能力確認 |
| Fusion Decision | 僅於原始資料無法滿足需求時評估融合 |
| Network Stability | 長時間持續穩定通訊 |
| Long Duration | 建圖與導航期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-003 | SUB-002 |

# SUB-003 IMU Perception

## 目的

IMU Perception 子系統負責取得 TDK IIM-42652 的角速度與線性加速度資料，轉換為標準 ROS 2 `Imu` 訊息，並提供里程估測、定位與導航使用。

---

## 對應需求

| Requirement |
|---|
| SYS-004 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| IMU | TDK IIM-42652 |
| 感測能力 | 3 軸角速度、3 軸線性加速度 |
| 通訊介面 | USB Serial |
| Device | `/dev/ttyACM0` |
| Coordinate Frame | SUB-012 Robot Description |

---

## 系統職責

- 建立 `/dev/ttyACM0` 通訊。
- 接收 IMU 資料封包。
- 驗證資料封包完整性。
- 解析三軸角速度資料。
- 解析三軸線性加速度資料。
- 將量測資料轉換為 ROS 2 標準 SI 單位。
- 發布標準 ROS 2 `Imu` Topic。
- 提供訊息時間戳記與 Frame ID。
- 提供 IMU 通訊與資料狀態。

IMU Perception 僅負責提供慣性量測資料。

姿態估測、感測器融合與座標系統里程資訊由下游子系統處理。

---

## 邏輯架構

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

---

## ROS Interface

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/imu/data_raw` | `sensor_msgs/msg/Imu` | IMU 原始量測資料 |

---

## TF Interface

| Parent Frame | Child Frame |
|---|---|
| `base_link` | `base_imu_link` |

IMU 安裝位置與座標方向由 **SUB-012 Robot Description** 管理。

初版沿用既有 URDF Baseline，並透過實機靜止與旋轉測試確認。

---

## IMU 訊息

`/imu/data_raw` 使用 `sensor_msgs/msg/Imu`。

| 欄位 | 初版處理 |
|---|---|
| `header.stamp` | 使用 Driver 產生之訊息時間 |
| `header.frame_id` | `base_imu_link` |
| `angular_velocity` | 轉換為 rad/s |
| `linear_acceleration` | 轉換為 m/s² |
| `orientation` | 維持未提供狀態 |
| `angular_velocity_covariance` | 依 Driver Baseline 與實機量測設定 |
| `linear_acceleration_covariance` | 依 Driver Baseline 與實機量測設定 |
| `orientation_covariance` | 標示 Orientation 未提供 |

---

## 系統參數

### Device Parameters

| 參數 | 初版來源 |
|---|---|
| Device | `/dev/ttyACM0` |
| Baud Rate | 既有 Driver Baseline |
| Frame ID | `base_imu_link` |
| Topic | `/imu/data_raw` |

---

### Sensor Parameters

下列參數依既有 Driver 與裝置設定決定：

- Output Rate
- Gyroscope Range
- Accelerometer Range
- Axis Mapping
- Packet Format
- Checksum

初版沿用既有 Driver Baseline，Hardware Bring-up 完成後確認。

---

## 座標與單位

IMU 資料遵循 ROS 2 標準單位：

| 資料 | 單位 |
|---|---|
| Angular Velocity | rad/s |
| Linear Acceleration | m/s² |

Axis Mapping 依 URDF 與實機測試確認。

實機確認項目包括：

- 靜止時重力方向。
- 正向旋轉時角速度方向。
- X、Y、Z 軸與 `base_imu_link` 定義一致。

---

## 軟體組成

```text
imu_perception
├── Serial Transport
├── Packet Parser
├── Checksum Validation
├── Unit Conversion
├── Parameter Manager
└── Diagnostics
```

Package 結構於 Implementation 階段確認。

---

## 設計依據

SUB-003 依下列順序完成設計確認：

1. IIM-42652 Datasheet。
2. 既有 ROS 2 Driver。
3. 現有專案 Baseline。
4. Hardware Bring-up。
5. 實機靜止與旋轉測試。
6. 下游感測融合需求。

初版優先沿用既有 Driver 的通訊、封包解析與單位轉換，不重新設計 IMU Protocol。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Device Access | 系統可開啟 `/dev/ttyACM0` |
| Driver Start | IMU Driver 可持續運作 |
| Topic Publish | `/imu/data_raw` 持續發布 |
| Message Type | `sensor_msgs/msg/Imu` |
| Timestamp | `header.stamp` 持續遞增 |
| Frame ID | `header.frame_id` 為 `base_imu_link` |
| Angular Velocity | 旋轉方向與實際運動一致 |
| Linear Acceleration | 靜止時重力方向一致 |
| Unit | 使用 ROS 2 標準 SI 單位 |
| Axis Mapping | 與 SUB-012 定義一致 |
| Long Duration | 建圖與導航期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-004 | SUB-003 |

# SUB-004 Differential Drive Controller

## 目的

Differential Drive Controller 子系統負責差速運動學與輪式里程：
接收車體速度命令並換算為左右輪速度命令，同時由輪端回授推算 AMR 平面里程，
發布標準 ROS 2 `Odometry` 訊息，提供 Robot Localization EKF 作為感測器融合輸入。

本子系統以 ros2_control 之 `diff_drive_controller` 實現，不含自訂程式碼。

---

## 對應需求

| Requirement |
|---|
| SYS-005 |
| SYS-022 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 運動模型 | Differential Drive |
| 控制框架 | ros2_control |
| 元件 | `diff_drive_controller` |
| 硬體介面 | SUB-001 Drive Hardware Interface |
| Coordinate Frame | SUB-012 Robot Description |

---

## 系統職責

- 接收車體速度命令 `/cmd_vel`。
- 執行差速運動學，輸出左右輪速度命令至 SUB-001。
- 由輪端回授推算 AMR 平面位姿、線速度與角速度。
- 發布 Wheel Odometry。
- 執行速度與加速度限制。
- 執行命令逾時保護。

不負責：

- 驅動器通訊與生命週期（SUB-001）。
- 感測器融合與 `odom → base_footprint` TF（SUB-006）。

---

## 邏輯架構

```text
            /cmd_vel
                │
                ▼
     diff_drive_controller
       ┌────────┴────────┐
       ▼                 ▼
  Inverse Kinematics  Odometry
       │                 │
       ▼                 ▼
 輪端速度命令        /wheel_odom
       │                 ▲
       ▼                 │
 SUB-001 Command If.  SUB-001 State If.
```

---

## ROS Interface

### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/TwistStamped` | 底盤速度命令 |

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/wheel_odom` | `nav_msgs/msg/Odometry` | Wheel Odometry |

`diff_drive_controller` 預設之 odometry topic 經 remap 為 `/wheel_odom`，
以維持 SUB-006 既有輸入介面不變。

`/cmd_vel` 之訊息型別依 `diff_drive_controller` 版本設定；
若採 `TwistStamped`，上游 Navigation 須對應設定。

---

## Joint State

`joint_state_broadcaster` 由 SUB-001 之 State Interface 發布 `/joint_states`
（`sensor_msgs/msg/JointState`，輪端 rad、rad/s），供 `robot_state_publisher`
與診斷工具使用。

本專案不另建自訂輪端狀態 Topic。

---

## TF Interface

Differential Drive Controller **不發布 TF**。

`diff_drive_controller` 之 `enable_odom_tf` 須設為 `false`。

系統唯一的：

```text
odom → base_footprint
```

由 **SUB-006 Robot Localization EKF** 發布，避免兩處同時發布造成 TF 衝突。

---

## Odometry

`/wheel_odom` 使用 `nav_msgs/msg/Odometry`。

| 欄位 | 初版處理 |
|---|---|
| `header.frame_id` | `odom` |
| `child_frame_id` | `base_footprint` |
| Position | `diff_drive_controller` 積分 |
| Orientation | `diff_drive_controller` 積分 |
| Linear Velocity | 輪端回授推算 |
| Angular Velocity | 輪端回授推算 |
| Covariance | 初版採 Baseline，實機調整 |

Wheel Odometry 提供相對運動估測，不保證長時間絕對定位精度。

---

## 系統參數

### Vehicle Parameters

| 參數 | 採用值 | 來源 |
|---|---|---|
| Wheel Radius | 0.08 m | 既有 Baseline，尚未經實機量測驗證 |
| Wheel Separation | 0.555 m | 既有 Baseline，尚未經實機量測驗證 |

本子系統為此二參數之**唯一持有者**。SUB-001 不重複宣告，
避免命令路徑與里程路徑採用不同數值而產生無聲不一致。

Wheel Radius 應量測有載滾動半徑，非幾何半徑。

Gear Ratio 與編碼器解析度不屬於本子系統；
SUB-001 已將回授換算至輪端物理量。

---

### Controller Parameters

下列參數依 `diff_drive_controller` Baseline 設定，實機調整：

- Update Rate
- Publish Rate
- Velocity / Acceleration Limits
- `cmd_vel_timeout`
- Odometry Covariance
- `open_loop`（本專案採 `false`，使用輪端回授）
- `enable_odom_tf`（固定 `false`）

---

## 軟體組成

```text
diff_drive_controller   （ros2_control 既有元件）
└── controller 參數檔
```

本子系統不建立自訂程式碼，僅提供組態與 launch 設定。

---

## 設計依據

SUB-004 依下列順序完成設計確認：

1. Differential Drive 運動模型。
2. ros2_control 與 `diff_drive_controller` 官方文件。
3. SUB-001 Drive Hardware Interface 匯出之介面。
4. Robot Localization 輸入需求。
5. Hardware Bring-up。
6. Vehicle Geometry 實機量測。

設計原則：

- 優先使用 `diff_drive_controller`，不自行實作差速運動學與里程積分。
- Wheel Radius 與 Wheel Separation 集中於本子系統，維持單一來源。
- TF 發布權責集中於 SUB-006，本子系統不發布 TF。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Controller 載入 | `controller_manager` 可載入並啟用 `diff_drive_controller` |
| Command Path | `/cmd_vel` 可驅動底盤直行與原地旋轉 |
| Topic Publish | `/wheel_odom` 持續發布 |
| Message Type | `nav_msgs/msg/Odometry` |
| Straight Motion | 直線位移方向與量值正確 |
| Rotation | 原地旋轉方向與角度正確 |
| Velocity | 線速度與角速度合理 |
| Covariance | Covariance 正常設定 |
| TF | 不發布 `odom → base_footprint` |
| Timeout | `/cmd_vel` 逾時後底盤停止 |
| Long Duration | 建圖與導航期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-005 | SUB-004 |
| SYS-022 | SUB-004 |

# SUB-005 RF2O Odometry

## 目的

RF2O Odometry 子系統負責使用 LiDAR 原始掃描資料估測 AMR 平面里程資訊，發布標準 ROS 2 `Odometry` 訊息，提供 Robot Localization EKF 作為感測器融合輸入。

---

## 對應需求

| Requirement |
|---|
| SYS-003 |
| SYS-005 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 演算法 | RF2O Laser Odometry |
| 資料來源 | SUB-002 LiDAR Perception |
| Coordinate Frame | SUB-012 Robot Description |

---

## 系統職責

- 接收選定之原始 LiDAR `LaserScan`。
- 執行 RF2O Laser Odometry。
- 推算 AMR 平面位姿。
- 推算 AMR 線速度。
- 推算 AMR 角速度。
- 發布標準 ROS 2 `Odometry` Topic。
- 提供 RF2O 運行狀態。

RF2O Odometry 僅負責雷射里程估測。

感測器融合、系統里程與 TF 發布由 **SUB-006 Robot Localization EKF** 負責。

---

## 邏輯架構

```text
/scan_front_left 或 /scan_back_right
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

---

## LiDAR 輸入原則

RF2O 優先直接使用 SUB-002 提供之原始 LiDAR Topic。

選擇順序：

1. 確認 RF2O 套件支援的輸入形式。
2. 若套件可直接接收所需之多個原始來源，直接使用原始 Topic。
3. 若套件僅接受單一 `LaserScan`，分別驗證 `/scan_front_left` 與 `/scan_back_right`。
4. 選用可穩定提供 RF2O 里程估測的單一原始來源。
5. 單一原始來源可滿足需求時維持不融合。
6. 僅於介面限制且單一來源無法滿足功能需求時，才評估 LaserScan Fusion。

初版不預設導入 LaserScan Fusion。

---

## ROS Interface

### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/scan_front_left` 或 `/scan_back_right` | `sensor_msgs/msg/LaserScan` | RF2O 原始 Scan 輸入 |

正式輸入 Topic 依套件介面、Hardware Bring-up 與實機測試結果決定。

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/rf2o_odom` | `nav_msgs/msg/Odometry` | RF2O Odometry |

---

## TF Interface

RF2O Odometry 不發布 TF。

系統唯一的：

```text
odom → base_footprint
```

由 **SUB-006 Robot Localization EKF** 發布。

---

## Odometry

`/rf2o_odom` 使用 `nav_msgs/msg/Odometry`。

| 欄位 | 初版處理 |
|---|---|
| `header.frame_id` | `odom` |
| `child_frame_id` | `base_footprint` |
| Position | RF2O 推算 |
| Orientation | RF2O 推算 |
| Linear Velocity | RF2O 推算 |
| Angular Velocity | RF2O 推算 |
| Covariance | 採 RF2O Baseline，實機調整 |

RF2O 提供相對運動估測，不提供長時間絕對定位。

---

## Scan Source 評估

候選原始來源：

- `/scan_front_left`
- `/scan_back_right`

實機評估項目：

- 靜止時位姿穩定性。
- 直線移動估測品質。
- 原地旋轉估測品質。
- 環境幾何特徵覆蓋。
- LiDAR 安裝位置與車體遮蔽。
- 長時間運行穩定性。

選定之原始 Topic 應能滿足 RF2O 與 EKF 輸入需求。

---

## 系統參數

### Input Parameters

| 參數 | 初版來源 |
|---|---|
| Scan Topic | 套件介面與實機測試決定 |
| Odom Topic | `/rf2o_odom` |
| Odom Frame | `odom` |
| Base Frame | `base_footprint` |

### RF2O Parameters

下列參數依 RF2O 套件 Baseline 建立：

- Processing Rate
- Publish Rate
- Covariance
- Initial Pose
- Scan Matching Parameters

初版採用 RF2O Baseline，實機測試後調整。

---

## 軟體組成

```text
rf2o_odometry
├── RF2O Node
├── Scan Interface
├── Parameter Manager
└── Diagnostics
```

初版優先使用成熟 RF2O 套件，不自行實作雷射里程估測演算法。

Package 結構於 Implementation 階段確認。

---

## 設計依據

SUB-005 依下列順序完成設計確認：

1. RF2O Laser Odometry 套件。
2. 現有專案 Baseline。
3. SUB-002 LiDAR Perception。
4. RF2O 輸入介面確認。
5. Hardware Bring-up。
6. `/scan_front_left` 與 `/scan_back_right` 實機比較。
7. LaserScan Fusion 必要性評估。
8. Robot Localization 輸入需求。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Input Capability | 完成 RF2O 原始 Scan 輸入能力確認 |
| Front-Left Scan Test | 完成 `/scan_front_left` RF2O 測試 |
| Back-Right Scan Test | 完成 `/scan_back_right` RF2O 測試 |
| Scan Source | 選定可滿足需求之原始 LiDAR 來源 |
| Topic Publish | `/rf2o_odom` 持續發布 |
| Message Type | `nav_msgs/msg/Odometry` |
| Static Stability | 靜止時位姿穩定 |
| Straight Motion | 直線位移方向正確 |
| Rotation | 原地旋轉方向正確 |
| Fusion Decision | 僅於原始來源無法滿足需求時評估融合 |
| TF | 不發布 `odom → base_footprint` |
| Long Duration | 建圖與導航期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-003 | SUB-005 |
| SYS-005 | SUB-005 |

# SUB-006 Robot Localization EKF

## 目的

Robot Localization EKF 子系統負責融合 Wheel Odometry、RF2O Odometry 與 IMU 量測資料，估測 AMR 之系統里程資訊，發布標準 ROS 2 `Odometry` 與 TF，提供 Mapping、Localization 與 Navigation 使用。

---

## 對應需求

| Requirement |
|---|
| SYS-005 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 套件 | robot_localization |
| Filter | Extended Kalman Filter (EKF) |

---

## 系統職責

- 接收 Wheel Odometry（SUB-004）。
- 接收 RF2O Odometry。
- 接收 IMU 原始量測。
- 執行 Extended Kalman Filter。
- 發布融合後 Odometry。
- 發布 `odom → base_footprint` TF。
- 提供 Localization 狀態。

Robot Localization EKF 僅負責感測器融合。

不負責：

- SLAM
- AMCL Localization
- Navigation
- Path Planning

---

## 邏輯架構

```text
         /wheel_odom
              │
              │
         /rf2o_odom
              │
              │
        /imu/data_raw
              │
              ▼
   Robot Localization EKF
              │
     ┌────────┴────────┐
     ▼                 ▼
     /odom      odom → base_footprint
```

---

## Sensor Fusion

初版 EKF 融合三種資料來源：

- Wheel Odometry
- RF2O Odometry
- IMU

```text
Wheel Odometry
        │
        │
RF2O Odometry
        │
        │
        IMU
        │
        ▼
      EKF
        │
        ▼
     /odom
```

各感測器維持獨立發布。

Robot Localization 負責融合。

---

## ROS Interface

### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/wheel_odom` | `nav_msgs/msg/Odometry` | Wheel Odometry |
| `/rf2o_odom` | `nav_msgs/msg/Odometry` | RF2O Odometry |
| `/imu/data_raw` | `sensor_msgs/msg/Imu` | IMU 原始量測 |

---

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/odom` | `nav_msgs/msg/Odometry` | EKF 融合後里程資訊 |

---

## TF Interface

### Subscribe

Robot Localization 使用：

```text
base_link
├── base_imu_link
├── base_lidar_link_FL
└── base_lidar_link_BR
```

由 **SUB-012 Robot Description** 提供。

---

### Publish

Robot Localization 為系統唯一發布：

```text
odom
    │
    ▼
base_footprint
```

Mapping 模式：

```text
map
 │
 ▼
SLAM Toolbox
 │
 ▼
odom
```

Navigation 模式：

```text
map
 │
 ▼
AMCL
 │
 ▼
odom
```

因此整體 TF 為：

```text
map
 │
 ▼
odom
 │
 ▼
base_footprint
 │
 ▼
base_link
```

---

## EKF Configuration

初版使用 robot_localization 單一 EKF。

融合來源：

| Sensor | 使用 |
|---|---|
| Wheel Odometry | ✓ |
| RF2O Odometry | ✓ |
| IMU Angular Velocity | ✓ |
| IMU Linear Acceleration | 實機驗證後決定 |

是否融合其他感測器，由後續版本評估。

---

## 系統參數

### Frame Parameters

| 參數 | 初版設定 |
|---|---|
| Map Frame | `map` |
| Odom Frame | `odom` |
| Base Frame | `base_footprint` |
| World Frame | `odom` |

---

### Input Topics

| Topic | 初版設定 |
|---|---|
| Wheel Odom | `/wheel_odom` |
| RF2O Odom | `/rf2o_odom` |
| IMU | `/imu/data_raw` |

---

### EKF Parameters

下列參數初版採 robot_localization Baseline：

- Update Rate
- Sensor Timeout
- Process Noise
- Initial Covariance
- Measurement Covariance
- Two Dimensional Mode

Hardware Bring-up 完成後再依實機調整。

---

## 軟體組成

```text
robot_localization
├── EKF Node
├── Sensor Interface
├── Parameter Manager
└── Diagnostics
```

Package 結構於 Implementation 階段確認。

---

## 設計依據

SUB-006 依下列順序完成設計確認：

1. robot_localization 官方文件。
2. ROS 2 Jazzy Baseline。
3. SUB-003 IMU Perception。
4. SUB-004 Differential Drive Controller。
5. SUB-005 RF2O Odometry。
6. Hardware Bring-up。
7. EKF Covariance 調整。
8. Navigation 與 Mapping 實機驗證。

初版優先採用 robot_localization 官方 EKF，不自行實作 Sensor Fusion 演算法。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Wheel Input | 可持續接收 `/wheel_odom` |
| RF2O Input | 可持續接收 `/rf2o_odom` |
| IMU Input | 可持續接收 `/imu/data_raw` |
| Topic Publish | `/odom` 持續發布 |
| TF Publish | 正確發布 `odom → base_footprint` |
| Fusion | 三種感測器可正常融合 |
| Straight Motion | 直線位姿估測穩定 |
| Rotation | 原地旋轉估測穩定 |
| Static Stability | 靜止時位姿穩定 |
| Long Duration | 建圖與導航期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-005 | SUB-006 |

# SUB-007 SLAM Toolbox

## 目的

SLAM Toolbox 子系統負責使用 LiDAR 原始掃描資料與系統里程資訊建立二維 Occupancy Grid 地圖，發布地圖與 `map → odom` TF，並提供 Map Management 儲存使用。

---

## 對應需求

| Requirement |
|---|
| SYS-001 |
| SYS-006 |
| SYS-007 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 套件 | `slam_toolbox` |
| 建圖模式 | Online Mapping |
| 地圖類型 | Occupancy Grid |
| LiDAR 來源 | SUB-002 LiDAR Perception |
| 里程來源 | SUB-006 Robot Localization EKF |

---

## 系統職責

- 接收 SLAM Toolbox 支援之原始 LiDAR `LaserScan`。
- 接收系統里程與 TF。
- 執行二維同步定位與建圖。
- 持續更新 Occupancy Grid。
- 發布 `/map`。
- 發布 `map → odom` TF。
- 提供建圖狀態。
- 提供 Map Management 所需之地圖資料。

SLAM Toolbox 僅負責建圖與建圖期間之地圖座標轉換。

地圖檔案與 Map Package 管理由 **SUB-008 Map Management** 負責。

---

## 邏輯架構

```text
Raw LiDAR Topic
       │
       │
     /odom
       │
       ▼
 SLAM Toolbox
       │
 ┌─────┴─────┐
 ▼           ▼
/map    map → odom
 │
 ▼
SUB-008 Map Management
```

---

## LiDAR 輸入原則

SLAM Toolbox 優先直接使用 SUB-002 提供之原始 LiDAR Topic。

確認順序：

1. 確認 SLAM Toolbox 可接受之 LiDAR 輸入形式。
2. 若可直接接收所需之多個原始來源，直接使用原始 Topic。
3. 若僅接受單一 `LaserScan`，分別驗證 `/scan_front_left` 與 `/scan_back_right`。
4. 選用可穩定完成建圖的單一原始來源。
5. 單一原始來源可滿足建圖需求時維持不融合。
6. 僅於介面限制且單一來源無法滿足建圖需求時，才評估 LaserScan Fusion。

初版不預設導入 LaserScan Fusion。

---

## ROS Interface

### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| 原始 Scan Topic | `sensor_msgs/msg/LaserScan` | 建圖輸入 |
| `/odom` | `nav_msgs/msg/Odometry` | 系統里程資訊 |
| `/tf` | TF2 | 動態座標轉換 |
| `/tf_static` | TF2 | 固定座標轉換 |

正式 Scan Topic 依套件介面與實機建圖結果決定。

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/map` | `nav_msgs/msg/OccupancyGrid` | 二維 Occupancy Grid 地圖 |
| `/tf` | TF2 | `map → odom` |

---

## TF Interface

SLAM Toolbox 於 Mapping 模式發布：

```text
map
 │
 ▼
odom
```

系統其餘 TF：

```text
odom
 │
 ▼
base_footprint
 │
 ▼
base_link
```

| Transform | 發布來源 |
|---|---|
| `map → odom` | SLAM Toolbox |
| `odom → base_footprint` | SUB-006 Robot Localization EKF |
| `base_footprint → base_link` | SUB-012 Robot Description |
| `base_link → sensor frames` | SUB-012 Robot Description |

Mapping 模式中，`map → odom` 僅由 SLAM Toolbox 發布。

---

## Occupancy Grid

`/map` 使用 `nav_msgs/msg/OccupancyGrid`。

| 欄位 | 初版處理 |
|---|---|
| `header.frame_id` | `map` |
| Resolution | 採 SLAM Toolbox Baseline |
| Width / Height | 依建圖範圍動態建立 |
| Origin | 由 SLAM Toolbox 管理 |
| Data | Occupancy Grid Cell Data |

建圖結果提供 SUB-008 儲存為：

```text
maps/<map_name>/
├── map.pgm
└── map.yaml
```

---

## 建圖流程

1. 啟動底盤、感知、里程估測與 TF。
2. 確認 SLAM Toolbox 的 LiDAR 輸入能力。
3. 選定可滿足需求之原始 LiDAR Topic。
4. 啟動 SLAM Toolbox Mapping 模式。
5. 使用者透過鍵盤控制 AMR。
6. SLAM Toolbox 接收原始 Scan 與里程資料。
7. 系統持續更新 `/map` 與 `map → odom`。
8. 使用者完成環境巡覽。
9. SUB-008 Map Management 儲存建圖成果。

若原始 LiDAR Topic 無法滿足建圖需求，再進入 LaserScan Fusion 評估。

---

## 系統參數

### Frame Parameters

| 參數 | 初版設定 |
|---|---|
| Map Frame | `map` |
| Odom Frame | `odom` |
| Base Frame | `base_footprint` |

### Input Parameters

| 參數 | 初版來源 |
|---|---|
| Scan Topic | 套件介面與實機測試決定 |
| Odom Topic | `/odom` |
| Transform Publish Period | SLAM Toolbox Baseline |

### Mapping Parameters

下列參數初版採 `slam_toolbox` Baseline：

- Resolution
- Map Update Interval
- Minimum Travel Distance
- Minimum Travel Heading
- Scan Buffer Size
- Correlation Search Space
- Loop Closure Parameters
- Transform Timeout

實機完成可用地圖後，再依建圖品質調整。

---

## 軟體組成

```text
mapping
├── SLAM Toolbox Node
├── Mapping Parameters
├── Launch Configuration
└── Diagnostics
```

初版優先使用 `slam_toolbox` 二進位套件與既有 Launch／Parameter 機制，不自行實作 SLAM 演算法。

Package 結構於 Implementation 階段確認。

---

## 設計依據

SUB-007 依下列順序完成設計確認：

1. `slam_toolbox` 官方文件與 ROS 2 Jazzy 套件。
2. SUB-002 LiDAR Perception。
3. SUB-006 Robot Localization EKF。
4. 既有 URDF 與 TF Tree。
5. SLAM Toolbox LiDAR 輸入能力確認。
6. Hardware Bring-up。
7. `/scan_front_left` 與 `/scan_back_right` 實機建圖比較。
8. LaserScan Fusion 必要性評估。
9. Occupancy Grid 實機驗證。

初版先以原始 LiDAR Topic 與套件 Baseline 完成可重複建圖，再進行必要調整。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Input Capability | 完成 SLAM Toolbox 原始 Scan 輸入能力確認 |
| Front-Left Scan Test | 完成 `/scan_front_left` 建圖測試 |
| Back-Right Scan Test | 完成 `/scan_back_right` 建圖測試 |
| Scan Source | 選定可滿足需求之原始 LiDAR 輸入 |
| Odom Input | 可持續取得 `/odom` 與 TF |
| Topic Publish | `/map` 持續發布並更新 |
| Message Type | `/map` 為 `nav_msgs/msg/OccupancyGrid` |
| TF Publish | 正確發布 `map → odom` |
| Mapping | 可建立與實際環境一致之二維地圖 |
| Loop Closure | 重訪區域時地圖維持一致 |
| Fusion Decision | 僅於原始資料無法滿足需求時評估融合 |
| Map Save Input | SUB-008 可取得 `/map` 並儲存 |
| Repeatability | 相同環境可重複建立可用地圖 |
| Long Duration | 建圖期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-001 | SUB-007 |
| SYS-006 | SUB-007 |
| SYS-007 | SUB-007 |

# SUB-008 Map Management

## 目的

Map Management 子系統負責管理二維地圖與其關聯導航資源，提供 Map Package 建立、儲存、載入與資源路徑管理，支援建圖、定位與導航使用。

---

## 對應需求

| Requirement |
|---|
| SYS-002 |
| SYS-007 |
| SYS-008 |
| SYS-009 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 核心套件 | `nav2_map_server` |
| 地圖格式 | Occupancy Grid |
| 管理單位 | Map Package |
| Map Root | `maps/` |

---

## 系統職責

- 建立指定名稱之 Map Package。
- 儲存建圖產生之 Occupancy Grid。
- 載入指定 Map Package 之 Occupancy Grid。
- 管理地圖與導航資源之固定目錄結構。
- 提供 Map Server 所需之地圖檔案路徑。
- 提供 Target Resolution 所需之 Route Graph 與 Station Mapping 路徑。
- 提供 Map Package 載入狀態。

Map Management 不負責：

- SLAM。
- Localization。
- Route Graph 建立與編輯。
- Station Mapping 內容解析。
- Navigation。

上述功能由對應子系統負責。

---

## Map Package

每個場域以一個 Map Package 集中管理地圖與導航資源。

```text
maps/
└── <map_name>/
    ├── map.pgm
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

| 檔案 | 說明 |
|---|---|
| `map.pgm` | Occupancy Grid 地圖影像 |
| `map.yaml` | Occupancy Grid 地圖設定 |
| `route_graph.geojson` | Nav2 Route Graph |
| `stations.yaml` | Station ID 與 Route Node ID 映射 |

UC-001 建圖完成後產生：

```text
map.pgm
map.yaml
```

UC-002 路網建置期間加入：

```text
route_graph.geojson
stations.yaml
```

---

## 邏輯架構

```text
                    Map Package
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      map.yaml     route_graph.geojson  stations.yaml
          │              │              │
          ▼              ▼              ▼
    Map Server      Route Graph      Station Mapping
                         │              │
                         └──────┬───────┘
                                ▼
                         Navigation
```

---

## 地圖儲存流程

```text
SLAM Toolbox
      │
      ▼
    /map
      │
      ▼
Map Management
      │
      ▼
maps/<map_name>/
├── map.pgm
└── map.yaml
```

執行流程：

1. 使用者指定 `map_name`。
2. 系統建立 `maps/<map_name>/`。
3. Map Management 取得 `/map`。
4. 呼叫成熟地圖儲存功能。
5. 產生 `map.pgm` 與 `map.yaml`。
6. 驗證檔案可重新載入。

初版優先使用 Nav2 提供之地圖儲存能力，不自行實作 Occupancy Grid 檔案轉換。

---

## 地圖載入流程

```text
map_name
    │
    ▼
maps/<map_name>/map.yaml
    │
    ▼
Nav2 Map Server
    │
    ▼
  /map
```

執行流程：

1. 使用者或 Launch 指定 `map_name`。
2. 系統解析 `maps/<map_name>/map.yaml`。
3. 啟動或設定 Nav2 Map Server。
4. Map Server 發布 `/map`。
5. AMCL 與 Navigation 使用載入之地圖。

---

## ROS Interface

### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/map` | `nav_msgs/msg/OccupancyGrid` | SLAM Toolbox 建圖結果 |

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/map` | `nav_msgs/msg/OccupancyGrid` | Map Server 載入之導航地圖 |

Mapping 與 Navigation 模式分別由不同來源發布 `/map`：

| 模式 | `/map` Publisher |
|---|---|
| Mapping | SUB-007 SLAM Toolbox |
| Navigation | Nav2 Map Server |

兩種模式不應同時啟用相同 `/map` 發布來源。

---

## Service Interface

| Service | 說明 |
|---|---|
| Save Map | 儲存目前 Occupancy Grid |
| Load Map | 載入指定 Occupancy Grid |

實際 Service 名稱與呼叫方式採 Nav2 套件既有介面，於 Implementation 階段確認。

---

## 資源路徑

Map Management 依 `map_name` 提供以下資源路徑：

| 資源 | 路徑 |
|---|---|
| Map YAML | `maps/<map_name>/map.yaml` |
| Map Image | `maps/<map_name>/map.pgm` |
| Route Graph | `maps/<map_name>/route_graph.geojson` |
| Station Mapping | `maps/<map_name>/stations.yaml` |

Route Graph 與 Station Mapping 由 SUB-010 使用。

Map Management 僅管理路徑與 Map Package 結構，不解析其導航語意。

---

## 系統參數

| 參數 | 初版設定 |
|---|---|
| Map Root | `maps/` |
| Map Name | 使用者或 Launch 指定 |
| Map YAML | `map.yaml` |
| Map Image | `map.pgm` |
| Route Graph | `route_graph.geojson` |
| Station Mapping | `stations.yaml` |
| Map Frame | `map` |
| Map Topic | `/map` |

---

## 檔案管理原則

- 一個 `map_name` 對應一個 Map Package。
- 地圖與其 Route Graph、Station Mapping 保存在相同目錄。
- 導航模式以同一個 `map_name` 載入所有相關資源。
- Map Package 內使用固定檔名，降低 Launch 與部署設定複雜度。
- Map Package 切換應以整個目錄為單位，避免地圖與路網版本不一致。
- 初版允許覆寫同名地圖，實際操作方式於 Implementation 階段確認。

---

## 軟體組成

```text
map_management
├── Map Package Resolver
├── Map Save Integration
├── Map Load Integration
├── Path Validation
├── Launch Configuration
└── Diagnostics
```

初版優先整合 `nav2_map_server` 與既有儲存介面。

專案自訂內容限於：

- Map Package 路徑解析。
- 固定目錄結構。
- `map_name` 參數整合。
- 資源存在性與狀態檢查。

---

## 設計依據

SUB-008 依下列順序完成設計確認：

1. UC-001 地圖儲存需求。
2. UC-002 地圖載入需求。
3. `nav2_map_server`。
4. SUB-007 SLAM Toolbox 輸出。
5. SUB-010 Target Resolution 資源需求。
6. Map Package 目錄結構。
7. 實機地圖儲存與載入驗證。

初版優先採用 Nav2 成熟地圖管理功能，不自行實作地圖格式轉換或 Map Server。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Package Create | 可建立 `maps/<map_name>/` |
| Map Save | 成功產生 `map.pgm` 與 `map.yaml` |
| Map Load | Nav2 Map Server 可載入指定 `map.yaml` |
| Topic Publish | Navigation 模式下 `/map` 持續發布 |
| Message Type | `/map` 為 `nav_msgs/msg/OccupancyGrid` |
| Map Consistency | 載入內容與儲存前地圖一致 |
| Resource Path | 可取得 Route Graph 與 Station Mapping 路徑 |
| Package Consistency | 地圖與導航資源位於同一 Map Package |
| Map Selection | 可依 `map_name` 選擇不同 Map Package |
| Repeatability | 相同 Map Package 可重複載入一致結果 |
| Long Duration | 定位與導航期間持續正常提供地圖 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-002 | SUB-008 |
| SYS-007 | SUB-008 |
| SYS-008 | SUB-008 |
| SYS-009 | SUB-008 |

# SUB-009 Task Interface

## 目的

Task Interface 子系統負責接收使用者提交之 Navigation Target，完成基本輸入驗證，並將目標交由 Target Resolution 流程產生 Canonical Goal Pose。

本子系統定位為薄層 Adapter，不負責導航策略、路徑規劃、導航控制或任務排程。

初版支援：

- Station ID
- Goal Pose

---

## 對應需求

| Requirement |
|---|
| SYS-008 |
| SYS-009 |
| SYS-017 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| ROS | ROS 2 Jazzy |
| 任務類型 | Navigation |
| Navigation Target | Station ID、Goal Pose |
| Canonical Navigation Goal | Goal Pose |
| Station Resolution | SUB-010 Target Resolution |
| Navigation Execution | SUB-011 Navigation |

---

## 系統職責

- 接收 Navigation Target。
- 識別 Navigation Target 類型。
- 驗證輸入資料格式。
- Station ID 交由 SUB-010 解析。
- Goal Pose 直接作為 Canonical Goal Pose。
- 將 Canonical Goal Pose 交由 SUB-011 Navigation。
- 接收 Navigation Feedback。
- 接收 Navigation Result。
- 將 Navigation Result 回報給使用者。

Task Interface 不負責：

- Station 資料管理。
- Route Graph 管理。
- Route Planning。
- Navigation Strategy Selection。
- Path Planning。
- Path Following。
- Localization。
- Task Queue。
- Task Priority。
- Fleet Scheduling。

---

## 邏輯架構

```text
                     User
                      │
             Navigation Target
                      │
                      ▼
             SUB-009 Task Interface
                      │
               Target Type
             ┌────────┴────────┐
             ▼                 ▼
        Station ID         Goal Pose
             │                 │
             ▼                 │
        SUB-010               │
     Target Resolution         │
             │                 │
             ▼                 │
          Goal Pose            │
             │                 │
             └────────┬────────┘
                      ▼
             Canonical Goal Pose
                      │
                      ▼
             SUB-011 Navigation
                      │
              ┌───────┴───────┐
              ▼               ▼
           Feedback          Result
              │               │
              └───────┬───────┘
                      ▼
             SUB-009 Task Interface
                      │
                      ▼
                     User
```

---

## Navigation Target

系統支援兩種 Navigation Target。

| Target Type | Input | 處理 |
|---|---|---|
| Station | Station ID | 交由 SUB-010 解析成 Goal Pose |
| Pose | `geometry_msgs/msg/PoseStamped` | 直接作為 Goal Pose |

Navigation Target 僅描述「使用者要去哪裡」。

Navigation Target 不決定：

- 是否使用 Route Graph。
- 是否使用 First Mile。
- 是否使用 Last Mile。
- 採用何種 Planner。
- 採用何種 Controller。

上述行為屬於 SUB-011 Navigation。

---

## Canonical Goal

所有 Navigation Target 在進入 Navigation 前統一轉換為：

```text
geometry_msgs/msg/PoseStamped
```

因此：

```text
Station ID
    │
    ▼
Goal Pose
```

以及：

```text
Goal Pose
    │
    ▼
Goal Pose
```

最終皆形成：

```text
Canonical Goal Pose
```

SUB-011 Navigation 不需要知道 Goal Pose 原本來自 Station 或直接 Pose 輸入。

---

## Station Target Flow

```text
Station ID
    │
    ▼
SUB-009
    │
    ▼
SUB-010
    │
stations.yaml
    │
    ▼
Goal Pose
    │
    ▼
SUB-011
```

Station 是否位於 Route Graph Node 上，不屬於 Target Resolution 必要條件。

Station 定義的是：

> AMR 最終應抵達的位置與朝向。

Route Graph 定義的是：

> AMR 導航過程可利用的路網。

兩者彼此解耦。

---

## Pose Target Flow

```text
Goal Pose
    │
    ▼
SUB-009
    │
    ▼
Canonical Goal Pose
    │
    ▼
SUB-011
```

Pose Target 不需要經過 SUB-010。

---

## ROS Interface

初版優先使用既有 ROS 2 與 Nav2 Interface，避免建立不必要的自定義 Navigation Action。

### Navigation Target Input

Station Target：

```text
Station ID
```

實際 CLI、Service 或其他輸入形式於 Implementation 階段依最小需求確認。

Pose Target：

```text
geometry_msgs/msg/PoseStamped
```

---

## Navigation Interface

SUB-009 將解析完成之 Canonical Goal Pose 交給 SUB-011。

SUB-011 初版優先整合 Nav2：

```text
NavigateToPose
```

Action。

```text
Canonical Goal Pose
        │
        ▼
Nav2 NavigateToPose
```

不另外實作與 Nav2 重複的 Navigation Action Server。

---

## Feedback

Navigation Feedback 優先直接沿用 Nav2 Action Feedback。

SUB-009 不建立另一套 Navigation Progress 定義，除非後續上層系統具有明確需求。

初版僅需向使用者提供足以確認導航正在執行之狀態。

---

## Result

Navigation Result 優先沿用 Nav2 Action Result。

Task Interface 對外至少應能表示：

```text
Succeeded
Failed
Canceled
```

實際 Error Code 優先沿用 Nav2 現有結果資訊，不重複建立自定義錯誤碼系統。

---

## 任務生命週期

SUB-009 不建立獨立完整 Task State Machine。

初版生命週期直接映射 Navigation Action 狀態：

```text
Received
    │
    ▼
Resolving Target
    │
    ▼
Navigation Executing
    │
 ┌──┼─────────┐
 ▼  ▼         ▼
Success     Failure
            Cancel
```

若未來 Fleet Management 需要：

- Queue
- Priority
- Retry
- Scheduling
- Multi-task

由上層 Fleet / Task Management 系統負責。

---

## Cancel

若底層 Nav2 Action 支援 Cancel，SUB-009 應直接使用既有 Cancel 機制。

初版不建立額外 Preemption Policy。

多任務搶占、Priority 與 Retry Policy 留待 Fleet Management 階段處理。

---

## 系統參數

| 參數 | 初版設定 |
|---|---|
| Supported Target | Station ID、Goal Pose |
| Canonical Goal | `geometry_msgs/msg/PoseStamped` |
| Navigation Action | Nav2 `NavigateToPose` |
| Automatic Retry | 不啟用 |
| Task Queue | 不提供 |
| Priority | 不提供 |

---

## 軟體組成

```text
task_interface
├── Target Input Adapter
├── Target Type Validation
├── Station Resolver Client
├── Navigation Client
└── Diagnostics
```

不建立：

```text
Custom Navigation Action Server
Task Scheduler
Task Queue
Route Planner
Navigation State Machine
```

除非後續需求明確要求。

---

## 設計依據

SUB-009 依下列順序完成設計確認：

1. UC-002 導航至指定目標。
2. CAP-002 自主導航至指定目標。
3. SYS-008 Navigation Target。
4. SYS-009 Target Resolution。
5. SYS-017 Navigation Result。
6. ROS 2 Action。
7. Nav2 `NavigateToPose`。
8. SUB-010 Target Resolution。
9. SUB-011 Navigation。

設計原則為：

- 優先沿用 Nav2 原生介面。
- Task Interface 維持薄層 Adapter。
- Target Resolution 與 Navigation Execution 分離。
- 不提前建立 Fleet / Scheduler 功能。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Station Input | 可接收有效 Station ID |
| Pose Input | 可接收有效 Goal Pose |
| Invalid Target | 非法 Target 可被拒絕 |
| Station Resolution | Station ID 可經 SUB-010 取得 Goal Pose |
| Pose Pass-through | Goal Pose 可直接形成 Canonical Goal Pose |
| Navigation Dispatch | Canonical Goal Pose 可交由 SUB-011 |
| Feedback | 可取得 Nav2 Navigation Feedback |
| Success Result | 成功導航可正確回報 |
| Failure Result | 導航失敗可正確回報 |
| Cancel | 可沿用 Nav2 Cancel 機制 |
| Repeatability | 可重複提交 Navigation Target |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-008 | SUB-009 |
| SYS-009 | SUB-009 |
| SYS-017 | SUB-009 |

# SUB-010 Target Resolution

## 目的

Target Resolution 子系統負責解析 Navigation Target，產生 Canonical Goal Pose，並管理 Navigation 所需之 Route Graph 資源。

本子系統專注於導航目標解析，不負責導航規劃、導航控制或 Route Search。

---

## 對應需求

| Requirement |
|---|
| SYS-009 |
| SYS-012 |
| SYS-018 |
| SYS-019 |
| SYS-020 |
| SYS-021 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| ROS | ROS 2 Jazzy |
| Navigation Target | Station、Goal Pose |
| Canonical Goal | `geometry_msgs/msg/PoseStamped` |
| Route Graph | `route_graph.geojson` |
| Station Database | `stations.yaml` |
| Navigation | SUB-011 Navigation |

---

## 系統職責

- 解析 Navigation Target。
- Station ID 轉換為 Goal Pose。
- 驗證 Station 是否存在。
- 載入 Station Database。
- 載入 Route Graph。
- 提供 Route Graph 給 Navigation。
- 提供 Canonical Goal Pose。

Target Resolution 不負責：

- Route Planning。
- Route Search。
- Path Planning。
- Controller。
- Navigation Strategy。
- Localization。
- Navigation Execution。

---

## 邏輯架構

```text
Navigation Target
        │
        ▼
 Target Resolution
        │
 ┌──────┴──────┐
 ▼             ▼
Station      Goal Pose
 ▼             │
stations.yaml  │
 ▼             │
Goal Pose      │
 └──────┬──────┘
        ▼
Canonical Goal Pose
        │
        ▼
SUB-011 Navigation
        │
        ▼
Route Graph
```

---

# Navigation Target

系統支援：

| Target | 說明 |
|---|---|
| Station | 預先定義導航站點 |
| Goal Pose | 任意導航目標 |

所有 Target 最終皆轉換為：

```text
geometry_msgs/msg/PoseStamped
```

---

# Station Database

Station Database：

```text
stations.yaml
```

定義：

```yaml
stations:
  station_a:
    x: 1.0
    y: 2.0
    yaw: 0.0

  station_b:
    x: 5.5
    y: 3.2
    yaw: 1.57
```

Station 定義：

- Position
- Orientation

Station 不綁定：

- Route Node
- Graph Node ID

Station 表示：

> AMR 最終應抵達的位置。

---

# Route Graph

Target Resolution 管理：

```text
route_graph.geojson
```

用途：

提供 Navigation 可利用之 Route Graph。

Route Graph：

不表示 Navigation Target。

不表示 Station。

僅表示：

> 可利用之導航路網。

Route Search 完全交由：

```text
Nav2 Route Server
```

完成。

---

# Map Package

```text
maps/
└── <map_name>/
    ├── map.pgm
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

Target Resolution 使用：

- stations.yaml
- route_graph.geojson

Map Package 切換時同步更新。

---

# Target Resolution Flow

## Station

```text
Station ID
     │
stations.yaml
     │
     ▼
Goal Pose
```

若 Station 不存在：

回傳 Invalid Target。

---

## Goal Pose

```text
Goal Pose
      │
      ▼
Goal Pose
```

直接 Pass Through。

---

# Canonical Goal Pose

所有 Navigation Target 最終形成：

```text
geometry_msgs/msg/PoseStamped
```

Navigation 不需知道：

- Goal 來自 Station。
- Goal 來自 Goal Pose。

Navigation 永遠使用：

```text
Canonical Goal Pose
```

---

# Navigation Integration

Target Resolution：

```text
Goal Pose
```

Navigation：

```text
Current Pose

Goal Pose

Route Graph
```

Navigation Strategy：

由 Navigation 決定。

不是 Target Resolution。

---

# Route Graph Integration

Route Graph：

```text
route_graph.geojson
```

由：

```text
Nav2 Route Server
```

載入。

Target Resolution：

不實作：

- Graph Loader。
- Route Planner。
- Route Search。
- Nearest Node Search。

上述能力全部沿用：

Nav2 Route。

---

# ROS Interface

Target Resolution 初版不發布 Topic。

輸入：

```text
Station ID
```

或：

```text
Goal Pose
```

輸出：

```text
geometry_msgs/msg/PoseStamped
```

Route Graph 由 Navigation 啟動流程載入。

---

# 系統參數

| 參數 | 初版設定 |
|---|---|
| Station Database | `stations.yaml` |
| Route Graph | `route_graph.geojson` |
| Canonical Goal | `geometry_msgs/msg/PoseStamped` |

---

# 軟體組成

```text
target_resolution
├── Station Database Loader
├── Station Resolver
├── Route Graph Resource Manager
├── Validation
└── Diagnostics
```

不建立：

```text
Graph Loader

Route Planner

Nearest Node Search

Graph Traversal
```

全部交由：

```text
Nav2 Route
```

---

# 設計依據

SUB-010 依下列順序完成設計確認：

1. UC-002 導航至指定目標。
2. CAP-002 自主導航至指定目標。
3. SYS-009 Navigation Target Processing。
4. Nav2 Route。
5. SUB-009 Task Interface。
6. SUB-011 Navigation。

設計原則：

- Navigation 永遠使用 Goal Pose。
- Station 僅為 Goal Pose 的來源之一。
- Route Graph 為 Navigation 可利用之導航資源。
- 優先使用 Nav2 Route 現有能力。

---

# 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Station Load | 可成功載入 `stations.yaml` |
| Route Graph Load | Nav2 可成功載入 `route_graph.geojson` |
| Station Resolution | Station ID 可解析為 Goal Pose |
| Invalid Station | 不存在 Station 可正確回報 |
| Goal Pose Pass-through | Goal Pose 可直接輸出 |
| Canonical Goal | 所有 Target 可形成 Canonical Goal Pose |
| Map Switch | Map Package 切換後同步更新 |
| Repeatability | 重複解析結果一致 |

---

# Traceability

| Requirement | Subsystem |
|---|---|
| SYS-009 | SUB-010 |
| SYS-012 | SUB-010 |
| SYS-018 | SUB-010 |
| SYS-019 | SUB-010 |
| SYS-020 | SUB-010 |
| SYS-021 | SUB-010 |

# SUB-011 Navigation

## 目的

Navigation 子系統負責接收 Canonical Goal Pose，取得 AMR 目前位姿，並整合 Nav2 完成定位、導航策略執行、路徑規劃、路徑追蹤、障礙物處理、到達判定與導航結果回報。

Navigation 不關心 Goal Pose 原本來自 Station ID 或使用者直接指定之 Pose。

初版優先使用 Nav2 既有 Server、Plugin、Behavior Tree 與 Action，不自行實作 Navigation Planner、Controller 或 Route Planner。

---

## 對應需求

| Requirement |
|---|
| SYS-010 |
| SYS-011 |
| SYS-012 |
| SYS-013 |
| SYS-014 |
| SYS-015 |
| SYS-016 |
| SYS-017 |
| SYS-018 |
| SYS-019 |
| SYS-020 |
| SYS-021 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| ROS | ROS 2 Jazzy |
| Navigation Framework | Nav2 |
| Canonical Goal | `geometry_msgs/msg/PoseStamped` |
| Localization | `nav2_amcl` |
| Navigation Orchestration | `nav2_bt_navigator` |
| Free-space Planning | `nav2_planner` |
| Path Following | `nav2_controller` |
| Obstacle Representation | `nav2_costmap_2d` |
| Route Navigation | `nav2_route` |
| Map | SUB-008 Map Management |
| Navigation Resources | SUB-010 Target Resolution |
| Task Interface | SUB-009 Task Interface |
| Base Control | SUB-001 Drive Hardware Interface |

---

## 系統職責

- 接收 Canonical Goal Pose。
- 取得 AMR Current Pose。
- 提供靜態地圖定位。
- 執行 Navigation Behavior Tree。
- 優先利用適用之 Route Graph。
- 支援 First Mile。
- 支援 On Route Navigation。
- 支援 Last Mile。
- Route Graph 不適用時執行 Free-space Navigation。
- 使用 Global / Local Costmap 表示環境障礙物。
- 規劃可執行 Navigation Path。
- 控制 AMR 沿 Path 移動。
- 發布底盤速度命令。
- 判定導航進度。
- 判定 Goal Pose 是否抵達。
- 提供 Navigation Feedback。
- 提供 Navigation Result。
- 管理 Nav2 Lifecycle。

Navigation 不負責：

- Navigation Target 輸入介面。
- Station ID 解析。
- Station Database 管理。
- Map Package 檔案管理。
- Route Graph 編輯。
- Route Graph 自訂搜尋演算法。
- 感測器 Driver。
- Wheel Odometry。
- Sensor Fusion。
- Task Queue。
- Fleet Scheduling。

---

## 核心架構

```text
                 Canonical Goal Pose
                         │
                         ▼
                  SUB-011 Navigation
                         │
                         ▼
                   BT Navigator
                         │
                         ▼
               Navigation Behavior Tree
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       Route-assisted          Free-space
        Navigation              Navigation
              │                     │
              └──────────┬──────────┘
                         ▼
                  Planner Server
                         │
                         ▼
                Controller Server
                         │
                         ▼
                     /cmd_vel
                         │
                         ▼
                SUB-001 Drive Hardware Interface
```

---

## Canonical Goal

SUB-011 僅接受：

```text
geometry_msgs/msg/PoseStamped
```

作為 Navigation Goal。

上游流程：

```text
Station ID
    │
    ▼
SUB-010
    │
    ▼
Goal Pose
```

或：

```text
Goal Pose
    │
    ▼
SUB-009
    │
    ▼
Goal Pose
```

最後均形成：

```text
Canonical Goal Pose
        │
        ▼
SUB-011 Navigation
```

因此 Navigation 不需要知道：

- Goal 是否來自 Station。
- Station ID 為何。
- Goal 是否位於 Route Graph Node。
- Target Resolution 如何完成。

---

# Navigation Strategy

Navigation Strategy 由 Nav2 Behavior Tree 編排。

初版不建立額外的：

```text
Custom Strategy Selector Node
```

而是優先透過 Nav2 Behavior Tree 組合：

- Route Server
- Planner Server
- Controller Server
- Recovery / Behavior

完成導航策略。

系統策略原則：

1. 可合理利用 Route Graph 時，優先執行 Route-assisted Navigation。
2. Current Pose 不在 Route Graph 上時，使用 First Mile 銜接路網。
3. Goal Pose 不在 Route Graph 上時，使用 Last Mile 銜接目標。
4. Route Graph 不適用或 Route-assisted Navigation 無法使用時，允許使用 Free-space Navigation。
5. 實際策略條件與 fallback 行為於 Behavior Tree 實機驗證後定版。

---

# Route-assisted Navigation

Route-assisted Navigation 利用既有 Route Graph 約束或引導 AMR 的主要移動路線。

```text
Current Pose
      │
      ▼
 First Mile
      │
      ▼
 Route Graph
      │
      ▼
   On Route
      │
      ▼
 Last Mile
      │
      ▼
  Goal Pose
```

Route Graph：

```text
maps/<map_name>/route_graph.geojson
```

由 Nav2 Route Server 使用。

SUB-011 不自行實作：

- Graph Search。
- Graph Traversal。
- Nearest Node Search。
- Route Cost Algorithm。
- Route Tracking Algorithm。

上述能力優先沿用 `nav2_route`。

---

## First Mile

First Mile 負責由 AMR Current Pose 銜接 Route Graph。

```text
Current Pose
      │
      ▼
Planner Server
      │
      ▼
Route Entry
```

First Mile 使用 Nav2 既有 Free-space Planner 完成。

SUB-011 不自行實作 First Mile Planner。

---

## On Route

On Route 階段由 Nav2 Route Server 提供 Route Graph 導航能力。

```text
Route Entry
     │
     ▼
Nav2 Route Server
     │
     ▼
Route
     │
     ▼
Route Exit
```

Route Server 負責 Route 計算與 Route Tracking。

---

## Last Mile

Last Mile 負責由 Route Graph 離開點銜接 Canonical Goal Pose。

```text
Route Exit
     │
     ▼
Planner Server
     │
     ▼
Goal Pose
```

Goal Pose 不需要位於 Route Graph Node。

因此 Station 與 Route Graph 維持解耦。

---

# Free-space Navigation

若 Route Graph 不適用，Navigation 可直接執行 Free-space Navigation。

```text
Current Pose
      │
      ▼
Planner Server
      │
      ▼
Global Path
      │
      ▼
Controller Server
      │
      ▼
Goal Pose
```

Free-space Navigation 使用 Nav2 既有：

- Planner Server
- Controller Server
- Costmaps
- Goal Checker
- Progress Checker
- Behavior Tree

不自行實作 Global Planner 或 Local Planner。

---

# Navigation Behavior Tree

Behavior Tree 負責 Navigation 流程編排。

概念流程：

```text
Canonical Goal Pose
        │
        ▼
 Navigation Behavior Tree
        │
        ├── Route-assisted Navigation
        │       ├── Compute Route
        │       ├── First Mile
        │       ├── On Route
        │       └── Last Mile
        │
        ├── Free-space Navigation
        │       ├── Compute Path
        │       └── Follow Path
        │
        └── Recovery / Failure Handling
```

初版優先沿用 Nav2 官方 Behavior Tree 與既有 BT Node。

僅在現有 Behavior Tree 無法滿足 v0.1 Navigation Strategy 時，才新增最小必要的 BT 組合或 Plugin。

---

# Localization

Navigation 使用靜態 Map Localization。

```text
Map Package
    │
    ▼
Map Server
    │
    ▼
  /map
    │
    ▼
  AMCL
    │
    ▼
map → odom
```

系統里程：

```text
/wheel_odom
/rf2o_odom
/imu/data_raw
      │
      ▼
SUB-006 Robot Localization EKF
      │
      ├── /odom
      └── odom → base_footprint
```

最終 TF：

```text
map
 │
 └── odom
      │
      └── base_footprint
            │
            └── base_link
```

---

# LiDAR 使用原則

Navigation 優先直接使用 SUB-002 提供之原始 LiDAR Topic：

```text
/scan_front_left
/scan_back_right
```

使用原則：

1. 下游元件可直接接收多個原始來源時，直接使用原始 Topic。
2. 單一原始來源已足夠時，直接使用單一原始 Topic。
3. 僅於下游介面限制且原始資料無法滿足功能需求時，才評估 LaserScan Fusion。
4. 初版不預設導入 LaserScan Fusion。

---

# Costmap

Navigation 使用：

- Global Costmap
- Local Costmap

概念資料流：

```text
/scan_front_left ─────┐
                 ├──► Costmap Observation Sources
/scan_back_right ──────┘
```

若 Nav2 Costmap 可直接設定兩個 Observation Source，直接使用兩個原始 LiDAR Topic。

Costmap 提供：

- Static Map。
- Robot Footprint。
- Obstacle Layer。
- Inflation Layer。
- Local Obstacle Representation。

實際 Layer 與 Plugin 以 Nav2 Baseline 起始，實機導航後調整。

---

# Planner Server

Planner Server 負責產生 Free-space Path。

使用場景包含：

- 完整 Free-space Navigation。
- First Mile。
- Last Mile。
- Route-assisted Navigation 中需要之局部自由空間規劃。

初版 Planner Plugin 優先採用 Nav2 成熟 Plugin。

正式 Plugin 依差速底盤與實機場域測試決定。

---

# Controller Server

Controller Server 負責：

- Path Following。
- Local Motion Control。
- Goal Checking。
- Progress Checking。
- 產生 Velocity Command。

輸出：

```text
/cmd_vel
```

初版 Controller Plugin 優先採用 Nav2 成熟 Plugin。

正式 Plugin 依實機追蹤品質與底盤特性決定。

---

# Goal Checking

所有導航目標最終皆為 Canonical Goal Pose。

因此 Goal Checking 使用一致條件：

- Goal Position。
- Goal Orientation。
- Position Tolerance。
- Yaw Tolerance。

```text
Current Pose
      │
      ▼
 Goal Checker
      │
      ▼
 Goal Pose
```

Station Goal 不需要特殊 Goal Checker。

Station 最終已解析為 Goal Pose。

---

# ROS Interface

## Input

| Interface | Type | 說明 |
|---|---|---|
| Canonical Goal Pose | `geometry_msgs/msg/PoseStamped` | Navigation Goal |
| `/map` | `nav_msgs/msg/OccupancyGrid` | Navigation Map |
| `/odom` | `nav_msgs/msg/Odometry` | 系統里程 |
| `/scan_front_left` | `sensor_msgs/msg/LaserScan` | Front-Left LiDAR |
| `/scan_back_right` | `sensor_msgs/msg/LaserScan` | Back-Right LiDAR |
| `/tf` | TF2 | Dynamic TF |
| `/tf_static` | TF2 | Static TF |

---

## Navigation Action

初版優先整合 Nav2 既有：

```text
NavigateToPose
```

Navigation Target 在進入 SUB-011 前已解析為 Canonical Goal Pose。

不另外建立與 Nav2 重複的 Navigation Action Server。

---

## Output

| Interface | Type | 說明 |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 底盤速度命令 |
| Navigation Feedback | Nav2 Action Feedback | 導航進度 |
| Navigation Result | Nav2 Action Result | 導航結果 |

---

# TF Interface

```text
map
 │
 └── odom
      │
      └── base_footprint
            │
            └── base_link
                  ├── base_imu_link
                  ├── base_lidar_link_FL
                  └── base_lidar_link_BR
```

| Transform | Publisher |
|---|---|
| `map → odom` | AMCL |
| `odom → base_footprint` | SUB-006 Robot Localization EKF |
| `base_footprint → base_link` | SUB-012 Robot Description |
| `base_link → sensor frames` | SUB-012 Robot Description |

Navigation 模式中 `map → odom` 僅由 AMCL 發布。

---

# Navigation Result

Navigation Result 優先沿用 Nav2 既有 Action Result。

SUB-011 不另外建立自定義 Result Protocol。

至少需支援：

```text
Succeeded
Failed
Canceled
```

Navigation Feedback 與 Result 交由 SUB-009 回報使用者。

---

# Recovery

Navigation Recovery 優先使用 Nav2 Behavior Tree 與既有 Behavior Server 能力。

初版不自行建立 Recovery Framework。

可使用之行為依 Nav2 Baseline 與實機需求確認，例如：

- Clear Costmap。
- Wait。
- Spin。
- Back Up。

僅保留實機有必要之 Recovery Behavior。

---

# Lifecycle

Nav2 元件使用 Lifecycle Management。

主要元件包含：

```text
Map Server
AMCL
Route Server
Planner Server
Controller Server
BT Navigator
Behavior Server
```

初版使用 `nav2_lifecycle_manager` 管理 Nav2 元件啟停與狀態。

---

# 系統參數

## Frames and Topics

| 參數 | 初版設定 |
|---|---|
| Map Frame | `map` |
| Odom Frame | `odom` |
| Base Frame | `base_footprint` |
| Odom Topic | `/odom` |
| Front-Left Scan | `/scan_front_left` |
| Back-Right Scan | `/scan_back_right` |
| Velocity Topic | `/cmd_vel` |

---

## Navigation Resources

| Resource | Path |
|---|---|
| Map | `maps/<map_name>/map.yaml` |
| Route Graph | `maps/<map_name>/route_graph.geojson` |

`stations.yaml` 不由 SUB-011 直接使用。

Station 已在 SUB-010 解析為 Canonical Goal Pose。

---

## Navigation Parameters

下列參數初版採 Nav2 Baseline：

- Planner Plugin
- Controller Plugin
- Goal Checker
- Progress Checker
- Costmap Parameters
- Robot Footprint
- Inflation Radius
- Navigation Behavior Tree
- Recovery Behavior
- Position Tolerance
- Yaw Tolerance

正式設定以實機導航結果確認。

---

# 軟體組成

```text
navigation
├── Nav2 Bringup
├── BT Navigator
├── AMCL
├── Route Server
├── Planner Server
├── Controller Server
├── Global Costmap
├── Local Costmap
├── Behavior Server
├── Lifecycle Manager
├── Parameters
└── Diagnostics
```

初版不建立：

```text
Custom Route Planner
Custom Global Planner
Custom Local Planner
Custom Strategy Selector
Custom Navigation Action Server
Custom Recovery Framework
```

除非實機驗證證明 Nav2 既有能力無法滿足需求。

---

# 設計依據

SUB-011 依下列順序完成設計確認：

1. UC-002 導航至指定目標。
2. CAP-002 自主導航至指定目標。
3. SYS-010～SYS-021。
4. ROS 2 Jazzy Navigation2。
5. Nav2 `NavigateToPose`。
6. Nav2 Route Server。
7. Nav2 Behavior Tree。
8. Nav2 Planner Server。
9. Nav2 Controller Server。
10. Nav2 Costmap。
11. Nav2 AMCL。
12. SUB-006 Robot Localization EKF。
13. SUB-008 Map Management。
14. SUB-009 Task Interface。
15. SUB-010 Target Resolution。
16. 實機導航驗證。

設計原則：

- Navigation 永遠處理 Canonical Goal Pose。
- Target Source 與 Navigation Execution 解耦。
- Route Graph 為 Navigation Strategy 資源。
- Route-assisted Navigation 優先使用 Nav2 Route。
- Free-space Navigation 優先使用 Nav2 Planner。
- Navigation Strategy 優先使用 Behavior Tree 編排。
- 不重複實作 Nav2 已提供能力。

---

# 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Canonical Goal | 可接收有效 Goal Pose |
| Map Load | 可載入指定 Map Package |
| Localization | AMCL 可持續提供有效定位 |
| TF | TF Tree 完整且無重複發布 |
| Route Graph Load | Nav2 Route Server 可載入 Route Graph |
| Route Planning | 可計算適用 Route |
| First Mile | Current Pose 不在 Route 上時可銜接路網 |
| On Route | AMR 可沿 Route Graph 導航 |
| Last Mile | Route Graph 未到達 Goal 時可銜接 Goal Pose |
| Free-space Navigation | 不使用 Route Graph 時可直接導航至 Goal Pose |
| Route-assisted Strategy | 適用 Route Graph 時可優先利用路網 |
| Route Fallback | Route-assisted 無法使用時可依 BT Policy 處理 |
| Planner | 可產生可執行 Path |
| Controller | AMR 可穩定追蹤 Path |
| Costmap | 可使用原始 LiDAR 建立障礙物資訊 |
| Obstacle Avoidance | 導航時可處理環境障礙物 |
| Goal Checking | 可正確判定 Goal Pose 抵達 |
| Velocity Command | `/cmd_vel` 持續提供有效速度命令 |
| Feedback | 可提供 Navigation Feedback |
| Result | 可正確回報成功、失敗或取消 |
| Repeatability | 可重複執行不同 Navigation Target |
| Long Duration | 長時間導航期間 Nav2 元件持續穩定運作 |

---

# Traceability

| Requirement | Subsystem |
|---|---|
| SYS-010 | SUB-011 |
| SYS-011 | SUB-011 |
| SYS-012 | SUB-011 |
| SYS-013 | SUB-011 |
| SYS-014 | SUB-011 |
| SYS-015 | SUB-011 |
| SYS-016 | SUB-011 |
| SYS-017 | SUB-011 |
| SYS-018 | SUB-011 |
| SYS-019 | SUB-011 |
| SYS-020 | SUB-011 |
| SYS-021 | SUB-011 |

# SUB-012 Robot Description

## 目的

Robot Description 子系統負責定義 AMR 之機器人幾何、座標系與關節，
提供 TF、感測器安裝位姿、ros2_control 硬體介面宣告與導航所需之車體輪廓。

本子系統為靜態描述資源，不含執行期邏輯。

---

## 對應需求

| Requirement |
|---|
| SYS-023 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| ROS | ROS 2 Jazzy |
| 描述格式 | URDF（xacro） |
| 幾何資產 | STL meshes |
| 發布元件 | `robot_state_publisher` |
| 來源 | 既有專案 `FIH_AMR_ROBOT_V2.0` |

---

## 系統職責

- 定義車體與輪組之連桿與關節。
- 定義感測器安裝位姿（LiDAR ×2、IMU）。
- 定義 `base_footprint` 與 `base_link` 之關係。
- 提供 ros2_control `<ros2_control>` 硬體介面宣告。
- 提供導航所需之車體輪廓（footprint）。
- 經 `robot_state_publisher` 發布靜態與關節 TF。

不負責：

- TF 之 `map → odom`（SUB-007 / SUB-011）與 `odom → base_footprint`（SUB-006）。
- 感測器驅動與資料處理。
- 運動控制與里程。

---

## 範圍

既有專案 URDF 為完整人形 AMR（含軀幹、雙臂、雙手、頭部）。
本子系統僅涵蓋 `mobile_base` v0.1 所需部分：

| 項目 | 納入 |
|---|---|
| `base_footprint`、`base_link` | ✅ |
| 驅動輪 ×2 與懸吊 | ✅ |
| Caster ×4 | ✅ |
| LiDAR ×2、IMU 安裝 frame | ✅ |
| 軀幹、手臂、手部、頭部 | ❌ 不納入 |

上半身於後續版本需要時再行加入，不預先建立未使用之描述。

---

## TF Interface

本子系統提供之座標關係：

```text
base_footprint
      │
      ▼
  base_link
      ├── driving_wheel_link_L / driving_wheel_link_R
      ├── caster_* （×4 組）
      ├── base_imu_link
      ├── base_lidar_link_FL
      └── base_lidar_link_BR
```

`base_footprint → base_link` 為固定轉換，由 `robot_state_publisher` 發布。

輪關節之轉動由 `joint_state_broadcaster` 提供 `/joint_states`，
經 `robot_state_publisher` 轉為 TF。

---

## Frame 命名

| Frame / Joint | 說明 |
|---|---|
| `base_footprint` | 車體於地面之投影，導航與定位基準 |
| `base_link` | 車體本體座標系 |
| `driving_wheel_joint_L` / `driving_wheel_joint_R` | 驅動輪關節，ros2_control 控制對象 |
| `base_imu_link` | IMU 安裝座標系（SUB-003） |
| `base_lidar_link_FL` | 前左 LiDAR（SUB-002） |
| `base_lidar_link_BR` | 後右 LiDAR（SUB-002） |

**既有 URDF 之名稱不予改動**，各子系統規格一律配合 URDF。
`base_footprint` 為新增連桿（來源 URDF 未定義），不影響既有名稱。

Topic 名稱不受此限制，與 frame 之對應如下：

| Topic | Frame |
|---|---|
| `/scan_front_left` | `base_lidar_link_FL` |
| `/scan_back_right` | `base_lidar_link_BR` |
| `/imu/data_raw` | `base_imu_link` |

---

## ros2_control 宣告

URDF 須包含 `<ros2_control>` 區段，宣告：

- SUB-001 Drive Hardware Interface 之 hardware interface 插件。
- 左右驅動輪之 `position` / `velocity` state interface
  與 `velocity` command interface。
- 插件所需之硬體參數（序列埠、Driver ID 等）。

---

## 軟體組成

```text
mobile_base_description
├── urdf/          機器人描述（xacro）
├── meshes/        STL 幾何資產
├── config/        （視需要）
└── launch/        robot_state_publisher
```

---

## 被動關節處理

來源 URDF 之 caster（swivel／suspension／wheel 共 16 個）與驅動輪懸吊
（prismatic ×2）皆為被動關節，無編碼器亦無任何 joint state 來源。

保留為可動將使 TF tree 殘缺並持續產生 tf2 警告，故一律宣告為 `fixed`。
僅 `driving_wheel_joint_L` / `driving_wheel_joint_R` 維持 `continuous`，
由 `joint_state_broadcaster` 提供狀態。

此為型別調整，未更動任何名稱。v0.1 不需建模懸吊行程與 caster 轉向；
日後若需精確視覺化，可還原型別並另行提供 joint state 來源。

---

## 幾何參數

由來源 URDF 取得，供交叉驗證：

| 項目 | 值 |
|---|---|
| 左輪中心 y | +0.2775 m |
| 右輪中心 y | −0.2770 m |
| 輪距（推算） | 0.5545 m |
| LiDAR FL | (+0.28771, +0.26721, −0.06011) |
| LiDAR BR | (−0.24671, −0.26721, −0.06011) |
| IMU | (+0.04375, −0.00800, −0.01459) |

輪距推算值 0.5545 m 與 SUB-004 採用之 Baseline 值 0.555 m 相符（差 0.5 mm）。

---

## 設計依據

SUB-012 依下列順序完成設計確認：

1. 既有專案 `FIH_AMR_ROBOT_V2.0` URDF 與 meshes。
2. 實車安裝配置確認（LiDAR 對角、IMU 位置）。
3. ros2_control URDF 規範。
4. SUB-002 / SUB-003 感測器 frame 需求。
5. SUB-006 TF tree 需求。
6. 實機 TF 與掃描方向驗證。

設計原則：

- 沿用既有 URDF 之幾何數值，不重新建模。
- 僅納入目前版本所需之連桿與關節。
- Frame 命名與各子系統規格一致。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| URDF 解析 | `robot_state_publisher` 可載入且無錯誤（2026-08-07 已確認） |
| TF Tree | 單一樹、root 為 `base_footprint`、25 links 無斷點（2026-08-07 已確認） |
| 靜態 TF | `/tf_static` 發布 22 筆固定轉換（2026-08-07 已確認） |
| 輪關節 | `/joint_states` 可驅動輪關節 TF 轉動（2026-08-07 已確認） |
| Frame 命名 | 與 SUB-002／SUB-003／SUB-006 規格一致（2026-08-07 已確認） |
| Mesh 載入 | RViz 可正確顯示車體幾何 |
| 感測器位姿 | LiDAR 與 IMU 之安裝位姿與實車一致 |
| 尺寸 | 車體輪廓與實車量測一致 |
| ros2_control | `controller_manager` 可依 `<ros2_control>` 載入硬體介面 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-023 | SUB-012 |
