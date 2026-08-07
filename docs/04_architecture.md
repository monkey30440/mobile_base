# System Architecture

## 目的

本文件定義 `mobile_base` v0.1 軟體架構。

Architecture 描述系統元件、資料流與子系統責任，不描述各子系統內部實作。

---

# Architecture Overview

```text
                    User
                     │
             Navigation Target
                     │
                     ▼
             SUB-009 Task Interface
                     │
                     ▼
              Target Resolution
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
    Station Target            Pose Target
        │                         │
        ▼                         │
 SUB-010 Route Graph              │
        │                         │
        └────────────┬────────────┘
                     ▼
            Canonical Goal Pose
                     │
                     ▼
            SUB-011 Navigation
                     │
                     ▼
          Navigation Strategy
        ┌────────────┴────────────┐
        ▼                         ▼
 Route-assisted            Free-space
 Navigation                Navigation
        │                         │
        └────────────┬────────────┘
                     ▼
              Velocity Command
                     │
                     ▼
   SUB-004 Differential Drive Controller
                     │
                     ▼
          SUB-001 Base Control
```

---

# Software Architecture

```text
                  Application
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     Mapping                  Navigation
          │                         │
          ▼                         ▼
   SLAM Toolbox              Task Interface
          │                         │
          ▼                         ▼
   Map Management          Target Resolution
                                    │
                                    ▼
                               Navigation
                                    │
                                    ▼
                    Differential Drive Controller
                                    │
                                    ▼
                            Base Control
```

---

# Layered Architecture

```text
Application Layer
─────────────────────────────────────
Mapping
Navigation

System Layer
─────────────────────────────────────
Task Interface
Map Management
Target Resolution
Navigation

Localization Layer
─────────────────────────────────────
Robot Localization EKF
SLAM Toolbox
AMCL

Control Layer （ros2_control）
─────────────────────────────────────
Differential Drive Controller
Joint State Broadcaster

Hardware Layer
─────────────────────────────────────
Base Control （hardware_interface）
LiDAR
IMU
```

---

# Mapping Pipeline

```text
LiDAR
   │
IMU
   │
Differential Drive Controller
   │
RF2O
   │
Robot Localization
   │
SLAM Toolbox
   │
Map Management
   │
Map Package
```

Map Package：

```text
maps/
└── <map_name>/
    ├── map.pgm
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

Map Package 為 Mapping 與 Navigation 共用之唯一資料來源。

---

# Navigation Pipeline

Navigation 採兩階段架構。

第一階段：

Target Resolution。

第二階段：

Navigation。

```text
Navigation Target
        │
        ▼
Target Resolution
        │
        ▼
Canonical Goal Pose
        │
        ▼
Navigation
```

Navigation 不直接處理：

- Station
- Dock
- Waypoint

Navigation 永遠處理：

```text
Goal Pose
```

---

# Target Resolution

Target Resolution 負責將各種 Navigation Target 解析為 Canonical Goal Pose。

支援：

```text
Navigation Target
├── Station
└── Goal Pose
```

Station：

```text
Station ID
      │
      ▼
Target Resolution
      │
      ▼
Goal Pose
```

Goal Pose：

```text
Goal Pose
      │
      ▼
Goal Pose
```

未來可擴充：

- Dock
- Parking Spot
- Waypoint
- QR Code
- AprilTag

Navigation 不需修改。

---

# Navigation

Navigation 負責：

- Localization
- Planning
- Controller
- Goal Checking
- Obstacle Avoidance

輸入：

```text
Current Pose
Goal Pose
```

輸出：

```text
cmd_vel
```

Navigation 不關心 Goal 來源。

---

# Navigation Strategy

Navigation 自主決定導航策略。

```text
Current Pose
Goal Pose
      │
      ▼
Navigation Strategy
```

可使用：

```text
Route-assisted Navigation
```

或：

```text
Free-space Navigation
```

Navigation Strategy 不受 Navigation Target 限制。

---

# Route-assisted Navigation

若 Route Graph 可提升導航品質，Navigation 可利用：

```text
First Mile
```

```text
On Route
```

```text
Last Mile
```

完成導航。

流程：

```text
Current Pose
      │
