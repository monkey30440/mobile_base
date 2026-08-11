# System Architecture

# 1. Purpose, Scope and Authority

本文件定義 `mobile_base` v0.1 的系統層級架構。

本文件負責定義：

- system boundary；
- system decomposition；
- requirement 至 subsystem responsibility allocation；
- cross-subsystem relationships；
- Mapping、Navigation、Localization / Odometry 與 Motion Control 的主要 operational flows；
- system-wide data、coordinate frame、ownership、lifecycle、fault 與 safety contracts；
- 影響多個 subsystem 的 architecture decisions and constraints。

本文件描述系統如何被分解，以及各 subsystem 如何協作以滿足已核准需求。

## 1.1 Normative Inputs

本架構僅以下列文件作為 normative input：

- `01_use_cases.md`
- `02_capabilities.md`
- `03_requirements.md`

本文件不得新增上述文件未定義的使用者功能、系統能力或系統需求。

Architecture 可以配置責任、選擇成熟技術並定義 subsystem contract，但不得以 architecture decision 取代缺失的上游需求。

## 1.2 Downstream Documents

`05_subsystem.md` 為本架構的下游文件，用於定義各 subsystem 的 boundary、interface、internal design、configuration 與 verification。

`05_subsystem.md` 不得反向重新定義本文件的：

- subsystem responsibility；
- primary ownership；
- cross-subsystem relationship；
- system-wide contract；
- operational flow。

Subsystem detailed design baselines 必須符合本架構，但其 internal design 不複製至本文件。

## 1.3 Architecture Boundaries

以下內容不屬於本文件：

- 單一 subsystem 的 internal component decomposition；
- package、node、class 或 source-file structure；
- ROS Topic、Service、Action 的詳細名稱與 message contract；
- driver protocol、function code、register、frame encoding；
- algorithm、plugin、Behavior Tree 或 recovery implementation；
- ROS parameter 與硬體參數數值；
- Map、Route Graph、Station 等檔案名稱、格式與 schema；
- subsystem test case、verification procedure 或 hardware bring-up procedure；
- future-only capability 或未納入 v0.1 的 extension。

上述內容應由 `05_subsystem.md`、詳細設計 baseline、implementation plan、configuration 或 verification evidence 負責。

# 2. Architecture Drivers

`mobile_base` v0.1 架構由下列已核准需求群組驅動。

| ID | Architecture Driver | Derived Requirements | Architectural Consequence |
|---|---|---|---|
| AD-001 | Reusable Mapping | SYS-001、SYS-002、SYS-006、SYS-007、SYS-024 | 系統必須分離地圖建立與 Map Package 管理，並提供建圖成功／失敗邊界。 |
| AD-002 | Canonical Navigation Target | SYS-008、SYS-009 | Station ID 與 Goal Pose 必須在進入導航執行前被驗證並正規化為單一 canonical goal。 |
| AD-003 | Autonomous Navigation Execution | SYS-010、SYS-011、SYS-014、SYS-015、SYS-016、SYS-017、SYS-025 | 導航必須具有定位、規劃、避障、追蹤、到站判定、取消與結果回報的清楚責任邊界。 |
| AD-004 | Shared Perception and State Estimation | SYS-003、SYS-004、SYS-005、SYS-010、SYS-029 | LiDAR、IMU、wheel feedback、odometry 與 map localization 必須形成一致的狀態估測資料流，並提供有效性狀態。 |
| AD-005 | Closed-loop Differential-drive Motion | SYS-022、SYS-027、SYS-028、SYS-029 | Motion Control 與 Drive Hardware Interface 必須分離；前者負責差速運動控制，後者負責硬體命令、量測回授與裝置狀態。 |
| AD-006 | Fault-safe Base Lifecycle | SYS-026、SYS-030、SYS-031 | 底盤啟用、運動、故障、停用與 shutdown 必須形成跨控制與硬體邊界的安全 contract。 |
| AD-007 | Authoritative Robot Geometry and Frames | SYS-023 | Robot geometry、joint relationship、sensor mounting 與 static frame relationship 必須具有單一 architectural owner。 |
| AD-008 | Evidence-bound Operational Parameters | SYS-015、SYS-016、SYS-026、SYS-027、SYS-028、SYS-030 | 路徑偏差、到站、停止、timeout 與 operational limit 不得由架構文件虛構；其值必須由下游 configuration、整合與實機驗證確立。 |
| AD-009 | Route-preferred Navigation | SYS-012、SYS-013、SYS-018、SYS-019、SYS-020、SYS-021 | 系統必須分離 Navigation Target、Navigation Resources、strategy selection 與 movement execution；有效且可安全執行的 Route Graph 應優先使用，並以 First Mile、On Route、Last Mile 組成 route-assisted movement。Free-space movement 只可在核准的 fallback eligibility 下使用。 |

