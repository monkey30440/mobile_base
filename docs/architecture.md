# System Architecture

本文件定義 `mobile_base` 系統之整體軟體架構、ROS 2 資料流、TF 關係、子系統協作與成熟套件採用方式，作為後續實作、整合測試與維護依據。

---

# Architecture Principles

系統採用 ROS 2 Jazzy 與成熟開源套件建構。

設計原則如下：

- 優先採用成熟 ROS 2 套件。
- 最小化自訂程式。
- 子系統維持單一職責。
- 優先使用標準 ROS 2 Interface。
- 保留原始感測資料。
- 以實機驗證作為初版設計確認依據。
- 支援後續功能擴充。

---

# LiDAR Data Usage Principle

系統優先保留並直接使用 LiDAR 原始資料。

SUB-002 持續發布：

```text
/scan_front
/scan_rear
```

下游子系統依自身介面能力選擇資料使用方式。

```text
/scan_front
/scan_rear
      │
      ▼
下游是否可直接接收所需原始來源？
      │
  ┌───┴───┐
  ▼       ▼
 Yes      No
  │        │
  ▼        ▼
直接使用   單一原始來源是否足夠？
原始資料          │
             ┌────┴────┐
             ▼         ▼
            Yes        No
             │          │
             ▼          ▼
       使用單一原始   評估 LaserScan Fusion
           Topic
```

適用原則：

- 下游可接收多個 LiDAR Topic 時，直接使用 `/scan_front` 與 `/scan_rear`。
- 下游僅需要單一來源且單一原始 Topic 可滿足需求時，使用選定之原始 Topic。
- 僅於下游介面無法直接使用所需原始資料，且單一來源無法滿足功能需求時，才評估 LaserScan Fusion。
- LaserScan Fusion 為依下游需求導入之相容層，不屬於系統預設架構。
- 是否導入融合，以實機驗證結果為準。

---

# Navigation Principle

所有導航任務皆以 AMR 目前位姿作為起點。

使用者僅指定導航目標，系統自動取得 Current Pose。

導航目標分為：

- 路網站點（Station）
- 任意位姿（Pose）

First Mile、On Route 與 Last Mile 屬於 Navigation 執行策略，由系統依目前位姿、目標與 Route Graph 關係決定。

---

# System Overview

```text
                       User
                        │
                        ▼
                SUB-009 Task Interface
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
   Station Navigation           Pose Navigation
          │                           │
          ▼                           │
SUB-010 Route Graph Management        │
          │                           │
          └─────────────┬─────────────┘
                        ▼
                SUB-011 Navigation
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     Localization    Planning      Controller
                        │
                        ▼
                    /cmd_vel
                        │
                        ▼
               SUB-001 Base Control
```

---

# Software Architecture

```text
                           User
                            │
                            ▼
                    Task Interface
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
          Station ID                  Goal Pose
              │                           │
              ▼                           │
      Route Graph Management              │
              │                           │
              └─────────────┬─────────────┘
                            ▼
                        Navigation
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
        AMCL          Planner Server   Controller Server
                            │
                            ▼
                        /cmd_vel
                            │
                            ▼
                       Base Control
```

---

# Mapping Architecture

UC-001 使用 SLAM Toolbox 建立二維 Occupancy Grid。

```text
/scan_front 或 /scan_rear
            │
            ▼
     RF2O Odometry
            │
            │
      /wheel_odom
            │
            │
     /imu/data_raw
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
      ┌─────┴─────┐
      ▼           ▼
    /map     map → odom
      │
      ▼
 Map Management
```

Mapping 使用：

- SUB-002 LiDAR Perception
- SUB-003 IMU Perception
- SUB-004 Wheel Odometry
- SUB-005 RF2O Odometry
- SUB-006 Robot Localization EKF
- SUB-007 SLAM Toolbox
- SUB-008 Map Management

SLAM Toolbox 使用原始 LiDAR Topic。

正式 Scan Source 依下列順序確認：

1. 確認套件可接受之輸入形式。
2. 優先使用原始 LiDAR Topic。
3. 單一原始來源可完成建圖時維持不融合。
4. 僅於原始來源無法滿足需求時評估 LaserScan Fusion。

---

# Localization Architecture

導航模式使用靜態 Occupancy Grid 與 AMCL 提供地圖定位。

```text
 Map Package
      │
      ▼
   Map Server
      │
      ▼
     /map
      │
      │
原始 LiDAR Topic
      │
      ▼
     AMCL
      │
      ▼
 map → odom
```

系統里程由 Robot Localization EKF 提供：

```text
/wheel_odom
/rf2o_odom
/imu/data_raw
      │
      ▼
Robot Localization EKF
      │
      ├── /odom
      └── odom → base_footprint
```

