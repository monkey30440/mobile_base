# System Architecture

本文件定義 `mobile_base` 的系統層級架構，包括：

- 系統邊界
- 架構分解
- 子系統責任配置
- 子系統間主要關係
- 建圖與導航的主要執行路徑
- 系統共用資料與座標架構
- 主要架構決策與約束

本文件描述系統「如何被分解與協作」。

不描述各子系統內部實作、ROS Topic / Service / Action 詳細介面、
套件參數、Driver Protocol、演算法參數或驗證程序。


# 1. Architecture Drivers

說明架構由哪些既定系統需求驅動。

重點整理為：

- 支援 Mapping 與 Navigation 兩個主要系統能力
- 支援 Station ID 與 Goal Pose 作為 Navigation Target
- 使用二維 Occupancy Grid
- 提供一致且唯一的 TF ownership
- 支援 Wheel / LiDAR / IMU 里程資訊整合
- Navigation 支援一般自由空間導航與 Route-assisted Navigation
- 優先整合成熟 ROS 2 / Nav2 元件
- 自訂程式碼限制在專案特有功能
- 系統資料與設定應維持 Single Source of Truth

本章只說「哪些需求影響架構」，
不要重新複製 03_requirements.md。


# 2. System Context

定義 mobile_base 的系統邊界。

建議畫一張 Context Diagram：

                    User / Upper Layer
                           │
                           ▼
                    ┌─────────────┐
                    │ mobile_base │
                    └─────────────┘
                      ▲    ▲    │
                      │    │    ▼
                    LiDAR IMU  Drive Hardware
                      │
                      └──── Environment

說明：

- User / Upper Layer 提供 Mapping / Navigation 操作與 Navigation Target
- mobile_base 負責感知、里程、定位、建圖、導航與底盤運動
- LiDAR / IMU / Drive Hardware 屬於外部實體裝置
- Environment 為 Mapping / Localization / Navigation 的實體環境


# 3. System Decomposition

## 3.1 Functional Decomposition

先以功能責任分解，而不是直接從 ROS package 開始。

建議分為：

- Task / Navigation Interface
- Mapping
- Navigation
- Localization / Odometry
- Perception
- Motion Control
- Hardware Interface
- Shared Robot Description / Map Resources

畫高階 decomposition：

                 Task / Navigation Interface
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
           Mapping                  Navigation
              │                         │
              └──────────┬──────────────┘
                         ▼
              Localization / Odometry
                         ▲
                         │
                    Perception
                         │
                         ▼
                  Motion Control
                         │
                         ▼
                 Hardware Interface

Shared Resources:
- Robot Description
- Map Package


## 3.2 Subsystem Decomposition

正式定義系統採用的 subsystem：

| ID | Subsystem | Architectural Responsibility |
|---|---|---|
| SUB-001 | Drive Hardware Interface | 隔離底盤驅動硬體與通訊細節 |
| SUB-002 | LiDAR Perception | 提供標準化 LiDAR 感知資料 |
| SUB-003 | IMU Perception | 提供標準化 IMU 感知資料 |
| SUB-004 | Differential Drive Controller | 負責差速運動控制與 Wheel Odometry |
| SUB-005 | RF2O Odometry | 提供 LiDAR-based relative odometry |
| SUB-006 | Robot Localization EKF | 融合里程與慣性感測資訊，提供系統 odometry |
| SUB-007 | SLAM Toolbox | 負責 Mapping 與建圖期間 map frame 建立 |
| SUB-008 | Map Management | 管理 Map Package 與地圖資源 |
| SUB-009 | Task Interface | 接收 Navigation Target 並提供導航執行介面 |
| SUB-010 | Target Resolution | 將 Navigation Target 解析為 Canonical Goal |
| SUB-011 | Navigation | 執行 Localization、Planning、Control 與 Navigation Strategy |
| SUB-012 | Robot Description | 提供機器人幾何、固定座標與描述資源 |

此處每個 subsystem 僅給一行 architectural responsibility。

不要放：
- Topic
- Service
- Action
- ROS parameter
- package structure
- class
- protocol
- verification


# 4. Architecture Overview

