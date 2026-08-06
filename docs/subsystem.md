# Subsystem Design

本文件定義 `mobile_base` 各子系統之目的、職責、系統邊界、介面、設計依據與驗證方式，作為系統實作、整合測試與維護之依據。

子系統依功能劃分如下：

| ID | Subsystem |
|---|---|
| SUB-001 | Base Control |
| SUB-002 | LiDAR Perception |
| SUB-003 | IMU Perception |
| SUB-004 | Wheel Odometry |
| SUB-005 | RF2O Odometry |
| SUB-006 | Robot Localization EKF |
| SUB-007 | SLAM Toolbox |
| SUB-008 | Map Management |
| SUB-009 | Task Interface |
| SUB-010 | Route Graph Management |
| SUB-011 | Navigation |

---

# SUB-001 Base Control

## 目的

Base Control 子系統負責接收 AMR 運動命令，控制差速底盤完成運動，並提供底盤運動回授，作為里程估測與定位之基礎。

---

## 對應需求

| Requirement |
|---|
| SYS-002 |

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

---

## 系統職責

- 接收底盤速度命令。
- 執行差速輪運動學計算。
- 控制左右輪驅動器。
- 讀取左右輪運動回授。
- 發布底盤運動資訊。
- 提供驅動器狀態。

---

## 邏輯架構

```text
            /cmd_vel
                │
                ▼
         Base Controller
                │
 Differential Drive Kinematics
                │
      ┌─────────┴─────────┐
      ▼                   ▼
 Left Wheel Cmd      Right Wheel Cmd
      │                   │
      └─────────┬─────────┘
                ▼
     Modbus Multi-drive 2.0
                │
             RS-485
                │
      ┌─────────┴─────────┐
      ▼                   ▼
 Left Driver         Right Driver
      │                   │
      └─────────┬─────────┘
                ▼
         Wheel Feedback
                │
                ▼
          ROS 2 Interface
```

---

## ROS Interface

### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 底盤速度命令 |

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/wheel_states` | 自定義訊息 | 左右輪回授資訊 |
| `/driver/status` | 自定義訊息 | Driver 狀態 |

Base Control 不負責 Wheel Odometry 計算。

Wheel Odometry 由 **SUB-004 Wheel Odometry** 負責。

---

## External Interface

| 裝置 | 介面 |
|---|---|
| Left Driver | RS-485 |
| Right Driver | RS-485 |

Driver Register、Control Word 與 Status Word 初版依 DEXMART 官方文件設定，實機 Bring-up 完成後確認。

---

## 差速運動學

Base Control 採用 Differential Drive 模型。

輸入：

- 車體線速度
- 車體角速度

輸出：

- 左輪目標速度
- 右輪目標速度

Vehicle Geometry 由下列參數決定：

- Wheel Radius
- Wheel Separation
- Gear Ratio

初版沿用既有 Baseline，後續以實機量測結果更新。

---

## 系統參數

### Vehicle Parameters

| 參數 | 初版來源 |
|---|---|
| Wheel Radius | 既有 Baseline |
| Wheel Separation | 既有 Baseline |
| Gear Ratio | 既有 Baseline |

上述參數於 Hardware Bring-up 完成後，以實機量測確認。

---

### Driver Parameters

下列參數依驅動器設定決定：

- Driver ID
- Baud Rate
- Control Mode
- Encoder Resolution
- Maximum Motor RPM
- Acceleration
- Deceleration
- Torque Limit

初版依官方文件建立設定，Bring-up 後確認。

---

## 軟體組成

```text
base_control
├── Driver Interface
├── Modbus Transport
├── Differential Kinematics
├── Parameter Manager
└── Diagnostics
```

Package 結構於 Implementation 階段確認。

---

## 設計依據

SUB-001 依下列順序完成設計確認：

1. DEXMART Driver 官方文件。
2. Modbus Multi-drive 2.0 通訊協議。
3. 現有專案 Baseline。
4. Hardware Bring-up。
5. Vehicle Parameter 實機量測。
6. Driver Configuration 確認。

初版優先沿用既有成熟 Driver 設定，不重新設計 Driver Protocol。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Driver 通訊 | 可建立 RS-485 通訊 |
| Driver 控制 | 左右輪可獨立控制 |
| 差速控制 | AMR 可完成直行與原地旋轉 |
| Wheel Feedback | 可持續取得左右輪回授 |
| `/cmd_vel` | 底盤可正確執行速度命令 |
| 長時間運轉 | 建圖與導航期間持續穩定運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-002 | SUB-001 |

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
| 通訊介面 | Ethernet |
| Coordinate Frame | URDF 定義 |

---

## 系統職責

- 建立前方 LiDAR 通訊。
- 建立後方 LiDAR 通訊。
- 接收兩顆 LiDAR 掃描資料。
- 分別發布標準 ROS 2 `LaserScan` Topic。
- 提供各 LiDAR 裝置狀態。
- 保留並提供原始 LiDAR 量測資料。

LiDAR Perception 僅負責提供原始 LiDAR 資料。

是否需要資料融合，由下游子系統依介面能力與實機需求決定。

---

## 邏輯架構

```text
Front picoScan150                    Rear picoScan150
        │                                    │
        ▼                                    ▼
