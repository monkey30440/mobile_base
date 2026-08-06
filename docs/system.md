# Subsystem Design

本文件定義 `mobile_base` 各子系統之目的、責任、介面與驗證方式。

---

## SUB-001 底盤控制

### 目的

底盤控制子系統負責接收 AMR 運動命令，控制左右輪驅動器完成車體運動，並提供底盤運動資訊作為定位、建圖與導航之基礎。

---

### 對應需求

| Requirement |
|---|
| SYS-002 |
| SYS-005 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| 運算平台 | Jetson AGX Orin Developer Kit |
| 馬達驅動器 | DEXMART M1C-N016RE ×2 |
| 通訊介面 | RS-485 |
| 通訊協議 | Modbus Multi-drive 2.0 |
| 裝置 | `/dev/ttyUSB0` |
| ROS | ROS 2 Jazzy |

---

### 系統職責

- 接收 AMR 運動命令。
- 執行差速運動學計算。
- 控制左右輪速度。
- 讀取左右輪運動回授。
- 發布底盤運動資訊。
- 提供驅動器狀態。

---

### 邏輯架構

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

### ROS Interface

#### Subscribe

| Topic | Type |
|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` |

#### Publish

| Topic | 說明 |
|---|---|
| `/odom/raw` | 底盤運動資訊 |
| `/wheel_states` | 左右輪運動回授 |
| `/driver/status` | Driver 狀態 |

---

### External Interface

| 裝置 | 介面 |
|---|---|
| DEXMART M1 Driver | RS-485 |
| Multi-drive 2.0 | Modbus RTU |

---

### 系統參數

#### Vehicle Parameters

| 參數 | 初版來源 |
|---|---|
| Wheel Radius | 現有專案 Baseline |
| Wheel Separation | 現有專案 Baseline |
| Gear Ratio | 現有專案 Baseline |

上述參數於 Hardware Bring-up 完成後，以實機量測結果更新。

#### Driver Parameters

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

### 設計依據

SUB-001 設計依下列順序完成：

1. 官方文件。
2. 既有實作。
3. Hardware Bring-up。
4. 實機量測。
5. Hardware Configuration。

---

### 軟體組成

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

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Driver 通訊 | 可建立 RS-485 通訊 |
| Driver 控制 | 左右輪可獨立控制 |
| 差速控制 | AMR 可完成直行與原地旋轉 |
| Wheel Feedback | 可持續取得左右輪回授 |
| Odometry | 可持續發布底盤運動資訊 |
| 長時間運轉 | 建圖期間穩定運作 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-002 | SUB-001 |
| SYS-005 | SUB-001 |

---

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
| `intensities` | LiDAR 強度資料，依 Driver 支援 |

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

---

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

---

### ROS Interface

#### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/imu/data_raw` | `sensor_msgs/msg/Imu` | IMU 原始量測資料 |

---

### TF Interface

| Parent Frame | Child Frame | 來源 |
|---|---|---|
| `base_link` | `imu_link` | URDF |

IMU 安裝位置與座標方向以既有 URDF 為初版 Baseline，並透過實機靜止與旋轉測試確認。

---

### 資料內容

| 欄位 | 初版處理 |
|---|---|
| `header.stamp` | 使用 Driver 產生之訊息時間 |
| `header.frame_id` | `imu_link` |
| `angular_velocity` | 轉換為 rad/s |
| `linear_acceleration` | 轉換為 m/s² |
| `orientation` | 維持未提供狀態 |
| `angular_velocity_covariance` | 依 Driver Baseline 與實機量測設定 |
| `linear_acceleration_covariance` | 依 Driver Baseline 與實機量測設定 |
| `orientation_covariance` | 標示 orientation 未提供 |

---

### 系統參數

| 參數 | 初版來源 |
|---|---|
| Device | `/dev/ttyACM0` |
| Baud Rate | 既有 Driver Baseline |
| Output Rate | 既有 Driver Baseline |
| Gyroscope Range | 既有 Driver Baseline |
| Accelerometer Range | 既有 Driver Baseline |
| Frame ID | `imu_link` |
| Topic | `/imu/data_raw` |
| Axis Mapping | URDF 與實機測試 |