First Mile
      │
Route Graph
      │
Last Mile
      │
Goal Pose
```

---

# Free-space Navigation

若 Route Graph 不適用：

```text
Current Pose
      │
Planner
      │
Goal Pose
```

直接完成導航。

---

# Localization Architecture

```text
Wheel Odometry
（Differential Drive Controller）
        │
RF2O Odometry
        │
IMU
        │
Robot Localization EKF
        │
        ▼
      /odom
```

Navigation 使用：

AMCL：

```text
/map
```

以及：

```text
map → odom
```

完成地圖定位。

---

# Perception Architecture

```text
Front-Left LiDAR
Back-Right LiDAR
        │
        ▼
Original LaserScan
        │
        ▼
Navigation
SLAM
Localization
```

設計原則：

- 能使用原始 LaserScan 即使用原始資料。
- 不得已才導入 LaserScan Fusion。
- 優先採用下游原生支援能力。

---

# ros2_control Architecture

底盤控制採 ros2_control 框架，硬體層與控制層分離。

```text
                /cmd_vel
                    │
                    ▼
        ┌───────────────────────┐
        │  controller_manager   │
        │  ┌─────────────────┐  │
        │  │ diff_drive_     │  │ ── /wheel_odom
        │  │ controller      │  │
        │  ├─────────────────┤  │
        │  │ joint_state_    │  │ ── /joint_states
        │  │ broadcaster     │  │
        │  └────────┬────────┘  │
        │  read()   │  write()  │
        │           ▼           │
        │  SUB-001 Base Control │
        │  (hardware_interface) │
        └───────────┬───────────┘
                    ▼
              RS-485 / M1 Drivers
```

責任劃分：

| 層 | 元件 | 職責 |
|---|---|---|
| Controller | `diff_drive_controller` | 差速運動學、里程積分、速度限制 |
| Broadcaster | `joint_state_broadcaster` | 發布 `/joint_states` |
| Hardware | SUB-001 Base Control | M1 協議、驅動器生命週期、編碼器解碼 |

設計原則：

- 自訂程式碼僅限硬體層之 M1 專屬協議，控制層全數採用既有元件。
- Vehicle Geometry 集中於 `diff_drive_controller`，不於多處重複宣告。
- `diff_drive_controller` 不發布 TF；`odom → base_footprint` 由
  SUB-006 Robot Localization EKF 單一發布。
- ros2_control 需要 URDF 之 `<ros2_control>` 描述，
  URDF 為硬體介面與 joint 定義之來源。

---

# Software Components

```text
SUB-001 Base Control

SUB-002 LiDAR Perception

SUB-003 IMU Perception

SUB-004 Differential Drive Controller

SUB-005 RF2O Odometry

SUB-006 Robot Localization EKF

SUB-007 SLAM Toolbox

SUB-008 Map Management

SUB-009 Task Interface

SUB-010 Target Resolution

SUB-011 Navigation

SUB-012 Robot Description
```

各 Subsystem 維持單一職責。

---

# Design Principles

Architecture 遵循：

- ROS 2 Jazzy
- ros2_control
- Nav2
- SLAM Toolbox
- Robot Localization
- Nav2 Route

以及：

- Hardware First
- Mature Solution First
- Single Source of Truth
- Keep Custom Code Minimal

---

# Core Architecture

本專案核心架構如下：

```text
Navigation Target
        │
        ▼
Target Resolution
        │
        ▼
Canonical Goal Pose
        │
        ▼
Navigation
        │
        ▼
Navigation Strategy
        │
 ┌──────┴────────┐
 ▼               ▼
Route-assisted  Free-space
        │
        ▼
    cmd_vel
        │
        ▼
   ros2_control
```

其中：

- Target Resolution 決定目標。
- Navigation 負責導航。
- Navigation Strategy 決定是否利用 Route Graph。

三者彼此解耦。

此架構作為 `mobile_base` v0.1 後續擴充之基礎。