Front LiDAR Driver                   Rear LiDAR Driver
        │                                    │
        ▼                                    ▼
  /scan_front                          /scan_rear
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
              Downstream Consumers
```

兩顆 LiDAR 分別發布 `/scan_front` 與 `/scan_rear`。

初版維持兩個獨立原始 Topic。

---

## LiDAR 資料使用原則

- SUB-002 持續發布原始 `/scan_front` 與 `/scan_rear`。
- 下游可直接接收多個原始 LiDAR Topic 時，直接使用原始資料。
- 下游僅需單一來源且單一原始 Topic 可滿足需求時，使用選定之原始 Topic。
- 僅於下游介面無法直接接收所需原始資料，且單一來源無法滿足功能需求時，才評估 LaserScan Fusion。
- LaserScan Fusion 屬於依下游需求導入之相容層，不屬於 SUB-002 預設功能。

---

## ROS Interface

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/scan_front` | `sensor_msgs/msg/LaserScan` | 前方 LiDAR 原始掃描資料 |
| `/scan_rear` | `sensor_msgs/msg/LaserScan` | 後方 LiDAR 原始掃描資料 |

SUB-002 不發布預設融合後 Scan Topic。

---

## TF Interface

| Parent Frame | Child Frame |
|---|---|
| `base_link` | `front_laser_frame` |
| `base_link` | `rear_laser_frame` |

LiDAR 安裝位置與姿態由 URDF 管理。

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
| Front Frame ID | `front_laser_frame` |
| Rear Frame ID | `rear_laser_frame` |
| Front Topic | `/scan_front` |
| Rear Topic | `/scan_rear` |

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
├── Front LiDAR Driver
├── Rear LiDAR Driver
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
| Front Driver | 可持續接收前方 LiDAR |
| Rear Driver | 可持續接收後方 LiDAR |
| Front Topic | `/scan_front` 持續發布 |
| Rear Topic | `/scan_rear` 持續發布 |
| Message Type | 兩個 Topic 均為 `sensor_msgs/msg/LaserScan` |
| Frame ID | 與 URDF 定義一致 |
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
| Coordinate Frame | URDF 定義 |

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
| `base_link` | `imu_link` |

IMU 安裝位置與座標方向由 URDF 管理。

初版沿用既有 URDF Baseline，並透過實機靜止與旋轉測試確認。

---

## IMU 訊息

`/imu/data_raw` 使用 `sensor_msgs/msg/Imu`。

| 欄位 | 初版處理 |
|---|---|
| `header.stamp` | 使用 Driver 產生之訊息時間 |
| `header.frame_id` | `imu_link` |
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
| Frame ID | `imu_link` |
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
- X、Y、Z 軸與 `imu_link` 定義一致。

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
| Frame ID | `header.frame_id` 為 `imu_link` |
| Angular Velocity | 旋轉方向與實際運動一致 |
| Linear Acceleration | 靜止時重力方向一致 |
| Unit | 使用 ROS 2 標準 SI 單位 |
| Axis Mapping | 與 URDF 定義一致 |
| Long Duration | 建圖與導航期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-004 | SUB-003 |

# SUB-004 Wheel Odometry

## 目的

Wheel Odometry 子系統負責根據左右輪運動回授計算 AMR 平面里程資訊，發布標準 ROS 2 `Odometry` 訊息，提供 Robot Localization EKF 作為感測器融合輸入。

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
| 運動模型 | Differential Drive |
| 資料來源 | SUB-001 Base Control |
| Coordinate Frame | URDF 定義 |

---

## 系統職責

- 接收左右輪運動回授。
- 執行 Differential Drive 運動學計算。
- 推算 AMR 平面位姿。
- 推算 AMR 線速度。
- 推算 AMR 角速度。
- 發布標準 ROS 2 `Odometry` Topic。
- 提供 Wheel Odometry 狀態。

Wheel Odometry 僅負責輪式里程估測。

感測器融合、系統里程與 TF 發布由 **SUB-006 Robot Localization EKF** 負責。

---

## 邏輯架構

```text
      /wheel_states
             │
             ▼
     Wheel Odometry
             │
 Differential Drive
    Kinematics
             │
             ├── Position
             ├── Orientation
             ├── Linear Velocity
             └── Angular Velocity
             │
             ▼
       /wheel_odom
```

---

## ROS Interface

### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/wheel_states` | 自定義訊息 | 左右輪運動回授 |

### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/wheel_odom` | `nav_msgs/msg/Odometry` | Wheel Odometry |

---

## TF Interface

Wheel Odometry 不發布 TF。

系統唯一的：

```text
odom → base_footprint
```

由 **SUB-006 Robot Localization EKF** 發布。

---

## Odometry

`/wheel_odom` 使用 `nav_msgs/msg/Odometry`。