本章只整理需求對架構造成的影響，不新增需求內容。

Route Graph、Route-assisted Navigation、First Mile、On Route、Last Mile 與受限的 Free-space Fallback 為 requirement-derived baseline。特定 planner、controller、Behavior Tree、route-search algorithm 或 recovery implementation 仍不是 Architecture Driver，應由下游 detailed design 與驗證決定。

# 3. System Context

`mobile_base` 的 system boundary 包含完成 Mapping、Localization / Odometry、Navigation 與 Motion Control 所需的軟體責任，以及系統所管理的 Map Package 與 Robot Description。

Operator、Navigation Client / Upper Layer、teleoperation tool、實體感測器、Drive Hardware 與 Physical Environment 均位於此 system boundary 之外。

```text
 Operator                         Navigation Client / Upper Layer
    │                                         │
    │ keyboard input                          │ navigation target / cancellation
    ▼                                         ▼
 External Teleoperation Tool ────────► ┌─────────────────────────┐
        manual velocity command       │                         │
                                      │       mobile_base       │
 LiDAR Devices ── measurements ──────►│                         │
 IMU Device ───── measurements ──────►│                         │
                                      └────────────┬────────────┘
        mapping / navigation results,             │ drive command
        status and faults ◄────────────────────────┤ wheel feedback,
                                                   │ device state and faults
                                                   ▼
                                          Drive Hardware

 Physical Environment ── perceived by sensors and affected by robot motion
```

## 3.1 External Actors and Systems

| External Entity | Relationship with `mobile_base` |
|---|---|
| Operator | 操作 external teleoperation tool，並發起或監督 Mapping 工作。 |
| External Teleoperation Tool | 將 Operator 輸入轉換為 Manual Velocity Command；不得直接控制 Drive Hardware。v0.1 的操作工具為 `teleop_twist_keyboard`。 |
| Navigation Client / Upper Layer | 提交 Navigation Target、要求取消導航，並接收 navigation feedback 與 result。 |
| LiDAR Devices | 提供環境量測；不負責地圖建立、定位或避障決策。 |
| IMU Device | 提供慣性量測；不負責 system pose 或 odometry 的最終估測。 |
| Drive Hardware | 接收受控的底盤命令，並回報 wheel measurement、device state 與 fault。 |
| Physical Environment | 被 LiDAR 感測，並受到 AMR 實體運動影響。 |

## 3.2 Boundary Contracts

- External Teleoperation Tool 只提供 Manual Velocity Command；`mobile_base` 負責 command acceptance、operational-limit enforcement、timeout handling、motion execution 與 safe stopping。
- Navigation Client / Upper Layer 提供 Station ID 或 Goal Pose；`mobile_base` 負責驗證、解析並正規化 Navigation Target。
- `mobile_base` 是 Drive Hardware 的唯一軟體控制邊界。外部 client 與 operator tool 不得繞過此邊界直接下達 drive command。
- `mobile_base` 管理 Mapping 所產出的 Map Package，並回報 Mapping 與 Navigation 的成功、失敗或取消結果。
- `mobile_base` 必須將 sensor validity、localization validity、drive state 與 fault 納入跨 subsystem 的 operational decision。

本章只定義 system boundary 與外部交換資訊；實際的 subsystem responsibility allocation 於後續章節定義。

# 4. System Decomposition and Responsibility Allocation