---

### 設計依據

SUB-003 依下列順序完成設計確認：

1. IIM-42652 Datasheet。
2. 既有 ROS 2 Driver。
3. Hardware Bring-up。
4. 實機靜止與旋轉測試。
5. 下游運動估測需求。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| 裝置存取 | 系統可開啟 `/dev/ttyACM0` |
| Driver 啟動 | IMU Driver 可持續運作 |
| Topic 發布 | `/imu/data_raw` 持續發布 |
| 訊息格式 | 訊息型別為 `sensor_msgs/msg/Imu` |
| 時間戳記 | `header.stamp` 持續遞增 |
| Frame ID | `header.frame_id` 為 `imu_link` |
| 靜止測試 | 線性加速度方向與重力方向一致 |
| 旋轉測試 | 角速度軸向與 AMR 實際旋轉方向一致 |
| 單位確認 | 角速度與線性加速度使用 SI 單位 |
| 持續運轉 | 建圖期間持續發布有效資料 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-004 | SUB-003 |

---

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
          ▼
    /wheel_odom
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

Wheel Odometry 初版不發布系統 `odom → base_footprint` TF。

系統里程 TF 由 Robot Localization EKF 單一發布。

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
| 持續運轉 | 建圖期間持續發布資料 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-005 | SUB-004 |

---

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

---

### ROS Interface

#### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| 可設定 Scan Topic | `sensor_msgs/msg/LaserScan` | RF2O 雷射掃描輸入 |

#### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/rf2o_odom` | `nav_msgs/msg/Odometry` | RF2O 雷射里程資訊 |

初版分別測試 `/scan_front` 與 `/scan_rear`，依實機運動估測結果選定正式輸入。

---

### TF Interface

RF2O 初版不發布系統 `odom → base_footprint` TF。

系統里程 TF 由 Robot Localization EKF 單一發布。

---

### 資料內容

| 欄位 | 初版處理 |
|---|---|
| `header.stamp` | 使用 Scan 對應時間 |
| `header.frame_id` | `odom` |
| `child_frame_id` | `base_footprint` |
| Position | RF2O 平面位姿估測 |
| Orientation | RF2O 平面航向估測 |
| Linear Velocity | RF2O 線速度估測 |
| Angular Velocity | RF2O 角速度估測 |
| Covariance | 依套件 Baseline 與實機量測設定 |

---

### 系統參數

| 參數 | 初版來源 |
|---|---|
| Scan Topic | `/scan_front` 與 `/scan_rear` 實機比較 |
| Odom Topic | `/rf2o_odom` |
| Odom Frame | `odom` |
| Base Frame | `base_footprint` |
| Initial Pose | 零位姿 |
| Publish TF | 關閉 |
| Processing Rate | LiDAR Scan 更新頻率 |

---

### 輸入選擇

RF2O 初版使用單一 LiDAR Topic。

輸入選擇依下列實機結果確認：

1. 靜止期間位姿穩定性。
2. 直線移動估測一致性。
3. 原地旋轉估測一致性。
4. 建圖環境中的持續追蹤能力。
5. LiDAR 視野與車體遮蔽情形。

---

### 設計依據

SUB-005 依下列順序完成設計確認：

1. RF2O 套件文件與既有實作。
2. SUB-002 LiDAR Topic。
3. `/scan_front` 實機測試。
4. `/scan_rear` 實機測試。
5. Robot Localization 輸入需求。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Scan 輸入 | RF2O 可持續接收指定 LaserScan |
| Topic 發布 | `/rf2o_odom` 持續發布 |
| 訊息格式 | `nav_msgs/msg/Odometry` |
| 靜止測試 | AMR 靜止時位姿維持穩定 |
| 直線移動 | 位移方向與實際運動一致 |
| 原地旋轉 | 航向變化與實際旋轉方向一致 |
| Scan 比較 | 完成前後 LiDAR 輸入測試並選定正式來源 |
| 持續運轉 | 建圖期間持續提供有效里程資訊 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-003 | SUB-005 |

---

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

---

### ROS Interface

#### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/wheel_odom` | `nav_msgs/msg/Odometry` | 輪式里程資訊 |
| `/rf2o_odom` | `nav_msgs/msg/Odometry` | 雷射里程資訊 |
| `/imu/data_raw` | `sensor_msgs/msg/Imu` | IMU 原始量測資料 |

#### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/odom` | `nav_msgs/msg/Odometry` | 融合後系統里程資訊 |

---

### TF Interface

| Parent Frame | Child Frame | 發布來源 |
|---|---|---|
| `odom` | `base_footprint` | Robot Localization EKF |

`odom → base_footprint` 由 Robot Localization EKF 單一發布。

---

### 融合範圍

初版採二維運動模式，融合以下資訊：

| 資料來源 | 初版融合內容 |
|---|---|
| Wheel Odometry | 平面線速度、角速度與相對位姿 |
| RF2O Odometry | 平面相對位姿、線速度與角速度 |
| IMU | Z 軸角速度 |

IMU 線性加速度依實機穩定性與濾波結果評估後納入。

---

### 座標系

| Frame | 用途 |
|---|---|
| `odom` | 連續局部里程座標 |
| `base_footprint` | AMR 平面基準座標 |
| `base_link` | AMR 車體座標 |
| `imu_link` | IMU 感測器座標 |

---

### 系統參數

| 參數 | 初版設定 |
|---|---|
| Frequency | 依輸入 Topic 更新率設定 |
| Sensor Timeout | 依實機 Topic 週期設定 |
| Two-D Mode | 啟用 |
| World Frame | `odom` |
| Odom Frame | `odom` |
| Base Link Frame | `base_footprint` |
| Publish TF | 啟用 |
| Wheel Odom Topic | `/wheel_odom` |
| RF2O Odom Topic | `/rf2o_odom` |
| IMU Topic | `/imu/data_raw` |

Process Noise、Initial Estimate Covariance 與各輸入欄位設定以套件 Baseline 建立，並透過實機運動測試完成調整。

---

### 輸入資料要求

| 項目 | 要求 |
|---|---|
| 時間戳記 | 持續遞增並使用一致時間基準 |
| Frame ID | 與 TF Tree 一致 |
| 單位 | 使用 ROS 標準 SI 單位 |
| Covariance | 反映各資料來源的量測可信度 |
| 更新率 | 可支援連續 EKF 更新 |
| TF 發布 | 系統里程 TF 由 EKF 單一發布 |

---

### 設計依據

SUB-006 依下列順序完成設計確認：

1. `robot_localization` 套件文件。
2. SUB-003 IMU 輸出。
3. SUB-004 Wheel Odometry 輸出。
4. SUB-005 RF2O Odometry 輸出。
5. 實機直線與旋轉測試。
6. SLAM Toolbox 輸入需求。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| 輸入接收 | EKF 持續接收三組輸入 Topic |
| Topic 發布 | `/odom` 持續發布 |
| 訊息格式 | `nav_msgs/msg/Odometry` |
| TF 發布 | `odom → base_footprint` 持續發布 |
| 靜止測試 | AMR 靜止時里程資訊維持穩定 |
| 直線運動 | 位移方向與實際運動一致 |
| 原地旋轉 | 航向與旋轉方向一致 |
| 持續運轉 | 建圖期間持續提供有效里程資訊 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-003 | SUB-006 |
| SYS-004 | SUB-006 |
| SYS-005 | SUB-006 |

---

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
| 套件 | `slam_toolbox` |
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

---

### 邏輯架構

```text
/scan_front 或 /scan_rear
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

其餘 SLAM 參數採用 `slam_toolbox` Baseline，並於實機建圖完成後調整。

---

### 設計依據

SUB-007 依下列順序完成設計確認：

1. `slam_toolbox` 文件。
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

---

## SUB-008 Map Management

### 目的

Map Management 子系統負責管理二維地圖及其關聯導航資源，提供地圖儲存、載入與後續導航使用。

---

### 對應需求

| Requirement |
|---|
| SYS-007 |
| SYS-008 |
| SYS-009 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| ROS 套件 | `nav2_map_server` |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |
| 地圖格式 | Occupancy Grid |
| 管理單位 | Map Package |

---

### 系統職責

- 儲存二維地圖。
- 載入指定 Map Package。
- 管理地圖與導航資源之對應關係。
- 提供 Occupancy Grid 地圖。
- 提供 Route Graph 檔案位置。
- 提供 Station Mapping 檔案位置。

---

### Map Package

一個場域之地圖與導航資源以 Map Package 集中管理。

```text
maps/
└── <map_name>/
    ├── map.pgm
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