導航定位使用：

- Map Server
- AMCL
- Robot Localization EKF
- URDF TF

AMCL 使用原始 LiDAR Topic。正式輸入依套件介面與實機定位結果決定。

---

# Navigation Architecture

UC-002 與 UC-003 共用 SUB-011 Navigation。

```text
                    Navigation
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
 UC-002 Station Navigation      UC-003 Pose Navigation
          │                             │
          ▼                             ▼
    Route Node                       Goal Pose
          │                             │
          └──────────────┬──────────────┘
                         ▼
                    BT Navigator
                         │
              Planner / Controller
                         │
                      /cmd_vel
```

共同使用：

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

# Station Navigation Architecture

UC-002 以 Station ID 作為導航目標。

```text
Station ID
    │
    ▼
stations.yaml
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
    │
    ▼
/cmd_vel
```

First Mile 由目前位姿銜接 Route Graph。

On Route 由 Nav2 Route Server 計算並追蹤。

目標站點為 Route Graph 上之節點，因此初版以 First Mile 與 On Route 為主要執行區段。

---

# Pose Navigation Architecture

UC-003 直接使用 Goal Pose。

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
/cmd_vel
```

Pose Navigation 不使用：

- Route Graph
- Route Server
- Station Mapping

其餘定位、Costmap、Goal Checker 與控制元件皆與 Station Navigation 共用。

---

# Obstacle Source Architecture

Nav2 Costmap 優先直接使用原始 LiDAR Topic。

```text
/scan_front ─────┐
                 ├──► Global / Local Costmap
/scan_rear ──────┘
```

若 Costmap Observation Sources 可同時設定兩個 Topic，直接使用前後兩個原始來源。

只有在下列條件成立時才評估融合後 Scan：

- Costmap 或其他下游介面無法直接接收所需來源。
- 單一原始 LiDAR 無法滿足障礙物覆蓋需求。
- 實機驗證確認融合具必要性。

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
SUB-010 Route Graph Management
              │
      ┌───────┴────────┐
      ▼                ▼
Route Graph       Station Mapping
      │                │
      └───────┬────────┘
              ▼
      Nav2 Route Server
              │
              ▼
       SUB-011 Navigation
```

Route Graph 拓樸、Edge Cost、Route Search 與 Route Tracking 優先採用 `nav2_route`。

專案自訂內容限於 Station ID 與 Route Node ID 的映射。

---

# Map Package

每個場域以一個 Map Package 管理地圖與導航資源。

```text
maps/
└── <map_name>/
    ├── map.pgm
    ├── map.yaml
    ├── route_graph.geojson
    └── stations.yaml
```

| File | Purpose |
|---|---|
| `map.pgm` | Occupancy Grid 地圖影像 |
| `map.yaml` | Occupancy Grid 地圖設定 |
| `route_graph.geojson` | Nav2 Route Graph |
| `stations.yaml` | Station ID 與 Route Node ID 映射 |

Map Package 由 SUB-008 Map Management 管理。

UC-001 產生：

```text
map.pgm
map.yaml
```

UC-002 建立：

```text
route_graph.geojson
stations.yaml
```

---

# Sensor and Odometry Architecture

```text
Front LiDAR ──► /scan_front
Rear LiDAR  ──► /scan_rear

Selected Raw Scan
        │
        ▼
      RF2O
        │
        ▼
  /rf2o_odom

Base Control
        │
        ▼
 /wheel_states
        │
        ▼
Wheel Odometry
        │
        ▼
 /wheel_odom

IMU
        │
        ▼
/imu/data_raw

/wheel_odom
/rf2o_odom
/imu/data_raw
        │
        ▼
Robot Localization EKF
        │
        ├── /odom
        └── odom → base_footprint
```

各感測來源維持獨立輸出，由 Robot Localization 執行里程融合。

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

| Transform | Publisher |
|---|---|
| `map → odom` | SLAM Toolbox（Mapping）或 AMCL（Navigation） |
| `odom → base_footprint` | Robot Localization EKF |
| `base_footprint → base_link` | URDF |
| `base_link → imu_link` | URDF |
| `base_link → front_laser_frame` | URDF |
| `base_link → rear_laser_frame` | URDF |

Mapping 與 Navigation 模式不應同時由 SLAM Toolbox 與 AMCL 發布 `map → odom`。

---

# Topic Flow