用一張圖表達主要 subsystem relationship。

建議：

                           User
                            │
                            ▼
                    SUB-009 Task Interface
                            │
                            ▼
                  SUB-010 Target Resolution
                            │
                     Canonical Goal
                            │
                            ▼
                    SUB-011 Navigation
                            │
                            ▼
                         cmd_vel
                            │
                            ▼
              SUB-004 Differential Drive
                            │
                            ▼
                 SUB-001 Drive Hardware
                            │
                            ▼
                       Drive Hardware


       LiDAR                           IMU
         │                              │
         ▼                              ▼
     SUB-002                        SUB-003
         │                              │
         ├──────────► SUB-005 ◄─────────┘
         │              │
         │              ▼
         └────────► SUB-006 ◄──── SUB-004
                        │
                       odom
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
           SUB-007             SUB-011
            SLAM              Navigation
              │
              ▼
           SUB-008
        Map Management


SUB-012 Robot Description
provides shared robot geometry / static frame information
to the system.

圖只表達重要 dependency / data relationship。
不要企圖把所有 ROS Topic 都畫進去。


# 5. Requirement Allocation

建立 system requirement → architectural responsibility 的配置。

格式：

| Requirement | Primary Subsystem | Supporting Subsystem |
|---|---|---|
| SYS-xxx | SUB-xxx | SUB-xxx |
| ... | ... | ... |

原則：

- Primary 表示 requirement 的主要 owner
- Supporting 表示提供資料或能力但不 owns requirement
- 每個 SYS requirement 至少要能找到 architectural owner
- 若 requirement 無法合理 allocation，代表 subsystem decomposition 仍有缺口
- 若同一 requirement 有多個 Primary owner，應重新檢查 responsibility boundary

本章是 03_requirements.md 與 architecture decomposition 之間的主要 traceability bridge。


# 6. Operational Architecture

只描述系統主要 end-to-end flow。

不要描述 subsystem internal implementation。


## 6.1 Mapping Mode

描述：

User
  ↓
Manual Motion
  ↓
Motion Control
  ↓
Robot Motion

LiDAR + Odometry
  ↓
SLAM
  ↓
Occupancy Grid
  ↓
Map Management
  ↓
Map Package

重點：

- Mapping 如何取得 perception / odometry
- 誰建立 map
- 誰保存 map
- Mapping mode 下 map frame ownership


## 6.2 Navigation Mode

描述：

Navigation Target
      ↓
Task Interface
      ↓
Target Resolution
      ↓
Canonical Goal Pose
      ↓
Navigation
      ↓
Motion Command
      ↓
Motion Control
      ↓
Drive Hardware

Navigation 同時使用：

- Loaded Map
- Localization
- LiDAR perception
- Robot geometry


## 6.3 Localization / Odometry Flow

描述：

Wheel Feedback
      ↓
Wheel Odometry ──┐
                 │
LiDAR → RF2O ────┼──→ Localization EKF
                 │
IMU ─────────────┘
                        ↓
                  System Odometry

只描述 responsibility 與 data flow。

不要描述：
- covariance
- filter parameter
- topic name
- RF2O parameter


## 6.4 Motion Control Flow

描述：

Navigation / Manual Command
          ↓
    Motion Controller
          ↓
     Wheel Commands
          ↓
   Hardware Interface
          ↓
      Drive Hardware

feedback:

Drive Hardware
      ↓
Hardware Interface
      ↓
Wheel State
      ↓
Motion Controller / Odometry


# 7. Navigation Architecture

Navigation 是系統中足夠重要且具有多階段 responsibility boundary 的功能，
因此獨立說明其 system-level architecture。


## 7.1 Navigation Target Model

定義：

Navigation Target
├── Station ID
└── Goal Pose

兩種輸入最後統一為：

Canonical Goal Pose

核心原則：

Navigation Execution 不需要知道原始 target type。


## 7.2 Target Resolution

描述 architectural transformation：

Station ID
    ↓
Target Resolution
    ↓
Canonical Goal Pose

Goal Pose
    ↓
Canonical Goal Pose

只說責任與資料轉換。

