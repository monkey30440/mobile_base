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

LiDAR 感知子系統負責取得兩顆 SICK picoScan150 的環境掃描資料，並分別提供 ROS 2 Topic 供下游應用使用。

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

- 建立兩顆 LiDAR 的 Ethernet 通訊。
- 取得兩顆 LiDAR 的掃描資料。
- 為每顆 LiDAR 指定獨立 ROS Topic。
- 為每顆 LiDAR 指定獨立 TF Frame。
- 依 URDF 提供 LiDAR 至 `base_link` 的固定座標轉換。
- 提供兩顆 LiDAR 的裝置狀態。

---

### 邏輯架構

```text
 Front picoScan150                 Rear picoScan150
         │                                 │
         ▼                                 ▼
 Front LiDAR Interface             Rear LiDAR Interface
         │                                 │
         ▼                                 ▼
    /scan/front                       /scan/rear
         │                                 │
         ▼                                 ▼
 front_laser_frame                 rear_laser_frame