本章依據 `01–03` 將 system responsibility 配置至 subsystem。Subsystem identifier 待 decomposition 全部確認後統一編定。

## 4.1 Drive Hardware Interface

Drive Hardware Interface 是 `mobile_base` 與實體 Drive Hardware 之間的唯一 software owner。其 architectural boundary 起於左右輪命令，止於實體驅動器的 command、measurement、device state 與 fault exchange。

### Responsibilities

- 接收左右輪命令，並轉換為 Drive Hardware 可執行的命令。
- 驗證必要的硬體配置與 hardware-related operational limits。
- 限制輪端命令及其對應的馬達輸出。
- 管理 Drive Hardware 的 enable、disable 與 shutdown lifecycle。
- 從有效的馬達回授提供左右輪位置與速度狀態。
- 偵測通訊失敗、驅動器警報，以及無效或缺失的回授。
- 提供 drive readiness、device state、feedback validity 與 fault information。
- 發生故障、停用或 shutdown 時，嘗試停止並安全停用 Drive Hardware。
- 獨占實體 Drive Hardware 的 software control；其他 subsystem 或 external entity 不得繞過此邊界直接控制驅動器。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-026 | Shared：負責偵測 hardware fault、停止接受持續輸出、嘗試停止並回報 fault。 |
| SYS-028 | Shared：負責 wheel command 與 motor output 的最終 operational-limit enforcement。 |
| SYS-029 | Primary owner：提供由有效 Drive Hardware feedback 所取得的 wheel position 與 velocity。 |
| SYS-030 | Primary owner：負責 Drive Hardware 的安全 enable、stop、disable 與 shutdown sequence。 |
| SYS-031 | Primary owner：負責 hardware-related configuration validation。 |

### Cross-subsystem Relationships

```text
Motion Control
    │ wheel command
    │ lifecycle intent
    ▼
Drive Hardware Interface
    │
    ├──► Drive Hardware: drive command
    ◄──── Drive Hardware: motor feedback / device state / fault
    │
    └──► Motion Control and system-wide fault handling:
         measured wheel state / readiness / validity / fault
```

Drive Hardware Interface 必須符合已核准的 M1 hardware 與 driver detailed design baselines；其 internal component、protocol、register、transport、conversion formula 與 timeout value 不在本文件定義。

### Excluded Responsibilities

Drive Hardware Interface 不負責：

- 接收 Manual Velocity Command 或 Navigation 所產生的 vehicle velocity command；
- differential-drive kinematics；
- vehicle odometry estimation；
- `odom → base_footprint` ownership；
- navigation stop、path tracking、arrival determination 或 recovery policy；
- robot geometry ownership。

Vehicle velocity command 必須先經 Motion Control 轉換為 wheel command，才能進入 Drive Hardware Interface。SYS-027 的 vehicle command freshness 與 timeout detection 由 Motion Control 主要負責；Drive Hardware Interface 仍須提供獨立的 hardware safety boundary，避免上游失效後持續輸出。

## 4.2 Motion Control

Motion Control 是 vehicle velocity command 與左右輪命令之間的唯一轉換邊界，並根據有效的 measured wheel state 產生 wheel odometry。建圖期間，外部 `teleop_twist_keyboard` 經 Manual Velocity Command 進入此邊界；導航期間則由 Navigation 提供 vehicle velocity command。

### Responsibilities

- 接收目前被授權來源所提供的 vehicle velocity command。
- 依 differential-drive kinematics 產生左右輪命令。
- 在 vehicle command 與 wheel command 層套用速度及加速度限制。
- 監控有效 vehicle velocity command 的 freshness。
- 在 command timeout、command source 失效或 Drive Hardware 不可用時輸出停止命令。
- 僅在 Drive Hardware Interface 回報 ready、無 fault 且 feedback valid 時允許非零輸出。
- 使用實際的左右輪位置與速度推算 wheel odometry。
- 提供底盤 stopped / moving motion state，供其他 subsystem 進行 operational decision。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-005 | Supporting owner：提供 wheel odometry；不擁有 system-level fused planar odometry。 |
| SYS-022 | Primary owner：接收 vehicle velocity command 並執行 differential-drive kinematics。 |
| SYS-026 | Shared：收到 hardware fault 或 invalid feedback 後停止持續運動輸出。 |
| SYS-027 | Primary owner：監控 vehicle velocity command freshness 並處理 timeout。 |
| SYS-028 | Shared：負責 vehicle-level 與 wheel-level motion limits；Drive Hardware Interface 負責 motor output 的最終限制。 |
| SYS-029 | Consumer：只使用有效的 measured wheel state，不得以 command value 取代 measurement。 |
| SYS-030 | Shared：以 Drive Hardware readiness、fault 與 feedback validity 作為非零輸出的必要條件。 |