| 欄位 | 初版處理 |
|---|---|
| `header.frame_id` | `odom` |
| `child_frame_id` | `base_footprint` |
| Position | Differential Drive 推算 |
| Orientation | Differential Drive 推算 |
| Linear Velocity | 左右輪速度推算 |
| Angular Velocity | 左右輪速度推算 |
| Covariance | 初版採 Baseline，實機調整 |

Wheel Odometry 提供相對運動估測，不保證長時間絕對定位精度。

---

## Differential Drive

Wheel Odometry 使用標準 Differential Drive 運動模型。

輸入：

- 左輪速度
- 右輪速度

輸出：

- X Position
- Y Position
- Heading
- Linear Velocity
- Angular Velocity

Vehicle Geometry 使用：

- Wheel Radius
- Wheel Separation
- Gear Ratio

初版沿用既有 Baseline，Hardware Bring-up 後以實機量測確認。

---

## 系統參數

### Vehicle Parameters

| 參數 | 初版來源 |
|---|---|
| Wheel Radius | 既有 Baseline |
| Wheel Separation | 既有 Baseline |
| Gear Ratio | 既有 Baseline |

---

### Odometry Parameters

下列參數依實機調整：

- Encoder Resolution
- Update Rate
- Covariance
- Initial Pose

初版沿用既有 Baseline，Hardware Bring-up 完成後確認。

---

## 軟體組成

```text
wheel_odometry
├── Differential Kinematics
├── Odometry Integration
├── Parameter Manager
└── Diagnostics
```

Package 結構於 Implementation 階段確認。

---

## 設計依據

SUB-004 依下列順序完成設計確認：

1. Differential Drive 運動模型。
2. 現有專案 Baseline。
3. SUB-001 Base Control。
4. Hardware Bring-up。
5. Vehicle Geometry 實機量測。
6. Robot Localization 輸入需求。

初版優先採用成熟 Differential Drive 運動模型，不自行設計 Wheel Odometry 演算法。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Wheel Feedback | 可持續接收左右輪回授 |
| Topic Publish | `/wheel_odom` 持續發布 |
| Message Type | `nav_msgs/msg/Odometry` |
| Straight Motion | 直線位移方向正確 |
| Rotation | 原地旋轉方向正確 |
| Velocity | 線速度與角速度合理 |
| Covariance | Covariance 正常設定 |
| TF | 不發布 `odom → base_footprint` |
| Long Duration | 建圖與導航期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-005 | SUB-004 |

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
| Coordinate Frame | URDF 定義 |

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

---

## LiDAR 輸入原則

RF2O 優先直接使用 SUB-002 提供之原始 LiDAR Topic。

選擇順序：

1. 確認 RF2O 套件支援的輸入形式。
2. 若套件可直接接收所需之多個原始來源，直接使用原始 Topic。
3. 若套件僅接受單一 `LaserScan`，分別驗證 `/scan_front` 與 `/scan_rear`。
4. 選用可穩定提供 RF2O 里程估測的單一原始來源。
5. 單一原始來源可滿足需求時維持不融合。
6. 僅於介面限制且單一來源無法滿足功能需求時，才評估 LaserScan Fusion。

初版不預設導入 LaserScan Fusion。

---

## ROS Interface

### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/scan_front` 或 `/scan_rear` | `sensor_msgs/msg/LaserScan` | RF2O 原始 Scan 輸入 |

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

- `/scan_front`
- `/scan_rear`

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
6. `/scan_front` 與 `/scan_rear` 實機比較。
7. LaserScan Fusion 必要性評估。
8. Robot Localization 輸入需求。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Input Capability | 完成 RF2O 原始 Scan 輸入能力確認 |
| Front Scan Test | 完成 `/scan_front` RF2O 測試 |
| Rear Scan Test | 完成 `/scan_rear` RF2O 測試 |
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