| 檔案 | 用途 |
|---|---|
| `map.pgm` | Occupancy Grid 地圖影像 |
| `map.yaml` | Occupancy Grid 地圖設定 |
| `route_graph.geojson` | Nav2 Route Graph |
| `stations.yaml` | Station ID 與 Route Node ID 對應 |

---

### 邏輯架構

```text
                Map Package
                     │
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
 Occupancy Grid  Route Graph  Station Mapping
        │            │             │
        ▼            ▼             ▼
  Map Server    Route Server   Station Navigation
```

---

### ROS Interface

#### Subscribe

| Topic | Type | 說明 |
|---|---|---|
| `/map` | `nav_msgs/msg/OccupancyGrid` | 建圖結果 |

#### Publish

| Topic | Type | 說明 |
|---|---|---|
| `/map` | `nav_msgs/msg/OccupancyGrid` | 載入之導航地圖 |

#### Service

| Service | 說明 |
|---|---|
| Save Map | 儲存目前 Occupancy Grid |
| Load Map | 載入指定 Occupancy Grid |

---

### 地圖儲存

UC-001 建圖完成後，系統將地圖儲存至指定 Map Package：

```text
maps/<map_name>/
├── map.pgm
└── map.yaml
```

Route Graph 與 Station Mapping 於 UC-002 路網站點導航建置期間加入同一 Map Package。

---

### 地圖載入

系統以 `map_name` 選擇 Map Package。

```text
map_name
    │
    ▼
maps/<map_name>/
    │
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

Map Management 提供各資源之固定路徑，供 Map Server、Route Graph Management 與 Station Navigation 使用。

---

### 系統參數

| 參數 | 初版設定 |
|---|---|
| Map Root | `maps/` |
| Map Name | 使用者指定 |
| Map YAML | `map.yaml` |
| Map Image | `map.pgm` |
| Route Graph | `route_graph.geojson` |
| Station Mapping | `stations.yaml` |

---

### 設計依據

SUB-008 依下列順序完成設計確認：

1. UC-001 地圖儲存需求。
2. UC-002 地圖與路網載入需求。
3. `nav2_map_server`。
4. Nav2 Route Graph。
5. 實機地圖儲存與載入驗證。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Package 建立 | 可建立指定名稱之 Map Package |
| 地圖儲存 | 成功產生 `map.yaml` 與 `map.pgm` |
| 地圖載入 | 成功載入指定 Map Package 之地圖 |
| 資源定位 | 可取得 Route Graph 與 Station Mapping 路徑 |
| 地圖一致性 | 載入後內容與儲存前一致 |
| 多地圖管理 | 可依 `map_name` 選擇不同 Map Package |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-007 | SUB-008 |
| SYS-008 | SUB-008 |
| SYS-009 | SUB-008 |

---

## SUB-009 Task Interface

### 目的

Task Interface 子系統負責接收使用者透過終端提交之路網站點移動任務，將任務轉換為系統內部導航請求，並提供任務執行狀態與完成結果。

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
| 操作者介面 | Terminal |
| 任務類型 | 路網站點移動任務 |
| 任務輸入 | Target Station |
| 任務輸出 | Task Status、Navigation Result |
| 運算平台 | Jetson AGX Orin Developer Kit |
| ROS | ROS 2 Jazzy |

---

### 系統職責

- 接收使用者指定之目標站點。
- 建立路網站點移動任務。
- 為任務配置唯一識別碼。
- 將任務提交至 Station Navigation。
- 接收導航執行狀態。
- 顯示任務目前狀態。
- 顯示任務完成結果。

---

### 邏輯架構

```text
使用者
  │
  │ Target Station
  ▼
Terminal Command
  │
  ▼
Task Interface
  │
  ├── Task ID
  ├── Task Type
  ├── Target Station
  └── Task Timestamp
  │
  ▼