### Cross-subsystem Relationships

```text
External teleop_twist_keyboard                 Navigation
        │ Manual Velocity Command                  │ vehicle velocity command
        └──────────────────┬───────────────────────┘
                           │ authorized source only
                           ▼
                     Motion Control
                       │         ▲
         wheel command │         │ measured wheel state
                       ▼         │ readiness / validity / fault
                 Drive Hardware Interface
                       │
                       └── wheel odometry ──► State Estimation
```

在任一時間，Motion Control 只接受目前 operational flow 所授權的單一 command source。非授權來源的 command 不得影響 wheel command。Command source selection 的實作方式不在本文件定義。

Wheel odometry 必須由 Drive Hardware Interface 提供的有效 measured wheel state 推算，不得以 command value 取代。State Estimation 使用 wheel odometry 產生 system-level planar odometry，並擁有 `odom → base_footprint`；Motion Control 不發布此 transform。

### Excluded Responsibilities

Motion Control 不負責：

- Navigation path planning、path validity、arrival determination 或 recovery policy；
- 決定 Mapping 或 Navigation operational flow 的啟用與切換；
- Drive Hardware communication、driver alarm interpretation 或 hardware lifecycle；
- motor mapping、direction、gear ratio 或 motor position scaling；
- sensor fusion 與 system-level fused planar odometry；
- `odom → base_footprint` ownership；
- robot geometry ownership；
- controller、ROS interface、topic、message type 或參數值的 detailed design。

## 4.3 State Estimation

State Estimation 是 system-level planar odometry、odometry validity 與 `odom → base_footprint` 的唯一 owner。它維持 `odom` frame 中連續的相對運動估測，不負責在既有地圖中估測全域 pose。

### Responsibilities

- 接收 Motion Control 產生的 wheel odometry。
- 接收有效的 IMU measurement。
- 必要時接收經驗證的 auxiliary odometry。
- 產生一致的 planar position、orientation、linear velocity 與 angular velocity estimate。
- 提供 system planar odometry 給 Mapping、Map Localization 與 Navigation。
- 判斷並提供 odometry validity。
- 獨占 `odom → base_footprint` 的發布權。
- 輸入遺失、逾時或無效時，不得將 stale estimate 宣告為有效。
- 提供 degraded 或 invalid 狀態，使依賴 subsystem 能停止使用無效估測。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-004 | Consumer：使用有效 IMU measurement；measurement 的提供責任屬於 IMU Perception。 |
| SYS-005 | Primary owner：提供可供 Mapping、Map Localization 與 Navigation 使用的 system planar odometry。 |
| SYS-029 | Indirect consumer：透過 Motion Control 使用由有效 Drive Hardware feedback 推算的 wheel odometry。 |

SYS-003 不直接配置給 State Estimation。若 detailed design 採用 LiDAR-derived odometry，它是實現 SYS-005 的 estimation strategy，不改變 LiDAR Perception 對 scan data 的 ownership。

### Cross-subsystem Relationships

```text
Motion Control ── wheel odometry ────────┐
                                         │
IMU Perception ── IMU measurement ───────┼──► State Estimation
                                         │         │
Validated auxiliary odometry ────────────┘         ├── system planar odometry
                                                   ├── odometry validity
                                                   └── odom → base_footprint
```

Coordinate-frame ownership 必須維持：

```text
Mapping or Map Localization   owns map → odom
State Estimation              owns odom → base_footprint
Robot Description             owns base_footprint → base_link
                              and sensor static transforms
```