- 接收 Wheel Odometry。
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
├── imu_link
├── front_laser_frame
└── rear_laser_frame
```

由 URDF 提供。

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
4. SUB-004 Wheel Odometry。
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
3. 若僅接受單一 `LaserScan`，分別驗證 `/scan_front` 與 `/scan_rear`。
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
| `base_footprint → base_link` | URDF |
| `base_link → sensor frames` | URDF |

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
7. `/scan_front` 與 `/scan_rear` 實機建圖比較。
8. LaserScan Fusion 必要性評估。
9. Occupancy Grid 實機驗證。

初版先以原始 LiDAR Topic 與套件 Baseline 完成可重複建圖，再進行必要調整。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Input Capability | 完成 SLAM Toolbox 原始 Scan 輸入能力確認 |
| Front Scan Test | 完成 `/scan_front` 建圖測試 |
| Rear Scan Test | 完成 `/scan_rear` 建圖測試 |
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
- 提供 Route Graph Management 所需之 Route Graph 與 Station Mapping 路徑。
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
2. UC-002 與 UC-003 地圖載入需求。
3. `nav2_map_server`。
4. SUB-007 SLAM Toolbox 輸出。
5. SUB-010 Route Graph Management 資源需求。
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
| SYS-007 | SUB-008 |
| SYS-008 | SUB-008 |
| SYS-009 | SUB-008 |

# SUB-009 Task Interface

## 目的

Task Interface 子系統負責接收使用者提交之導航任務，驗證任務內容、轉換為系統內部導航請求，並管理導航任務生命週期，提供一致的任務介面供上層系統使用。

初版支援：

- Station Navigation（UC-002）
- Pose Navigation（UC-003）

Task Interface 不負責導航規劃與控制，而是負責任務管理與派送。

---

## 對應需求

| Requirement |
|---|
| SYS-010 |
| SYS-011 |
| SYS-012 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| ROS | ROS 2 Jazzy |
| 任務型態 | Navigation Task |
| 支援導航模式 | Station Navigation、Pose Navigation |
| 任務執行者 | SUB-011 Navigation |

---

## 系統職責

- 接收 Navigation Task。
- 驗證任務內容。
- 識別導航任務類型。
- 建立 Navigation Goal。
- 派送導航任務。
- 接收導航執行結果。
- 回報任務狀態。
- 管理任務生命週期。

Task Interface 不負責：

- Route Planning
- Route Graph
- Localization
- Navigation Control
- Motion Control

---

## 邏輯架構

```text
                 User
                  │
                  ▼
          Navigation Task
                  │
          Task Validation
                  │
          Task Classification
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
Station Navigation     Pose Navigation
        │                   │
        └─────────┬─────────┘
                  ▼
        SUB-011 Navigation
                  │
                  ▼
          Navigation Result
                  │
                  ▼
             Task Status
```

---

## Navigation Task

Task Interface 統一管理所有導航任務。

初版支援：

| Task Type | 說明 |
|---|---|
| Station Navigation | 導航至指定 Station |
| Pose Navigation | 導航至指定 Goal Pose |

未來可擴充：

- Dock Navigation
- Patrol
- Multi-goal Navigation
- Fleet Dispatch

無須修改 Navigation 子系統介面。

---

## 任務生命週期

所有 Navigation Task 使用一致生命週期。

```text
Created
    │
    ▼
Validated
    │
    ▼
Dispatched
    │
    ▼
Executing
    │
 ┌──┴─────┐
 ▼        ▼
Succeeded Failed
```

Task Interface 管理狀態，不管理導航細節。

---

## ROS Interface

### Subscribe

Task Interface 初版不直接訂閱感測器 Topic。

導航結果由 Navigation Action 回傳。

---

### Action Server

初版提供一個 Navigation Action。

| Action | 說明 |
|---|---|
| Navigation Task | 接收導航任務 |

Action Goal：

| 欄位 | 說明 |
|---|---|
| `task_type` | `station_navigation` 或 `pose_navigation` |
| `target_station` | Station Navigation 使用 |
| `goal_pose` | Pose Navigation 使用 |

Action Feedback：

| 欄位 | 說明 |
|---|---|
| Current State | 任務狀態 |
| Navigation Status | Navigation 執行狀態 |

Action Result：

| 欄位 | 說明 |
|---|---|
| Result | Success / Failure |
| Error Code | 失敗原因 |
| Message | 補充資訊 |

Action 型別於 Interface Design 階段定義。

---

## 與 SUB-011 關係

Task Interface 不參與導航規劃。

```text
Navigation Task
        │
        ▼
Task Interface
        │
        ▼
Navigation Goal
        │
        ▼
SUB-011 Navigation
        │
        ▼
Navigation Result
        │
        ▼
