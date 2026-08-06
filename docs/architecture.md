# System Architecture

本文件定義 `mobile_base` 系統之整體軟體架構、ROS 2 節點組成、資料流與子系統關係，作為後續實作、測試與維護之依據。

---

# Architecture Principles

系統採用 ROS 2 Jazzy 與成熟開源套件建構。

設計原則如下：

- 優先採用成熟 ROS 2 套件。
- 最小化自訂程式。
- 子系統單一職責。
- 標準 ROS 2 Interface。
- 可重複驗證與測試。
- 支援後續功能擴充。

---

# System Overview

```text
                 User
                  │
                  ▼
          Task Interface
                  │
         ┌────────┴─────────┐
         ▼                  ▼
 Station Navigation     Pose Navigation
         │                  │
         └────────┬─────────┘
                  ▼
          SUB-011 Navigation
                  │
      ┌───────────┼────────────┐
      ▼           ▼            ▼
   Localization  Planning  Controller
                  │
                  ▼
              /cmd_vel
                  │
                  ▼
          Base Controller
```

---

# Software Architecture

```text
                   User
                     │
                     ▼
             SUB-009 Task Interface
                     │
      ┌──────────────┴──────────────┐
      ▼                             ▼
 UC-002 Station ID             UC-003 Goal Pose
      │                             │
      ▼                             │
SUB-010 Route Graph                 │
      │                             │
      └──────────────┬──────────────┘
                     ▼
            SUB-011 Navigation
                     │
     ┌───────────────┼────────────────┐
     ▼               ▼                ▼
  AMCL         Planner Server   Controller Server
                     │
                     ▼
                 /cmd_vel
                     │
                     ▼
            SUB-001 Base Control
```

---

# Mapping Architecture

UC-001 建圖流程：

```text
LiDAR
   │
   ▼
RF2O
   │
Wheel Odom
   │
IMU
   │
   ▼
Robot Localization EKF
   │
   ▼
/odom
   │
   ▼
SLAM Toolbox
   │
   ├── /map
   └── map → odom
```

Mapping 使用：

- SLAM Toolbox
- Robot Localization
- Wheel Odometry
- RF2O
- LiDAR

---

# Localization Architecture

導航模式使用靜態地圖定位。

```text
Map
 │
 ▼
AMCL
 │
 ├── /map
 ├── /scan_front
 ├── /scan_rear
 └── /odom
        │
        ▼
Current Pose
```

Localization 使用：

- AMCL
- Robot Localization EKF

---

# Navigation Architecture

UC-002 與 UC-003 共用同一套 Navigation。

```text
                 Navigation
                      │
      ┌───────────────┴───────────────┐
      ▼                               ▼
 UC-002 Station                 UC-003 Pose
      │                               │
      ▼                               ▼
 Route Graph                    Goal Pose
      │                               │
      └───────────────┬───────────────┘
                      ▼
               BT Navigator
                      │
          Planner / Controller
                      │
                   /cmd_vel
```

UC-002 使用：

- Route Graph
- Route Server

UC-003 使用：

- Goal Pose

共同使用：

- Planner Server
- Controller Server
- Costmaps
- Goal Checker
- Progress Checker

---

# Route Graph Architecture

Route Graph 僅用於 UC-002。

```text
Map Package
      │
      ├── route_graph.geojson
      └── stations.yaml
             │
             ▼
 Route Graph Management
             │
             ▼
     Nav2 Route Server
             │
             ▼
     Navigation
```

---

# Map Package

每個場域以一個 Map Package 管理所有導航資源。

```text
maps/
└── <map_name>/
    ├── map.pgm
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

| File | Purpose |
|------|---------|
| map.pgm | Occupancy Grid |
| map.yaml | Map Metadata |
| route_graph.geojson | Nav2 Route Graph |
| stations.yaml | Station Mapping |

---

# TF Tree

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

TF 發布來源：

| Transform | Publisher |
|-----------|-----------|
| map → odom | SLAM Toolbox（Mapping）/ AMCL（Navigation） |
| odom → base_footprint | Robot Localization EKF |
| base_footprint → base_link | URDF |
| base_link → Sensors | URDF |

---

# Topic Flow

```text
LiDAR
    │
    ▼
/scan_front
/scan_rear
    │
    ▼
RF2O
    │
    ▼
/rf2o_odom

Wheel Driver
    │
    ▼
/wheel_odom

IMU
    │
    ▼
/imu/data_raw

        │
        ▼
Robot Localization
        │
        ▼
      /odom
        │
        ├─────────────┐
        ▼             ▼
SLAM Toolbox       AMCL
        │             │
        ▼             ▼
      /map      Current Pose
                    │
                    ▼
              Navigation
                    │
                    ▼
                /cmd_vel
```

---

# Package Architecture

```text
mobile_base
├── base_driver
├── lidar_driver
├── imu_driver
├── wheel_odometry
├── localization
├── mapping
├── map_management
├── navigation
├── route_graph
└── task_interface
```

Package 名稱於 Implementation 階段最終確認。

---

# Subsystem Relationship

| Subsystem | Responsibility |
|-----------|----------------|
| SUB-001 Base Control | 差速底盤控制 |
| SUB-002 LiDAR Perception | LiDAR 感知 |
| SUB-003 IMU Perception | IMU 感知 |
| SUB-004 Wheel Odometry | Wheel Odometry |
| SUB-005 RF2O Odometry | LiDAR Odometry |
| SUB-006 Robot Localization EKF | Sensor Fusion |
| SUB-007 SLAM Toolbox | Mapping |
| SUB-008 Map Management | Map Package 管理 |
| SUB-009 Task Interface | 任務介面 |
| SUB-010 Route Graph Management | Route Graph 管理 |
| SUB-011 Navigation | Nav2 導航 |

---

# Mature Software Components

初版優先採用成熟 ROS 2 套件：

| Component | Purpose |
|-----------|---------|
| slam_toolbox | Mapping |
| robot_localization | Sensor Fusion |
| rf2o_laser_odometry | LiDAR Odometry |
| nav2_map_server | Map Management |
| nav2_amcl | Localization |
| nav2_route | Route Graph Navigation |
| nav2_planner | Global Planning |
| nav2_controller | Path Following |
| nav2_bt_navigator | Navigation Orchestration |
| nav2_costmap_2d | Obstacle Representation |
| nav2_lifecycle_manager | Lifecycle Management |

專案自訂程式僅包含：

- Base Driver
- Wheel Odometry
- Task Interface
- Route Graph Management（Station Mapping）
- 專案整合與 Launch

---

# Architecture Traceability

| Use Case | Capability | Subsystem |
|-----------|------------|-----------|
| UC-001 | CAP-001 | SUB-001 ~ SUB-008 |
| UC-002 | CAP-002 | SUB-009 ~ SUB-011 |
| UC-003 | CAP-003 | SUB-009、SUB-011 |