State Estimation 與 Map Localization 必須保持獨立。State Estimation 維持 `odom` frame 中的相對運動估測；Map Localization 在已載入地圖中提供 `map` frame correction。Map Localization 暫時失效不得造成多重 TF owner，也不得使其他 subsystem 接管 `odom → base_footprint`。

### Auxiliary Odometry Constraint

RF2O 或其他 LiDAR-derived odometry 不構成獨立的 architecture-level subsystem，也不是 SYS-005 的必要條件。只有在 approved estimation design 需要，且 integration evidence 證明其輸入、frame、timing 與品質適合時，才可作為 State Estimation 的 internal source。

本文件不要求固定融合 Wheel Odometry、RF2O Odometry 與 IMU 的特定組合。

### Excluded Responsibilities

State Estimation 不負責：

- LiDAR 或 IMU device communication；
- wheel command、differential-drive control 或 Drive Hardware lifecycle；
- Occupancy Grid 建立或 Map Package 管理；
- 在已載入地圖中估測 global pose；
- `map → odom` ownership；
- navigation planning、control 或 arrival determination；
- RF2O、filter algorithm、filter parameter、covariance 或 ROS interface 的 detailed design；
- robot geometry 或 sensor mounting transform ownership。

## 4.4 LiDAR Perception

LiDAR Perception 是系統所配置之實體 LiDAR devices 的唯一 software owner。它提供各來源獨立且可判斷有效性的 scan measurement，不負責將 scan 解讀為 map、pose 或 navigation obstacle decision。

### Responsibilities

- 管理系統配置的兩具實體 LiDAR。
- 分別取得各 LiDAR 的 scan measurement，並保留來源身分。
- 為每個 scan source 提供 measurement、source identity、acquisition time、coordinate frame、validity 與 device state / fault。
- 確保 scan 所宣告的 frame 與 Robot Description 一致。
- 將有效 scan 提供給 Mapping、Map Localization 與 Navigation。
- 個別裝置失效時明確標示受影響的來源，不得將 stale scan 宣告為有效。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-003 | Primary owner：提供可供 Mapping、Map Localization 與 Navigation 使用的 LiDAR scan。 |
| SYS-006 | Provider：提供 Mapping 更新地圖所需的有效 perception data。 |
| SYS-010 | Provider：提供 Map Localization 所需的 environment measurement。 |
| SYS-014 | Provider：提供 Navigation 建立有效 obstacle information 所需的 measurement；不負責 avoidance decision。 |
| SYS-023 | Consumer：使用 Robot Description 提供的 LiDAR mounting frame，不擁有 geometry。 |

### Cross-subsystem Relationships

```text
Front LiDAR ─┐
             ├──► LiDAR Perception
Rear LiDAR ──┘          │
                        ├── independent scans ──► Mapping
                        ├── independent scans ──► Map Localization
                        ├── independent scans ──► Navigation
                        └── validity / state ───► operational decisions

Robot Description ── sensor mounting transforms ──► consumers
```

LiDAR Perception reports validity per source。各 consuming subsystem 必須判斷目前有效來源是否足以支援 active operation；若無法維持足夠的有效 perception，該 operation 不得開始或繼續。單一 LiDAR 仍有效不得被直接視為 Mapping、Map Localization 或 Navigation 可降級繼續運作的充分條件。

### LaserScan Fusion Constraint

- 預設提供並使用各 LiDAR 的 independent scan；consumer 可直接使用多個來源時，不導入 LaserScan fusion。
- 只有在 consumer 無法直接使用所需的多來源資料，且單一來源不足以滿足其功能需求時，才可根據 integration 與 real-hardware evidence 評估 LaserScan merge。
- LaserScan merge algorithm 尚未定案。本文件不指定 merge component、algorithm、output representation 或 interface。
- LaserScan merge 不構成獨立的 architecture-level subsystem，也不是 v0.1 的預設資料路徑。

若 State Estimation 的 approved detailed design 採用 LiDAR-derived odometry，LiDAR Perception 仍只提供 valid scan；odometry derivation 屬於 State Estimation internal design。

### Excluded Responsibilities

LiDAR Perception 不負責：