Task Status
```

Task Interface 僅負責：

- 任務建立
- 任務派送
- 任務狀態管理

Navigation 負責：

- 規劃
- 控制
- 定位
- 避障
- 到站判定

---

## Navigation Mode

### Station Navigation

輸入：

```text
Station ID
```

Task Interface 建立：

```text
Station Navigation Task
```

交由 SUB-011 Navigation 執行。

---

### Pose Navigation

輸入：

```text
geometry_msgs/msg/PoseStamped
```

Task Interface 建立：

```text
Pose Navigation Task
```

交由 SUB-011 Navigation 執行。

---

## 系統參數

| 參數 | 初版設定 |
|---|---|
| Supported Task | Station Navigation、Pose Navigation |
| Station Target | Station ID |
| Pose Target | `geometry_msgs/msg/PoseStamped` |
| Result Timeout | Navigation Parameter |
| Retry Policy | 不自動 Retry |

Retry Policy 後續版本再評估。

---

## 軟體組成

```text
task_interface
├── Task Validator
├── Task Dispatcher
├── Navigation Action Server
├── Task State Manager
├── Parameter Manager
└── Diagnostics
```

初版自訂程式僅負責：

- Navigation Task 定義
- Task 驗證
- Task 派送
- Task 狀態管理

導航能力完全重用 SUB-011。

---

## 設計依據

SUB-009 依下列順序完成設計確認：

1. UC-002 Navigation Task。
2. UC-003 Navigation Task。
3. ROS 2 Action。
4. SUB-011 Navigation 介面。
5. 未來 Fleet / Scheduler 擴充需求。
6. 實機導航驗證。

初版優先建立統一 Navigation Task 介面，避免 Station Navigation 與 Pose Navigation 使用不同 API。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Station Task | 可建立 Station Navigation 任務 |
| Pose Task | 可建立 Pose Navigation 任務 |
| Task Validation | 可拒絕非法任務 |
| Task Dispatch | 可派送至 SUB-011 |
| Action Feedback | 可持續收到執行狀態 |
| Action Result | 成功回傳導航結果 |
| State Machine | 任務生命週期正確 |
| Failure Handling | 導航失敗可正確回報 |
| Repeatability | 可重複提交導航任務 |
| Long Duration | 長時間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-012 | SUB-009 |
| SYS-017 | SUB-009 |
| SYS-018 | SUB-009 |
| SYS-023 | SUB-009 |

# SUB-010 Route Graph Management

## 目的

Route Graph Management 子系統負責管理路網拓樸與站點對應資訊，提供 Navigation 子系統路網站點導航所需之 Route Graph 與 Station Mapping。

本子系統專注於資料管理與查詢，不負責路徑規劃與導航控制。

---

## 對應需求

| Requirement |
|---|
| SYS-013 |
| SYS-014 |
| SYS-015 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| ROS | ROS 2 Jazzy |
| Route Graph | Nav2 Route (`route_graph.geojson`) |
| Station Mapping | `stations.yaml` |
| Map Package | SUB-008 Map Management |
| Navigation | SUB-011 Navigation |

---

## 系統職責

- 載入 Route Graph。
- 載入 Station Mapping。
- 驗證 Route Graph 完整性。
- 驗證 Station Mapping 完整性。
- 提供 Station ID 查詢。
- 提供 Route Node ID 查詢。
- 提供 Navigation 所需 Route Graph 資源。
- 提供 Route Graph 載入狀態。

Route Graph Management 不負責：

- Route Search
- Route Planning
- Path Planning
- Navigation
- Route Graph 編輯

上述功能由 Nav2 Route Server 或 Navigation 子系統負責。

---

## 邏輯架構

```text
               Map Package
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
route_graph.geojson       stations.yaml
        │                       │
        ▼                       ▼
 Route Graph Loader     Station Loader
        │                       │
        └───────────┬───────────┘
                    ▼
       Route Graph Management
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  Route Graph Query      Station Query
                    │
                    ▼
            SUB-011 Navigation
```

---

## Route Graph

Route Graph 採用 Nav2 Route 標準 GeoJSON 格式。

```text
route_graph.geojson
```

內容包含：

- Route Node
- Route Edge
- Edge Cost
- Graph Metadata

Route Graph Management 不解析導航策略。

Route Search 與 Route Tracking 完全交由 Nav2 Route Server。

---

## Station Mapping

Station Mapping 使用：

```text
stations.yaml
```

建立：

```text
Station ID
        │
        ▼
Route Node ID
```

例如：

```yaml
stations:
  station_a: node_001
  station_b: node_018
  station_c: node_052
```

Navigation 僅使用 Station ID。

Route Node ID 對使用者透明。

---

## Navigation 流程

Station Navigation：

```text
Station ID
      │
      ▼
Station Mapping
      │
      ▼
Route Node ID
      │
      ▼
Nav2 Route Server
      │
      ▼
SUB-011 Navigation
```

Route Graph Management 不參與：

- Route Planning
- Controller
- BT
- Costmap

---

## ROS Interface

Route Graph Management 初版不發布新的 ROS Topic。

Navigation 啟動流程：

```text
Map Package
      │
      ▼
Route Graph Management
      │
      ├── Route Graph
      └── Station Mapping
              │
              ▼
      SUB-011 Navigation
```

是否透過 ROS Parameter、Service 或 Library API 整合，由 Implementation 階段決定。

---

## Resource Interface

### Input

| Resource | 說明 |
|---|---|
| `route_graph.geojson` | Nav2 Route Graph |
| `stations.yaml` | Station Mapping |

由 SUB-008 Map Management 提供路徑。

---

### Output

| Resource | 說明 |
|---|---|
| Route Graph | Navigation 使用 |
| Route Node ID | Station Navigation 使用 |

---

## Map Package

Route Graph Management 使用：

```text
maps/
└── <map_name>/
    ├── map.pgm
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

各資源用途：

| Resource | Purpose |
|---|---|
| `map.yaml` | Navigation Map |
| `route_graph.geojson` | Route Graph |
| `stations.yaml` | Station Mapping |

Map Package 切換時，同步切換 Route Graph 與 Station Mapping。

---

## 資料驗證

Route Graph Management 啟動時應完成：

### Route Graph

- 檔案存在。
- 格式合法。
- Node 唯一。
- Edge 合法。
- Graph 可載入。

### Station Mapping

- 檔案存在。
- YAML 格式合法。
- Station ID 唯一。
- Route Node ID 存在於 Route Graph。
- 不存在無效 Mapping。

若驗證失敗，Navigation 不應啟動。