不要描述：
- YAML schema
- ROS interface
- class
- parser implementation


## 7.3 Navigation Execution

Navigation consumes：

- Canonical Goal Pose
- Current Localization
- Map
- Perception
- Robot Geometry

Navigation produces：

- Motion Command
- Feedback
- Result


## 7.4 Navigation Strategy

Navigation 支援：

Canonical Goal Pose
        │
        ▼
Navigation Strategy
    ┌───┴────┐
    ▼        ▼
Route-     Free-space
assisted   Navigation
    │        │
    └───┬────┘
        ▼
Navigation Execution

說明：

- Goal 與 Route Graph 是不同概念
- Goal 定義最終目的地
- Route Graph 定義導航過程可利用的路網
- Route-assisted 是 navigation strategy，不改變 Canonical Goal
- 無適用 route 時仍可使用 free-space navigation

不要在 04 展開：
- BT node
- Planner plugin
- Controller plugin
- Route Server parameter
- Route search implementation


# 8. Shared Architectural Data

只描述跨 subsystem 共用且會影響 architecture consistency 的資料。


## 8.1 Map Package

定義 Map Package 是：

- Occupancy Grid
- Route Graph
- Station Mapping

的場域級資源集合。

概念結構：

maps/<map_name>/
├── map
├── route_graph
└── station_mapping

04 只定義「它們屬於同一 Map Package」這個 architectural contract。

實際：
- filename
- format
- schema
- load/save mechanism

留給 subsystem / implementation design。


## 8.2 Robot Description

說明 Robot Description 為以下資訊的 single source of truth：

- Robot geometry
- Sensor mounting pose
- Joint relationship
- Static coordinate relationship
- Robot footprint related geometry

不要在此展開 URDF/xacro implementation。


# 9. Coordinate Frame Architecture

這是 system-level contract，應留在 04。

定義核心 frame：

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
 ├── LiDAR frames
 └── IMU frame

並定義 ownership：

| Transform | Architectural Owner |
|---|---|
| map → odom | Mapping 或 Navigation Localization，依 operating mode |
| odom → base_footprint | System Localization |
| base_footprint → base_link | Robot Description |
| base_link → sensor frames | Robot Description |

核心原則：

- 每個 dynamic transform 同時間只能有一個 owner
- Mapping / Navigation mode 不得同時產生衝突的 map → odom
- static transform 由 Robot Description 統一管理

不要放：
- publish rate
- covariance
- node parameter


# 10. Architectural Decisions and Constraints

只保留真正跨 subsystem、會影響整體系統的 decision。


## 10.1 Mature Solution First

優先使用成熟 ROS 2 / Nav2 元件，
僅在現有元件無法滿足系統需求時增加自訂實作。


## 10.2 Minimal Custom Code

自訂程式碼集中於：

- Hardware-specific integration
- Project-specific target resolution
- Project-specific resource management

不重複實作成熟 middleware / navigation functionality。


## 10.3 Single Source of Truth

系統級資料應只有一個 authoritative owner，例如：

- Robot geometry
- Vehicle geometry parameters
- TF ownership
- Map Package resources
- Navigation goal representation


## 10.4 Standard Interface First

Subsystem boundary 優先採 ROS 2 標準資料模型與成熟 framework interface。

避免因專案方便建立與既有 ecosystem 重複的 interface。


## 10.5 Separation of Responsibility

Architecture 應維持：

Perception
≠ Odometry
≠ Localization
≠ Mapping
≠ Navigation
≠ Motion Control
≠ Hardware Interface

各 subsystem 可以互相依賴資料，
但不應重複擁有相同 system responsibility。


# 11. Architecture Boundaries

最後明確說明 04 不負責什麼。

以下內容不屬於 System Architecture：

- ROS Topic / Service / Action 詳細定義
- Package / Node / Class 結構
- Driver Protocol
- Register 定義
- Algorithm parameter
- Nav2 plugin configuration
- Behavior Tree implementation
- ros2_control internal implementation
- Map / Route / Station file schema
- Subsystem verification procedure
- Hardware bring-up procedure

上述內容應在後續 subsystem design 或 implementation documentation 中定義。