- Occupancy Grid 建立或 Map Package 管理；
- Map Localization 或 global pose estimation；
- obstacle classification、costmap ownership 或 avoidance decision；
- system odometry 或 LiDAR-derived odometry；
- 預設進行 LaserScan merge；
- `map → odom` 或 `odom → base_footprint` ownership；
- sensor mounting geometry ownership；
- driver、topic、message field、network setting、scan frequency 或 merge algorithm 的 detailed design；
- 判定 Mapping、Map Localization 或 Navigation operation 的最終結果。

## 4.5 IMU Perception

IMU Perception 是實體 IMU device 的唯一 software owner。它將 device output 轉換為具有明確時間、座標、單位與有效性的 inertial measurement，不負責姿態估測或 multi-sensor fusion。

### Responsibilities

- 管理實體 IMU device 的 communication 與 data acquisition。
- 驗證 device output 與 measurement integrity。
- 提供 angular velocity 與 linear acceleration。
- 將 measurement 正規化為一致的 physical unit、axis convention、coordinate frame 與 timestamp semantics。
- 提供 measurement validity、device state 與 fault。
- 套用已核准的 sensor calibration，使輸出符合 system measurement contract。
- 資料遺失、逾時或無效時，不得將 stale measurement 宣告為有效。
- 確保 measurement frame 與 Robot Description 一致。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-004 | Primary owner：提供可供定位使用的有效 IMU measurement。 |
| SYS-005 | Provider：向 State Estimation 提供 system odometry 所需的 inertial measurement；不擁有最終 odometry。 |
| SYS-010 | Indirect provider：透過 State Estimation 支援 Map Localization；不判斷 localization validity。 |
| SYS-023 | Consumer：使用 Robot Description 的 IMU mounting frame，不擁有 mounting geometry。 |

### Cross-subsystem Relationships

```text
Physical IMU Device
        │ device measurement / state
        ▼
  IMU Perception
        │
        ├── angular velocity
        ├── linear acceleration
        ├── timestamp / frame
        └── validity / fault
                  │
                  ▼
          State Estimation
                  │
                  ├── system planar odometry
                  └── odometry validity
```

Mapping、Map Localization 與 Navigation 原則上使用 State Estimation 的 system odometry，不各自重新解析、校正或轉換 IMU device output。若成熟元件需要直接使用 IMU measurement，仍必須使用 IMU Perception 所擁有的同一 measurement source 與 validity contract。

### Calibration and Orientation Contracts

IMU Perception 負責 device scale conversion、axis mapping、fixed bias / scale correction 與 calibration configuration validity。State Estimation 負責 estimation-level filtering、fusion、covariance policy 與 system state estimation。Robot Description 負責 IMU mounting geometry 與 static frame relationship。

Calibration method、parameter value 與 verification procedure 屬於 detailed design、configuration 與 real-hardware evidence，不在本文件定義。

IMU Perception 不得合成 orientation estimate，除非 physical device 或 approved estimation component 提供經驗證的 orientation measurement。沒有可靠 orientation measurement 時，必須明確標示 unavailable；robot pose 與 yaw estimation 屬於 State Estimation。

IMU measurement 失效時，IMU Perception 負責回報 invalid / unavailable。State Estimation 判斷剩餘來源是否足以維持有效 odometry；依賴 subsystem 再依 odometry 與 localization validity 決定是否可開始或繼續 operation。本文件不預設 IMU 失效後一定可降級運作或必須立即停止。

### Excluded Responsibilities

IMU Perception 不負責：

- system pose、yaw 或 planar odometry estimation；
- wheel、LiDAR 或其他 sensor fusion；
- `odom → base_footprint` 或 `map → odom` ownership；
- Map Localization validity；
- navigation planning、control 或 stopping decision；
- IMU mounting geometry ownership；
- serial device、driver、packet format、topic 或 message field 的 detailed design；
- 在本文件固定 calibration value、filter algorithm 或 covariance。

## 4.6 Mapping

Mapping 擁有二維 Occupancy Grid 的建立與持續更新，以及 Mapping mode 中的 `map → odom`。Map Package 的儲存、驗證與載入由獨立的 Map Management 負責。