---

## 系統參數

| 參數 | 初版設定 |
|---|---|
| Map Root | `maps/` |
| Map Name | Launch 指定 |
| Route Graph | `route_graph.geojson` |
| Station Mapping | `stations.yaml` |

Route Graph 與 Station Mapping 固定使用 Map Package 標準名稱。

---

## 軟體組成

```text
route_graph_management
├── Map Package Resolver
├── Route Graph Loader
├── Station Loader
├── Graph Validator
├── Station Validator
├── Query Interface
└── Diagnostics
```

專案自訂程式僅負責：

- Map Package 整合。
- Route Graph 載入。
- Station Mapping 載入。
- Station ID 查詢。
- Graph 驗證。

Route Search、Shortest Path、Graph Traversal 完全採用 `nav2_route`。

---

## 設計依據

SUB-010 依下列順序完成設計確認：

1. Nav2 Route 官方文件。
2. GeoJSON Route Graph 格式。
3. UC-002 Station Navigation。
4. SUB-008 Map Management。
5. SUB-011 Navigation。
6. Map Package 結構。
7. Route Graph 實機導航驗證。

初版優先採用 Nav2 Route 提供之 Route Graph 能力，不自行實作 Graph 演算法或 Route Planner。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Route Graph Load | 可成功載入 `route_graph.geojson` |
| Station Mapping Load | 可成功載入 `stations.yaml` |
| Graph Validation | Route Graph 格式合法 |
| Station Validation | 所有 Station ID 對應有效 Route Node |
| Station Query | 可依 Station ID 查得 Route Node |
| Package Switch | 切換 `map_name` 時同步切換所有資源 |
| Navigation Integration | SUB-011 可成功使用 Route Graph |
| Error Handling | 無效 Graph 或 Mapping 可正確回報 |
| Repeatability | 重複載入結果一致 |
| Long Duration | 長時間導航期間持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-010 | SUB-010 |
| SYS-013 | SUB-010 |
| SYS-014 | SUB-010 |

# SUB-011 Navigation

## 目的

Navigation 子系統負責執行 Station Navigation 與 Pose Navigation，整合 Nav2 Navigation Stack、定位、路徑規劃、路徑追蹤、障礙物處理與到站判定，控制 AMR 由目前位姿移動至指定導航目標。

---

## 對應需求

| Requirement |
|---|
| SYS-011 |
| SYS-014 |
| SYS-015 |
| SYS-016 |
| SYS-017 |
| SYS-018 |
| SYS-019 |
| SYS-020 |
| SYS-021 |
| SYS-022 |
| SYS-023 |

---

## 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 導航框架 | Nav2 |
| 定位 | `nav2_amcl` |
| 任務編排 | `nav2_bt_navigator` |
| 路徑規劃 | `nav2_planner` |
| 路徑追蹤 | `nav2_controller` |
| 障礙物表示 | `nav2_costmap_2d` |
| 路網導航 | `nav2_route` |
| 地圖來源 | SUB-008 Map Management |
| Route Graph 來源 | SUB-010 Route Graph Management |
| 任務來源 | SUB-009 Task Interface |

---

## 系統職責

- 接收 Station Navigation 或 Pose Navigation 目標。
- 取得 AMR 目前地圖位姿。
- 依任務類型選擇導航流程。
- 執行靜態地圖定位。
- 規劃導航路徑。
- 追蹤導航路徑。
- 使用原始 LiDAR 資料建立 Costmap。
- 產生底盤速度命令。
- 判定導航進度。
- 判定 AMR 抵達導航目標。
- 回傳導航 Feedback 與 Result。
- 管理 Nav2 元件生命週期。

Navigation 不負責：

- Map Package 檔案管理。
- Route Graph 與 Station Mapping 內容管理。
- 感測器 Driver。
- Wheel Odometry 與 Sensor Fusion。
- 上層任務排程。

---

## 邏輯架構

```text
                    SUB-009 Task Interface
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
      Station Navigation                  Pose Navigation
            │                                   │
            ▼                                   │
SUB-010 Route Graph Management                   │
            │                                   │
            ▼                                   ▼
      Goal Route Node                       Goal Pose
            │                                   │
            └─────────────────┬─────────────────┘
                              ▼
                     SUB-011 Navigation
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
            AMCL       Planner Server   Controller Server
                              │
                              ▼
                          /cmd_vel
                              │
                              ▼
                     SUB-001 Base Control
```

---

## 導航模式

| 模式 | 目標輸入 | Route Graph | Route Server |
|---|---|---|---|
| Station Navigation | Station ID 對應之 Route Node | 使用 | 使用 |
| Pose Navigation | `geometry_msgs/msg/PoseStamped` | 不使用 | 不使用 |

兩種模式共用：

- AMCL
- BT Navigator
- Planner Server
- Controller Server
- Global Costmap
- Local Costmap
- Goal Checker
- Progress Checker
- Lifecycle Manager

---

## Station Navigation

Station Navigation 使用 Route Graph 完成指定站點導航。