Station Navigation
  │
  │ Task Status / Result
  ▼
Task Interface
  │
  ▼
使用者
```

---

### 任務資料

| 欄位 | 說明 |
|---|---|
| `task_id` | 任務唯一識別碼 |
| `task_type` | 路網站點移動 |
| `target_station` | 使用者指定之目標站點識別碼 |
| `created_at` | 任務建立時間 |
| `status` | 任務執行狀態 |
| `result` | 任務完成結果 |

---

### 任務狀態

| 狀態 | 說明 |
|---|---|
| `accepted` | 系統完成任務接收 |
| `planning` | 系統正在產生導航路徑 |
| `navigating` | AMR 正在執行移動 |
| `completed` | AMR 已抵達目標站點 |

---

### ROS Interface

初版透過 ROS 2 Action 建立非同步任務介面。

#### Action Goal

| 欄位 | 說明 |
|---|---|
| `target_station` | 目標站點識別碼 |

#### Action Feedback

| 欄位 | 說明 |
|---|---|
| `task_id` | 任務識別碼 |
| `status` | 任務目前狀態 |

#### Action Result

| 欄位 | 說明 |
|---|---|
| `task_id` | 任務識別碼 |
| `status` | 任務最終狀態 |
| `reached_station` | AMR 抵達之站點識別碼 |

Action 名稱與自定義訊息格式於 Interface Design 階段確認。

---

### 終端操作

初版終端命令提供目標站點參數：

```text
ros2 action send_goal <station_navigation_action> <goal_message>
```

Task Interface 將終端輸入轉換為內部任務資料並提交執行。

---

### 資料流

| 資料 | 來源 | 目的地 |
|---|---|---|
| Target Station | 使用者 | Task Interface |
| Navigation Task | Task Interface | Station Navigation |
| Task Status | Station Navigation | Task Interface |
| Navigation Result | Station Navigation | Task Interface |
| Status Display | Task Interface | 使用者 |

---

### 系統參數

| 參數 | 初版設定 |
|---|---|
| Task Type | Station Navigation |
| User Interface | ROS 2 Terminal |
| Communication Model | ROS 2 Action |
| Task ID | 系統自動產生 |
| Target Format | Station ID |
| Status Output | Terminal |

---

### 設計依據

SUB-009 依下列順序完成設計確認：

1. UC-002 路網站點移動任務。
2. CAP-002 導航至指定路網站點。
3. ROS 2 Action 通訊模型。
4. Station Navigation 輸入需求。
5. 實機導航任務驗證。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| 任務提交 | 使用者可透過終端指定目標站點 |
| 任務識別 | 每項任務具備唯一 Task ID |
| 任務轉換 | Target Station 可轉換為內部導航任務 |
| 任務傳遞 | Station Navigation 可接收導航任務 |
| 狀態更新 | 終端可顯示任務執行狀態 |
| 完成結果 | 終端可顯示抵達站點與完成狀態 |
| 重複執行 | 可依序執行多項路網站點移動任務 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-012 | SUB-009 |
| SYS-017 | SUB-009 |

---

## SUB-010 Route Graph Management

### 目的

Route Graph Management 子系統負責管理 Map Package 中之 Route Graph 與 Station Mapping，提供路網站點導航所需之路網資料，並整合 Nav2 Route Server 完成 Route Graph 載入。

---

### 對應需求

| Requirement |
|---|
| SYS-010 |
| SYS-013 |
| SYS-014 |

---

### 系統邊界

| 項目 | 規格 |
|---|---|
| 核心套件 | `nav2_route` |
| Route Server | Nav2 Route Server |
| Graph Format | GeoJSON |
| Graph Editor | Nav2 Route Tool |
| Map Package | `maps/<map_name>/` |
| Coordinate Frame | `map` |
| ROS | ROS 2 Jazzy |
| 運算平台 | Jetson AGX Orin Developer Kit |

---

### 系統職責

- 載入 Map Package 中之 Route Graph。
- 載入 Map Package 中之 Station Mapping。
- 提供 Station ID 與 Route Node ID 對應。
- 提供 Route Graph 載入狀態。
- 提供 Route Graph 給 Nav2 Route Server。
- 維持 Route Graph 與 Occupancy Grid 地圖一致。

Route 規劃、Route Tracking、Route Operation 與 Edge Cost 由 Nav2 Route Server 負責。

---

### Map Package

每個場域以一個 Map Package 管理所有導航資源。

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
| `map.pgm` | Occupancy Grid 地圖 |
| `map.yaml` | Occupancy Grid 設定 |
| `route_graph.geojson` | Nav2 Route Graph |
| `stations.yaml` | Station ID 與 Route Node ID 對應 |

---

### 邏輯架構

```text
                Map Package
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    map.yaml   route_graph   stations.yaml
                     │            │
                     ▼            ▼
             Route Graph     Station Mapping
                     │            │
                     └─────┬──────┘
                           ▼
              Route Graph Management
                           │
                           ▼
                  Nav2 Route Server