```text
                      /scan_front
Front LiDAR ──────────────┐
                          │
                      /scan_rear
Rear LiDAR ───────────────┤
                          │
                          ├──► RF2O / SLAM / AMCL / Costmaps
                          │
                          ▼
                    Downstream Consumer

Base Control
    │
    ▼
/wheel_states
    │
    ▼
Wheel Odometry
    │
    ▼
/wheel_odom

IMU
    │
    ▼
/imu/data_raw

RF2O
    │
    ▼
/rf2o_odom

/wheel_odom
/rf2o_odom
/imu/data_raw
    │
    ▼
Robot Localization EKF
    │
    ▼
  /odom
    │
    ├───────────────┐
    ▼               ▼
SLAM Toolbox       AMCL
    │               │
    ▼               ▼
  /map         Current Pose
                    │
                    ▼
               Navigation
                    │
                    ▼
                /cmd_vel
                    │
                    ▼
               Base Control
```

---

# ROS Topic Baseline

| Topic | Publisher | Primary Consumers |
|---|---|---|
| `/cmd_vel` | Navigation 或 Teleop | Base Control |
| `/wheel_states` | Base Control | Wheel Odometry |
| `/scan_front` | Front LiDAR Driver | RF2O、SLAM、AMCL、Costmap |
| `/scan_rear` | Rear LiDAR Driver | RF2O、SLAM、AMCL、Costmap |
| `/imu/data_raw` | IMU Driver | Robot Localization |
| `/wheel_odom` | Wheel Odometry | Robot Localization |
| `/rf2o_odom` | RF2O Odometry | Robot Localization |
| `/odom` | Robot Localization EKF | SLAM Toolbox、AMCL、Navigation |
| `/map` | SLAM Toolbox 或 Map Server | AMCL、Navigation |

---

# Deployment Architecture

所有 ROS 2 功能部署於 Jetson AGX Orin Developer Kit。

```text
Jetson AGX Orin
├── Base Control
├── LiDAR Drivers
├── IMU Driver
├── Wheel Odometry
├── RF2O
├── Robot Localization
├── SLAM Toolbox
├── Map Server
├── AMCL
├── Route Server
├── Nav2
├── Task Interface
└── Diagnostics
```

初版使用 Docker Compose 管理系統部署。

---

# Package Architecture

```text
mobile_base
├── base_control
├── lidar_perception
├── imu_perception
├── wheel_odometry
├── rf2o_odometry
├── localization
├── mapping
├── map_management
├── task_interface
├── route_graph_management
└── navigation
```

Package 名稱與實際合併方式於 Implementation 階段確認。

成熟套件以依賴與 Launch 整合為主，不為每個成熟套件重建包裝實作。

---

# Subsystem Relationship

| Subsystem | Responsibility |
|---|---|
| SUB-001 Base Control | 差速底盤控制與輪速回授 |
| SUB-002 LiDAR Perception | 發布前後原始 LaserScan |
| SUB-003 IMU Perception | 發布原始 IMU 量測 |
| SUB-004 Wheel Odometry | 建立輪式里程 |
| SUB-005 RF2O Odometry | 建立雷射里程 |
| SUB-006 Robot Localization EKF | 融合系統里程並發布 TF |
| SUB-007 SLAM Toolbox | 建立二維 Occupancy Grid |
| SUB-008 Map Management | 管理 Map Package |
| SUB-009 Task Interface | 接收 Station 與 Pose 導航任務 |
| SUB-010 Route Graph Management | 管理 Route Graph 與 Station Mapping |
| SUB-011 Navigation | 執行 Station 與 Pose Navigation |

---

# Mature Software Components

初版優先採用成熟 ROS 2 套件。

| Component | Purpose |
|---|---|
| SICK ROS Driver | LiDAR 通訊與 LaserScan 發布 |
| Existing TDK IMU Driver | IMU 通訊與訊息發布 |
| `rf2o_laser_odometry` | LiDAR Odometry |
| `robot_localization` | Sensor Fusion |
| `slam_toolbox` | Mapping |
| `nav2_map_server` | Map Loading |
| `nav2_amcl` | Static Map Localization |
| `nav2_route` | Route Graph Navigation |
| `nav2_planner` | Global Path Planning |
| `nav2_controller` | Path Following |
| `nav2_bt_navigator` | Navigation Orchestration |
| `nav2_costmap_2d` | Obstacle Representation |
| `nav2_lifecycle_manager` | Lifecycle Management |

專案自訂程式限於：

- Base Driver 與硬體整合。
- Wheel Odometry。
- Task Interface。
- Station Mapping。
- Map Package 路徑整合。
- Launch、Parameters 與 Diagnostics。

---

# Architecture Traceability

| Use Case | Capability | Main Subsystems |
|---|---|---|
| UC-001 建圖任務 | CAP-001 | SUB-001～SUB-008 |
| UC-002 路網站點移動任務 | CAP-002 | SUB-001～SUB-006、SUB-008～SUB-011 |
| UC-003 任意 Pose 移動任務 | CAP-003 | SUB-001～SUB-006、SUB-008、SUB-009、SUB-011 |