```text
Station ID
    │
    ▼
SUB-010 Route Graph Management
    │
    ▼
Route Node ID
    │
    ▼
Nav2 Route Server
    │
    ├── Route Search
    ├── Route Tracking
    └── Route Operations
    │
    ▼
BT Navigator
    │
    ├── First Mile
    ├── On Route
    └── Goal Arrival
    │
    ▼
Controller Server
```

執行流程：

1. 接收目標 Route Node。
2. 取得 AMR 目前位姿。
3. Route Server 計算至目標節點之 Route。
4. Navigation 完成目前位置與 Route Graph 的銜接。
5. AMR 沿 Route Graph 移動。
6. Goal Checker 判定 AMR 抵達站點。
7. Navigation 回傳結果。

---

## Pose Navigation

Pose Navigation 直接使用 Goal Pose。

```text
Goal Pose
    │
    ▼
BT Navigator
    │
    ▼
Planner Server
    │
    ▼
Controller Server
    │
    ▼
Goal Checker
```

執行流程：

1. 接收 `Goal Pose`。
2. 驗證目標位姿位於可導航區域。
3. 取得 AMR 目前位姿。
4. Planner Server 產生全域路徑。
5. Controller Server 追蹤路徑。
6. Goal Checker 判定 AMR 抵達指定位置與朝向。
7. Navigation 回傳結果。

Pose Navigation 不使用：

- Route Graph
- Route Server
- Station Mapping

---

## Nav2 組成

| 元件 | 職責 |
|---|---|
| Map Server | 發布指定 Occupancy Grid |
| AMCL | 發布 `map → odom` 並提供地圖定位 |
| Route Server | 計算與追蹤 Route Graph 路線 |
| BT Navigator | 編排導航流程 |
| Planner Server | 產生全域路徑 |
| Controller Server | 追蹤路徑並產生速度命令 |
| Global Costmap | 提供全域可通行與障礙物資訊 |
| Local Costmap | 提供 AMR 周圍即時障礙物資訊 |
| Goal Checker | 判定位置與朝向抵達條件 |
| Progress Checker | 判定 AMR 是否持續推進 |
| Lifecycle Manager | 管理 Nav2 元件狀態 |

初版優先採用 Nav2 既有 Server、Plugin、Behavior Tree 與 Lifecycle 機制。

---

## LiDAR 與障礙物來源

Navigation 優先直接使用 SUB-002 發布之原始 LiDAR Topic。

```text
/scan_front ─────┐
                 ├──► Global Costmap
/scan_rear ──────┤
                 └──► Local Costmap
```

使用原則：

1. Costmap 支援多個 Observation Source 時，直接使用 `/scan_front` 與 `/scan_rear`。
2. 下游僅需單一來源且單一原始 Topic 可滿足需求時，使用選定之原始 Topic。
3. 僅於介面無法直接使用所需原始來源，且單一來源無法滿足障礙物覆蓋需求時，才評估 LaserScan Fusion。
4. 初版不預設導入 LaserScan Fusion。

---

## ROS Interface

### 輸入

| 介面 | Type | 說明 |
|---|---|---|
| Goal Route Node | Nav2 Route Action Goal | Station Navigation 目標節點 |
| Goal Pose | `geometry_msgs/msg/PoseStamped` | Pose Navigation 目標 |
| `/map` | `nav_msgs/msg/OccupancyGrid` | 導航地圖 |
| `/odom` | `nav_msgs/msg/Odometry` | 系統里程資訊 |
| `/scan_front` | `sensor_msgs/msg/LaserScan` | 前方原始 LiDAR |
| `/scan_rear` | `sensor_msgs/msg/LaserScan` | 後方原始 LiDAR |
| `/tf` | TF2 | 動態座標轉換 |
| `/tf_static` | TF2 | 固定座標轉換 |

### 輸出

| 介面 | Type | 說明 |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 底盤速度命令 |
| Navigation Feedback | Action Feedback | 導航執行狀態 |
| Navigation Result | Action Result | 導航完成結果 |

---

## TF Interface

```text
map
 │
 └── odom
      │
      └── base_footprint
            │
            └── base_link
                  ├── imu_link
                  ├── front_laser_frame
                  └── rear_laser_frame
```

| Transform | 發布來源 |
|---|---|
| `map → odom` | AMCL |
| `odom → base_footprint` | SUB-006 Robot Localization EKF |
| `base_footprint → base_link` | URDF |
| `base_link → sensor frames` | URDF |

Navigation 模式中，`map → odom` 僅由 AMCL 發布。

---

## 定位

Navigation 使用靜態地圖與 AMCL。

```text
Map Server
    │
    ▼
  /map
    │
原始 LiDAR Topic
    │
    ▼
   AMCL
    │
    ▼
map → odom
```

AMCL 的正式 LiDAR 輸入依套件介面與實機定位結果決定，並遵循原始資料優先原則。

---

## 路徑規劃與控制

### Planner

Planner Server 負責：

- Pose Navigation 全域路徑規劃。
- Station Navigation 的自由空間銜接路徑。
- 依 Global Costmap 產生可執行路徑。