### Responsibilities

- 接受開始、完成或終止 Mapping operation 的控制。
- 使用有效且足夠的 LiDAR scan 與 system planar odometry 建立二維 Occupancy Grid。
- Mapping 進行期間持續更新 active Occupancy Grid。
- 提供 Mapping state 與其 input validity dependency。
- 在 Mapping mode 中獨占 `map → odom`。
- 使用者完成環境巡覽後，將 candidate Occupancy Grid 提交給 Map Management。
- 無法初始化、必要輸入失效或無法繼續建圖時，終止 Mapping 並回報原因。
- 在 Map Package 尚未成功儲存並驗證可重新載入前，不得宣告整體建圖成功。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-001 | Primary owner：建立二維 Occupancy Grid。 |
| SYS-003 | Consumer：使用 LiDAR Perception 提供的有效 scan。 |
| SYS-005 | Consumer：使用 State Estimation 提供的有效 system planar odometry。 |
| SYS-006 | Primary owner：取得新的有效 perception 與 odometry 後持續更新地圖。 |
| SYS-023 | Consumer：使用 Robot Description 提供的 frame relationships。 |
| SYS-024 | Shared：回報 Mapping 是否成功開始、持續及產生 candidate map；Map Management 負責 package 儲存與 reload validation。 |

SYS-002 與 SYS-007 由 Map Management 擁有，不配置給 Mapping。

### Cross-subsystem Relationships

```text
LiDAR Perception ── valid independent scan(s) ──┐
                                                │
State Estimation ── planar odometry / validity ─┼──► Mapping
                                                │       │
Robot Description ── frame relationships ───────┘       ├── active Occupancy Grid
                                                        ├── map → odom
                                                        ├── Mapping state
                                                        └── candidate map
                                                                  │
                                                                  ▼
                                                           Map Management
```

### Coordinate-frame Contract

Mapping 與 Map Localization 對 `map → odom` 的 ownership 必須互斥：

```text
Mapping mode:    Mapping owns map → odom
Navigation mode: Map Localization owns map → odom
```

任何時候只能存在一個有效的 `map → odom` owner。Mapping 終止或離開 active state 後，不得繼續宣告此 transform 的 ownership。

### LaserScan Input Constraint

- Mapping 優先使用 LiDAR Perception 提供的 independent valid scan source，不預設 LaserScan merge。
- Mapping implementation 可直接使用多個來源時，應直接使用各來源。
- 若 implementation 只能使用單一來源，必須以 integration 與 real-hardware evidence 證明該來源足以完成建圖。
- 只有單一來源不足，且 implementation 無法直接使用所需的多來源時，才可評估 LaserScan merge。
- 本文件不指定 merge algorithm、merged representation 或 interface。

Mapping 的 architectural input 是「有效且足夠的 LiDAR perception」，不是「必須存在 merged scan」。

### Teleoperation and Result Contracts

Mapping 不接收或轉送 `teleop_twist_keyboard` 的 vehicle velocity command。Mapping active 時，external teleoperation source 才可被 operational flow 授權；Mapping 終止或失敗後，該 command authority 必須撤銷。所有停止行為仍經 Motion Control 與 Drive Hardware Interface 執行。

Mapping 只產生 candidate Occupancy Grid。Map Management 必須將其儲存為 Map Package 並驗證可重新載入；只有兩個階段皆成功，系統才能依 SYS-024 回報 Mapping Success。

```text
Mapping: candidate Occupancy Grid ready
                    │
                    ▼
Map Management: package stored and reloadable
                    │
                    ▼
System: Mapping Success
```

### Excluded Responsibilities

Mapping 不負責：

- Map Package file storage、format、path、reload 或 lifecycle；
- Station 或 Navigation Target resource；
- Map Localization；
- navigation planning、control 或 obstacle avoidance；
- vehicle velocity command、teleoperation 或 differential-drive control；
- system odometry；
- LiDAR / IMU device communication；
- `odom → base_footprint` ownership；
- SLAM algorithm、plugin、topic、parameter 或 map file format 的 detailed design；
- LaserScan merge algorithm。