```

---

### Route Graph

Route Graph 使用 Nav2 Route Tool 建立，並由 Nav2 Route Server 載入。

Route Graph 包含：

- Route Node
- Route Edge
- Edge Direction
- Edge Cost
- Route Metadata

Graph 編輯、儲存與載入採用 Nav2 官方工具與資料格式。

---

### Station Mapping

Station Mapping 保存業務站點與 Route Node 的對應關係。

```yaml
stations:
  station_a:
    node_id: 10
    yaw: 0.0

  station_b:
    node_id: 20
    yaw: 1.5708
```

| 欄位 | 說明 |
|---|---|
| `station_id` | 使用者操作之站點名稱 |
| `node_id` | Route Graph Node ID |
| `yaw` | 到站目標朝向 |

Route Graph 保存導航拓樸；Station Mapping 作為業務站點與導航節點之橋接。

---

### 路網建立流程

1. 使用 UC-001 建立之 Occupancy Grid。
2. 載入 `map.yaml`。
3. 使用 Nav2 Route Tool 建立 Route Graph。
4. 建立 Route Node 與 Route Edge。
5. 儲存 `route_graph.geojson`。
6. 建立 `stations.yaml`。
7. 將所有檔案保存至同一 Map Package。
8. 啟動 Nav2 Route Server。

---

### ROS Interface

#### 輸入

| 項目 | 說明 |
|---|---|
| Map Package | 地圖資源 |
| Route Graph | `route_graph.geojson` |
| Station Mapping | `stations.yaml` |
| Map Name | 指定載入之地圖 |

#### 輸出

| 項目 | 說明 |
|---|---|
| Route Graph | Nav2 Route Server |
| Station Mapping | Station Navigation |
| Graph Status | Route Graph 載入狀態 |

---

### 系統參數

| 參數 | 初版設定 |
|---|---|
| Map Root | `maps/` |
| Map Name | 使用者指定 |
| Route Graph | `route_graph.geojson` |
| Station Mapping | `stations.yaml` |
| Graph Loader | GeoJSON |
| Coordinate Frame | `map` |

---

### 設計依據

SUB-010 依下列順序完成設計確認：

1. UC-002 路網站點移動任務。
2. SUB-008 Map Management。
3. Nav2 Route Server。
4. Nav2 Route Tool。
5. 實機路網建立流程。

初版優先採用 Nav2 提供之 Route Graph、Graph Loader 與 Route Tool，降低自訂路網管理程式。

---

### 驗證項目

| 驗證項目 | 完成條件 |
|---|---|
| Map Package | 成功載入指定 Map Package |
| Route Graph | 成功載入 `route_graph.geojson` |
| Station Mapping | 成功載入 `stations.yaml` |
| Graph 一致性 | Route Graph 與 Occupancy Grid 對齊 |
| Station Mapping | 可依 Station ID 取得 Route Node |
| Route Server | Nav2 Route Server 可成功載入 Route Graph |
| 多地圖 | 可切換不同 Map Package |
| 重複載入 | 相同 Map Package 可得到一致結果 |

---

### Traceability

| Requirement | Subsystem |
|---|---|
| SYS-010 | SUB-010 |
| SYS-013 | SUB-010 |
| SYS-014 | SUB-010 |