### Controller

Controller Server 負責：

- 路徑追蹤。
- 局部障礙物處理。
- 產生 `/cmd_vel`。
- 執行 Goal Checker。
- 執行 Progress Checker。

Planner 與 Controller Plugin 初版採用 Nav2 成熟 Plugin，依差速底盤實機表現選定。

---

## 到站判定

### Station Navigation

到站條件依站點定義與 Goal Checker 設定確認：

- Route Node 位置。
- Station Mapping 定義之朝向。
- Position Tolerance。
- Yaw Tolerance。

### Pose Navigation

到站條件依 Goal Pose 與 Goal Checker 設定確認：

- 目標位置。
- 目標朝向。
- Position Tolerance。
- Yaw Tolerance。

初版採 Nav2 Baseline，實機驗證後定版。

---

## 系統參數

### Frame and Topic Parameters

| 參數 | 初版設定 |
|---|---|
| Map Frame | `map` |
| Odom Frame | `odom` |
| Base Frame | `base_footprint` |
| Odom Topic | `/odom` |
| Velocity Topic | `/cmd_vel` |
| Front Scan | `/scan_front` |
| Rear Scan | `/scan_rear` |

### Navigation Parameters

| 參數 | 初版設定 |
|---|---|
| Navigation Mode | Station 或 Pose |
| AMCL | 啟用 |
| Route Server | Station 模式啟用 |
| Global Costmap | 啟用 |
| Local Costmap | 啟用 |
| Goal Position Tolerance | Nav2 Baseline，實機調整 |
| Goal Yaw Tolerance | Nav2 Baseline，實機調整 |
| Planner Plugin | Nav2 成熟 Plugin |
| Controller Plugin | Nav2 成熟 Plugin |
| Behavior Tree | Nav2 Baseline |
| Progress Checker | Nav2 Baseline |
| Goal Checker | Nav2 Baseline |

### Station Parameters

| 參數 | 初版設定 |
|---|---|
| Route Graph | `maps/<map_name>/route_graph.geojson` |
| Station Mapping | `maps/<map_name>/stations.yaml` |

上述參數僅適用於 Station Navigation。

---

## 軟體組成

```text
navigation
├── Nav2 Bringup Integration
├── AMCL Configuration
├── Route Server Configuration
├── Planner Configuration
├── Controller Configuration
├── Costmap Configuration
├── Behavior Trees
├── Lifecycle Configuration
├── Action Adapter
└── Diagnostics
```

初版專案自訂內容限於：

- Station 與 Pose 任務介面整合。
- Map Package 路徑參數。
- Nav2 Launch 與 Parameters。
- Behavior Tree 選擇與設定。
- Diagnostics。

Navigation 演算法、Planner、Controller、Costmap 與 Route Search 優先採用 Nav2 成熟實作。

---

## 設計依據

SUB-011 依下列順序完成設計確認：

1. UC-002 Station Navigation。
2. UC-003 Pose Navigation。
3. Nav2 Jazzy 套件。
4. `nav2_route`。
5. SUB-006 Robot Localization EKF。
6. SUB-008 Map Management。
7. SUB-009 Task Interface。
8. SUB-010 Route Graph Management。
9. 原始 LiDAR 輸入能力確認。
10. 實機導航驗證。

---

## 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Map Load | Map Server 成功發布指定地圖 |
| Localization | AMCL 持續提供有效地圖定位 |
| TF | TF Tree 持續完整且無重複發布 |
| Station Goal | 可接收目標 Route Node |
| Route Planning | Route Server 可產生至目標節點之 Route |
| First Mile | AMR 可由目前位置銜接 Route Graph |
| On Route | AMR 可沿 Route Graph 移動 |
| Station Arrival | AMR 可抵達指定站點與朝向 |
| Pose Goal | 可接收有效 Goal Pose |
| Pose Planning | Planner Server 可產生至 Goal Pose 的路徑 |
| Pose Navigation | AMR 可抵達指定位置與朝向 |
| Costmap Input | Costmap 可直接使用原始 LiDAR Topic |
| Obstacle Representation | Costmap 可反映前後 LiDAR 障礙物 |
| Velocity Command | `/cmd_vel` 持續提供有效命令 |
| Feedback | SUB-009 可持續取得導航狀態 |
| Result | SUB-009 可取得導航完成結果 |
| Repeatability | 可重複執行 Station 與 Pose 任務 |
| Long Duration | 導航期間各 Nav2 元件持續正常運作 |

---

## Traceability

| Requirement | Subsystem |
|---|---|
| SYS-011 | SUB-011 |
| SYS-014 | SUB-011 |
| SYS-015 | SUB-011 |
| SYS-016 | SUB-011 |
| SYS-017 | SUB-011 |
| SYS-018 | SUB-011 |
| SYS-019 | SUB-011 |
| SYS-020 | SUB-011 |
| SYS-021 | SUB-011 |
| SYS-022 | SUB-011 |
| SYS-023 | SUB-011 |