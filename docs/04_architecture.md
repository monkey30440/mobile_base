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
- algorithm、internal orchestration 或 recovery implementation；
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
| AD-009 | Route-preferred Navigation | SYS-012、SYS-013、SYS-018、SYS-019、SYS-020、SYS-021 | 系統必須分離 Navigation Target、Navigation Resources、strategy selection 與 movement execution；有效且可安全執行的 Route Graph 應優先使用，並以 First Mile、On Route、Last Mile 組成 route-assisted movement。架構保留受限的 Free-space Fallback boundary，但 v0.1 不執行 fallback movement。 |

本章只整理需求對架構造成的影響，不新增需求內容。

Route Graph、Route-assisted Navigation、First Mile、On Route、Last Mile 與保留但未實作的 Free-space Fallback boundary 為 requirement-derived baseline。特定 planning、control、internal orchestration、route-search 或 recovery implementation 仍不是 Architecture Driver，應由下游 detailed design 與驗證決定。

# 3. System Context

`mobile_base` 的 system boundary 包含完成 Mapping、Localization / Odometry、Navigation 與 Motion Control 所需的軟體責任，以及系統所管理的 Navigation Resource Set、Navigation Configuration 與 Robot Description。

Operator、Navigation Client / Upper Layer、teleoperation tool、commissioning operator / tool、實體感測器、Drive Hardware 與 Physical Environment 均位於此 system boundary 之外。

```text
 Operator                         Navigation Client / Upper Layer
    │                                         │
    │ keyboard input                          │ navigation target / cancellation
    ▼                                         ▼
 External Teleoperation Tool ────────► ┌─────────────────────────┐
        manual velocity command       │                         │
                                      │       mobile_base       │
 Commissioning Operator / Tool ──────►│                         │
        route and station resources   │                         │
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
| Operator | 操作 external teleoperation tool、發起或監督 Mapping 工作，並在 v0.1 需要時提供 approximate initial pose 以初始化地圖定位。 |
| External Teleoperation Tool | 將 Operator 輸入轉換為 Manual Velocity Command；不得直接控制 Drive Hardware。具體工具屬 downstream implementation choice。 |
| Navigation Client / Upper Layer | 提交 Navigation Target、要求取消導航，並接收 navigation feedback 與 result。 |
| Commissioning Operator / Tool | 依 Mapping 所建立的地圖建立或維護 Route Graph 與 Station Catalog，並將場域 navigation resources 提供給 `mobile_base`。此 entity 不參與 runtime route selection 或 navigation execution。 |
| LiDAR Devices | 提供環境量測；不負責地圖建立、定位或避障決策。 |
| IMU Device | 提供慣性量測；不負責 system pose 或 odometry 的最終估測。 |
| Drive Hardware | 接收受控的底盤命令，並回報 wheel measurement、device state 與 fault。 |
| Physical Environment | 被 LiDAR 感測，並受到 AMR 實體運動影響。 |

## 3.2 Boundary Contracts

- External Teleoperation Tool 只提供 Manual Velocity Command；`mobile_base` 負責 command acceptance、operational-limit enforcement、timeout handling、motion execution 與 safe stopping。
- Navigation Client / Upper Layer 提供 Station ID 或 Goal Pose；`mobile_base` 負責驗證、解析並正規化 Navigation Target。
- `mobile_base` 將同一場域的 Map Package、Route Graph 與 Station Catalog 管理為單一 Navigation Resource Set。Map Package 與 Route Graph 必須共同選取、載入並通過相容性驗證；Station Catalog 必須屬於同一 resource set，並在處理 Station Target 前通過驗證。
- Map Package 由 Mapping flow 產生；Route Graph 與 Station Catalog 由 external commissioning process 建立或維護。其來源不同不得破壞 Navigation Resource Set 的一致性。
- Navigation Configuration 是獨立於場域 Navigation Resource Set 的 software deployment configuration；兩者均有效時，Navigation 才可進入 operational state。
- Route Graph 描述 route-preferred movement resource；Station Catalog 將 Station ID 定義為 `map` frame 中的 Canonical Goal Pose。Station 不得因部署格式而被強制等同於 Route Graph node。
- `mobile_base` 是 Drive Hardware 的唯一軟體控制邊界。外部 client 與 operator tool 不得繞過此邊界直接下達 drive command。
- `mobile_base` 管理 Mapping 所產出的 Map Package；Mapping 回報 Success 或 Failure，Navigation 回報 Success、Failure 或 Canceled。
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

Drive Hardware Interface 的 downstream design 必須實現本節所配置之 requirements 與 system-wide contracts；其 internal component、protocol、register、transport、conversion formula 與 timeout value 不在本文件定義。

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

Motion Control 是 vehicle velocity command 與左右輪命令之間的唯一轉換邊界，並根據有效的 measured wheel state 產生 wheel odometry。建圖期間，External Teleoperation Tool 經 Manual Velocity Command 進入此邊界；導航期間則由 Navigation 提供 vehicle velocity command。

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
External Teleoperation Tool                   Navigation
        │ Manual Velocity Command                  │ vehicle velocity command
        └──────────────────┬───────────────────────┘
                           │ authorized source only
                           ▼
                     Motion Control
                       │         ▲
         wheel command │         │ measured wheel state
                       ▼         │ readiness / validity / fault
                 Drive Hardware Interface
                       │         ▲
          drive command│         │ motor feedback
                       ▼         │
                    Drive Hardware

Motion Control ── wheel odometry ──► State Estimation
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

LiDAR-derived odometry 不構成獨立的 architecture-level subsystem，也不是 SYS-005 的必要條件。只有在 approved estimation design 需要，且 integration evidence 證明其輸入、frame、timing 與品質適合時，才可作為 State Estimation 的 internal source。

本文件不要求固定融合 Wheel Odometry、LiDAR-derived Odometry 與 IMU 的特定組合。

### Excluded Responsibilities

State Estimation 不負責：

- LiDAR 或 IMU device communication；
- wheel command、differential-drive control 或 Drive Hardware lifecycle；
- Occupancy Grid 建立或 Map Package 管理；
- 在已載入地圖中估測 global pose；
- `map → odom` ownership；
- navigation planning、control 或 arrival determination；
- auxiliary-odometry implementation、filter algorithm、filter parameter、covariance 或 external interface 的 detailed design；
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
- obstacle classification、navigation environment-model ownership 或 avoidance decision；
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

Mapping 擁有二維 Occupancy Grid 的建立與持續更新，以及 Mapping mode 中的 `map → odom`。Map Package 的儲存、驗證與載入由獨立的 Navigation Resource Management 負責。

### Responsibilities

- 接受開始、完成或終止 Mapping operation 的控制。
- 使用有效且足夠的 LiDAR scan 與 system planar odometry 建立二維 Occupancy Grid。
- Mapping 進行期間持續更新 active Occupancy Grid。
- 提供 Mapping state 與其 input validity dependency。
- 在 Mapping mode 中獨占 `map → odom`。
- 使用者完成環境巡覽後，將 candidate Occupancy Grid 提交給 Navigation Resource Management。
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
| SYS-024 | Primary owner：聚合 Mapping execution、candidate Occupancy Grid，以及 Navigation Resource Management 提供的 storage / reload-validation result，回報唯一 Mapping Result。 |

SYS-002 與 SYS-007 由 Navigation Resource Management 擁有，不配置給 Mapping。

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
                                                   Navigation Resource Management
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

Mapping 不接收或轉送 External Teleoperation Tool 的 vehicle velocity command。Mapping active 時，external teleoperation source 才可被 operational flow 授權；Mapping 終止或失敗後，該 command authority 必須撤銷。所有停止行為仍經 Motion Control 與 Drive Hardware Interface 執行。

Mapping 只產生 candidate Occupancy Grid，不執行 Map Package storage 或 reload validation。Navigation Resource Management 必須提供上述 package-operation result；Mapping 聚合兩階段 evidence，只有兩階段皆成功時才可依 SYS-024 回報唯一 Mapping Success。

```text
Mapping: candidate Occupancy Grid ready
                    │
                    ▼
Navigation Resource Management: package stored and reloadable
                    │
                    ▼
Mapping: authoritative Mapping Success
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
- mapping algorithm、internal extension、external interface、parameter 或 map file format 的 detailed design；
- LaserScan merge algorithm。

## 4.7 Navigation Resource Management

Navigation Resource Management 是場域 Navigation Resource Set 的 selection、loading、validation、readiness 與 activation owner。v0.1 以人工管理的單一場域資料集合為部署單位；此 logical subsystem 不代表必須建立自訂 resource-management framework 或獨立 software package。

### Responsibilities

- 接收唯一的場域 resource-set selection，並由該 selection 取得同一集合中的 Map Package、Route Graph 與 Station Catalog。
- 禁止以彼此獨立的 resource selection 組合不同場域的 Map Package、Route Graph 或 Station Catalog。
- 接收 Mapping 產生的 candidate Occupancy Grid，儲存為 Map Package，並驗證可重新載入。
- 在 navigation startup 前檢查必要 resource 是否存在、可解析且可由其 consuming subsystem 載入。
- 彙整 Map Package、Route Graph、Station Catalog 與 Navigation Configuration 的 readiness。
- 只有 Map Package 與 Route Graph 通過驗證，且 Navigation Configuration 有效時，才可將 resource set 宣告為 navigation-ready。
- 處理 Station Target 前，額外要求同一 resource set 的 Station Catalog 通過驗證。
- Resource 缺失、無效或不相容時回報 configuration failure，不得將其轉換為 free-space fallback。
- 提供唯一的 active resource-set identity，供 Map Localization、Navigation Target Resolution 與 Navigation 使用。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-002 | Primary owner：將 candidate Occupancy Grid 儲存為可重新載入的 Map Package。 |
| SYS-007 | Primary owner：載入已儲存的 Map Package，並提供有效的 Occupancy Grid。 |
| SYS-009 | Provider：向 Navigation Target Resolution 提供同一 resource set 的 valid Station Catalog。 |
| SYS-010 | Provider：向 Map Localization 提供 active Occupancy Grid 與 map readiness。 |
| SYS-012 | Primary owner：彙整 Navigation Resource Set 與 Navigation Configuration validation，並提供 navigation readiness。 |
| SYS-013、SYS-018～SYS-021 | Provider：向 Navigation 提供同一 resource set 的 valid Route Graph；不擁有 strategy 或 execution。 |
| SYS-024 | Contributor：提供 Map Package storage 與 reload-validation result；不得自行以 package-operation result 取代完整 Mapping Result。 |

### Cross-subsystem Relationships

```text
Mapping ── candidate Occupancy Grid ────────────┐
                                                │
Commissioning Operator / Tool ── Route Graph ───┼──► Navigation Resource Management
                                 Station Catalog│             │
                                                │             ├── active map ──► Map Localization
Navigation Configuration ── config readiness ───┘             ├── Station Catalog ──► Navigation Target Resolution
                                                              ├── Route Graph ──► Navigation
                                                              └── resource-set identity / readiness
```

Navigation Resource Management 擁有 resource lifecycle，不擁有各 resource 的 domain semantics：Map Localization 解讀 active map；Navigation Target Resolution 解讀 Station Catalog；Navigation 解讀 Route Graph 並執行 route-preferred movement。

### Validation Contract

Compatibility validation 分成兩個證據邊界：

- Runtime validation：所有 runtime resource 由同一 resource-set selection 取得，且必要 resource 存在、可解析、可載入並使用一致的 coordinate-frame contract。
- Commissioning validation：Route Graph 與 Station Pose 在 active map 中的幾何位置合理、route 可執行、Station 可由核准策略抵達，並具有對應的整合或實機 evidence。

Runtime validation 不得宣稱能取代尚未實作的 geometric compatibility proof；人工管理亦不得取代 runtime 的 existence、parsing 與 loading checks。

### Lifecycle Contract

Mapping Success 與 Navigation Ready 是不同狀態：

```text
candidate Occupancy Grid
        │ store and reload-validate
        ▼
Map Package Ready ───────────────► Mapping Success may be reported
        │ commissioning adds Route Graph and Station Catalog
        ▼
Navigation Resource Set Complete
        │ resource and configuration validation
        ▼
Navigation Ready
```

Navigation Resource Set 尚未完成，不影響已成功儲存且可重新載入之 Map Package 回報 Mapping Success；但不得開始 Navigation。

### Excluded Responsibilities

Navigation Resource Management 不負責：

- 建立 Occupancy Grid；
- 自動建立或編輯 Route Graph、Station Catalog；
- Station ID resolution；
- route search、strategy selection 或 navigation execution；
- Map Localization；
- dynamic resource switching、version management、checksum、rollback、remote deployment 或 resource database；
- resource directory、file name、schema、server、service 或 ROS interface 的 detailed design。

## 4.8 Navigation Target Resolution

Navigation Target Resolution 是外部 Navigation Target 到 Canonical Goal Pose 的唯一 validation and normalization boundary。v0.1 的 Navigation Target 由 terminal client 提交，支援 Station ID 與 Absolute Goal Pose；Navigation execution 不得依 target source 建立不同核心流程。

### Responsibilities

- 接收 Station ID 或 Absolute Goal Pose，並識別其 target type。
- 驗證輸入資料完整、數值有效且 coordinate-frame semantics 可用。
- 使用 Navigation Resource Management 提供的 active、valid Station Catalog 解析 Station ID。
- 將 Station target 解析為 position 與 orientation 完整的 goal pose。
- 將有效 Absolute Goal Pose 正規化為 active map frame 的 goal pose。
- 產生與 active resource-set identity 關聯的 Canonical Goal Pose。
- 對 unknown Station、invalid pose、unavailable frame 或 normalization failure 回報 target-resolution failure。
- 將有效 Canonical Goal Pose 交給 Navigation，並保持 Station 與 Goal Pose 共用同一 execution boundary。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-008 | Primary owner：接受並區分 Station ID 與 Goal Pose。 |
| SYS-009 | Primary owner：驗證 Navigation Target，並解析為 Canonical Goal Pose。 |
| SYS-012 | Consumer：只使用 active、valid、compatible resource set 中的 Station Catalog。 |
| SYS-017 | Contributor：提供 invalid target、unknown Station 與 target-resolution failure reason。 |

### Cross-subsystem Relationships

```text
Terminal Navigation Client
        │
        ├── Station ID ──────────────────────────┐
        └── Absolute Goal Pose ──────────────────┤
                                                 ▼
Navigation Resource Management ─────────► Navigation Target Resolution
        └── active Station Catalog                    │
                                                     │ Canonical Goal Pose
                                                     ▼
                                                 Navigation
```

Navigation Resource Management 擁有 Station Catalog 的 selection、loading、readiness 與 active resource-set identity；Navigation Target Resolution 擁有 Station ID lookup 與 target semantics。Navigation Target Resolution 不管理 resource directory 或 activation。

### Canonical Goal Contract

Canonical Goal Pose 至少具有下列 architectural semantics：

```text
Canonical Goal Pose
├── position
├── orientation
├── active map frame
└── associated active resource-set identity
```

Station 定義最終應抵達的位置與朝向，不得被強制等同於 Route Graph node。Route entry、route exit、First Mile、On Route、Last Mile 與 fallback eligibility classification 均由 Navigation 決定，不屬於 target resolution。

Target validity 與 reachability 必須分離：Navigation Target Resolution 判斷 target 是否能形成有效 Canonical Goal Pose；Navigation 判斷該 pose 是否可透過核准策略安全抵達。無法到達不得被重新分類為 invalid target。

### Failure Boundaries

- Resource failure：Station Catalog 缺失、無法載入或 resource-set mismatch，由 Navigation Resource Management 依 SYS-012 回報；不得視為 fallback。
- Target failure：Station ID 不存在、Goal Pose 無效、frame 不可用或無法正規化，由 Navigation Target Resolution 依 SYS-009 回報；不得視為 fallback。
- Navigation failure：route selection、First Mile、On Route、Last Mile 無法完成，或符合保留 eligibility 但 Free-space Fallback unavailable，由 Navigation 回報。

### v0.1 Input Constraint

Relative Pose 不屬於 v0.1 Navigation Target。若未來納入，必須先建立上游 requirement，並在 input boundary 將其一次性解析為 active map frame 的 Absolute Canonical Goal Pose，不得使 Navigation core 增加相對座標執行分支。

`DriveOnHeading` 或其他指定距離 movement primitive 不構成 Navigation Target，也不經此 subsystem 執行。

### Excluded Responsibilities

Navigation Target Resolution 不負責：

- Station Catalog file lifecycle、resource-set selection 或 activation；
- Route Graph loading、route search、route entry / exit selection；
- First Mile、On Route、Last Mile 或 Free-space Fallback；
- path planning、obstacle avoidance、motion control、arrival determination 或 navigation result aggregation；
- task queue、priority、scheduling、automatic retry 或 fleet management；
- terminal CLI syntax、ROS message、topic、service 或 action 的 detailed design。

## 4.9 Map Localization

Map Localization 是 Navigation Mode 下，AMR 在 active Map Package 中之 global pose、localization validity 與 `map → odom` 的唯一 owner。它使用既有地圖與感測、里程估測資料修正全域位置，不負責建立地圖、規劃路徑或控制車體。

### Responsibilities

- 只在 Navigation Resource Management 已提供 active、valid、compatible Map Package 後建立 localization context。
- 接收 LiDAR Perception 提供的有效 scan measurement。
- 接收 State Estimation 提供的 system planar odometry 與 odometry validity。
- 使用 Robot Description 擁有的 frame relationships 解讀 sensor 與 base frames。
- 當開機位置無法可靠得知時，接受 Operator / Tool 提供之 approximate initial pose 作為 localization initialization input。
- 估測並提供 AMR 在 active map frame 中的 current pose。
- 判斷並提供 localization validity / state，不得將 stale、未收斂或與 active resource set 不一致的 pose 宣告為有效。
- 在 Navigation Mode 下獨占 `map → odom` 的發布權。
- localization 失效時明確回報狀態與 failure reason，使 Navigation 終止或拒絕依賴有效定位的 execution。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-010 | Primary owner：在已載入地圖中提供 current pose 與 localization validity。 |
| SYS-012 | Consumer：只使用 active、valid、compatible resource set 中的 Map Package。 |
| SYS-017 | Contributor：提供 localization state 與 localization failure reason。 |

### Cross-subsystem Relationships

```text
Navigation Resource Management ── active Map Package / readiness ──┐
LiDAR Perception ──────────────── valid scan measurement ──────────┤
State Estimation ──────────────── planar odometry / validity ──────┼──► Map Localization
Robot Description ─────────────── frame relationships ─────────────┤          │
Operator / Tool ───────────────── approximate initial pose ────────┘          │
                                                                              ├── current map pose
                                                                              ├── localization validity
                                                                              └── map → odom
```

Navigation Resource Management 擁有 Map Package 的 selection、loading、readiness 與 active resource-set identity；Map Localization 擁有該地圖中的 pose estimation 與 validity。載入成功不等於 localization 已有效。

### Initial Pose Provision Contract

當 AMR 開機位置無法由系統可靠得知時，v0.1 由 Operator 透過外部工具提供 active map frame 中的 approximate `x`、`y` 與 `yaw`。Map Localization 擁有該輸入的接受、有效性檢查與 localization initialization responsibility。

Initial Pose Provision、localization process active 與 localization valid 是不同狀態：

```text
active Map Package ready
        │
        ▼
approximate initial pose provided, when required
        │
        ▼
Map Localization converges
        │
        ▼
localization valid
        │
        ▼
Navigation may accept execution
```

Approximate initial pose 不是 Navigation Target，也不能單獨證明 current pose 有效。具體 initial-pose tool 與 localization interface 屬 implementation choice，不是本文件的 system-wide contract。自動定位、固定開機點與保存上次位置不屬於 v0.1。

### Coordinate-frame Ownership Contract

`map → odom` 必須由目前 operating mode 的單一 subsystem 擁有：

```text
Mapping Mode       Mapping owns map → odom
Navigation Mode    Map Localization owns map → odom
```

Mapping 與 Map Localization 不得同時發布 `map → odom`。State Estimation 在兩種 mode 下均維持 `odom → base_footprint` 的唯一 ownership；Robot Description 維持 `base_footprint → base_link` 與 sensor static transforms 的 ownership。

### Localization-loss Contract

Navigation execution 期間發生 localization invalid 時，責任鏈必須維持：

```text
Map Localization ── invalid state / reason ──► Navigation
                                                    │
                                                    └── terminate or reject execution
                                                               │
                                                               ▼
                                                        Motion Control
                                                        revokes autonomous command
                                                        and reaches safe stop
```

Map Localization 只負責偵測並回報定位狀態，不直接發布 motion command。Navigation 負責停止依賴有效定位的 execution；Motion Control 負責撤銷 autonomous command 並使車體進入 safe stop。

### Excluded Responsibilities

Map Localization 不負責：

- Occupancy Grid 建立、Map Package 儲存或 resource-set activation；
- Route Graph、Station Catalog 或 Navigation Target resolution；
- route search、First Mile、On Route、Last Mile 或 Free-space Fallback；
- path planning、obstacle avoidance、arrival determination 或 navigation result aggregation；
- `odom → base_footprint` 或 static transform ownership；
- 直接發布 wheel command、velocity command 或控制 Drive Hardware；
- localization algorithm、filter、recovery policy、parameter 或 ROS interface 的 detailed design。

## 4.10 Navigation

Navigation 是一次 autonomous navigation execution 的唯一 owner。它接收已正規化的 Canonical Goal Pose，在必要資源與定位均有效的前提下，以 route-preferred 原則協調完整 movement execution，並產生單一 navigation result。Navigation 不擁有 target resolution、resource lifecycle、localization estimation 或 Drive Hardware。

### Responsibilities

- 一次只管理一個 active navigation execution。
- 開始 execution 前確認 Canonical Goal Pose、navigation resource readiness 與 localization validity 等 preconditions 已成立。
- 根據 current pose、Canonical Goal Pose 與有效 Route Graph 建立完整 route-preferred movement strategy。
- 協調 First Mile、On Route 與 Last Mile；辨識 SYS-021 eligibility，但 v0.1 不啟動 Free-space Fallback movement。
- 為目前 active navigation stage 規劃並維持可安全執行的有效路徑。
- 執行 path tracking、obstacle avoidance、stage progress monitoring 與 stage transition。
- 接受使用者對 active execution 提出的 cancellation request。
- 在完成、取消或失敗時撤銷 autonomous motion command。
- 只有在 Canonical Goal Pose 的 position、orientation acceptance conditions 與 chassis stopped condition 均成立時判定成功。
- 聚合並回報 Success、Failure 或 Canceled，以及可辨識的 execution stage / failure boundary。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-010 | Consumer：有效定位是開始及持續 navigation execution 的必要條件。 |
| SYS-011 | Primary owner：為 active navigation stage 規劃並維持有效路徑。 |
| SYS-012 | Consumer：只在必要 navigation resources 均 ready 時開始 execution。 |
| SYS-013 | Primary owner：建立並維持 route-preferred movement strategy。 |
| SYS-014 | Primary owner：使用有效環境資訊避免不安全的 navigation movement。 |
| SYS-015 | Primary owner：追蹤 active stage path 並監控 stage transition。 |
| SYS-016 | Primary owner：依 goal acceptance 與 chassis stopped conditions 判定成功。 |
| SYS-017 | Primary owner：聚合並回報最終 navigation result 與 failure boundary。 |
| SYS-018 | Primary owner：協調 First Mile execution。 |
| SYS-019 | Primary owner：協調 On Route execution。 |
| SYS-020 | Primary owner：協調 Last Mile execution。 |
| SYS-021 | Primary owner：判斷保留的 eligibility；v0.1 終止 execution 並回報 Free-space Fallback unavailable。 |
| SYS-025 | Primary owner：接受取消要求並終止 active navigation execution。 |

### Cross-subsystem Relationships

```text
Navigation Target Resolution ── Canonical Goal Pose ─────────────┐
Navigation Resource Management ─ resources / readiness ─────────┤
Map Localization ─────────────── current pose / validity ────────┤
LiDAR Perception ──────────────── environment measurement ───────┼──► Navigation
State Estimation ──────────────── planar odometry / validity ────┤         │
User ──────────────────────────── cancellation request ──────────┘         ├── autonomous motion command
                                                                          ├── navigation stage / status
                                                                          └── final navigation result
```

Navigation 將 autonomous motion command 提供給 Motion Control，但不擁有 command-source arbitration 或 Drive Hardware。System Operation Coordination 依 active operating mode 指派 command authority；Motion Control 強制執行該 authority，只將目前被授權來源的有效且未逾時命令轉換為 wheel command。

### Execution Ownership Contract

Navigation execution 的 ownership 不因 target type、active stage 或 internal implementation component 改變：

```text
Station ID or Absolute Goal Pose
              │
              ▼
Navigation Target Resolution
              │ Canonical Goal Pose
              ▼
       one Navigation execution
              │
              ├── First Mile, when required
              ├── On Route
              ├── Last Mile, when required
              └── reserved fallback eligibility
                         └── v0.1: Failure / Fallback unavailable
              │
              ▼
   Success, Failure, or Canceled
```

First Mile、On Route 與 Last Mile 是同一 execution 中的 movement stages。保留的 Free-space Fallback 是未啟用的 strategy extension boundary；它不建立另一個 execution owner，也不在 v0.1 產生 movement command。

### First Mile Strategy Contract

First Mile 是 route-assisted movement 的正常連接階段：當 Current Pose 尚未位於所選 route entry 時，Navigation 規劃並執行由 Current Pose 至該 entry 的安全連接。即使此連接使用 Route Graph 範圍外的 free-space path，它仍是為了接入 Route Graph 的 First Mile，不構成 Free-space Fallback。

所選 route entry 不得只根據距離或孤立 graph node 決定；它必須屬於能朝 Canonical Goal Pose 前進的完整 route-assisted candidate：

```text
Current Pose
    │
    ├── First Mile
    ▼
selected route entry
    │
    ├── usable Route Graph route
    ▼
selected route exit
    │
    ├── Last Mile
    ▼
Canonical Goal Pose
```

First Mile 使用 current pose / localization validity、selected route entry、其所屬 route-assisted candidate、有效環境障礙物資訊，以及 system planar odometry / validity。其 architecture-level outcome 為：

| Outcome | Semantics |
|---|---|
| Not Required | Current Pose 已符合 selected route entry 的 acceptance condition；Navigation 可直接進入 On Route，不得判定失敗。 |
| Completed | AMR 已安全抵達 selected route entry，且可安全轉入 On Route。 |
| Failed | 無法規劃、維持或安全完成至 selected route entry 的連接。 |

單一 selected route entry 的 First Mile 失敗，不足以直接宣告 SYS-021 fallback eligibility。Navigation 必須先重新評估其他 usable route-assisted candidates；只有 Current Pose 無法連接任何可用 route entry 時，才符合對應的 Free-space Fallback eligibility：

```text
selected entry connection failed
              │
              ▼
reevaluate other usable route-assisted candidates
              │
       ┌──────┴────────┐
       │               │
alternative found   no usable entry can be connected
       │               │
       ▼               ▼
retry First Mile    SYS-021 fallback eligibility
```

First Mile 只提供 stage outcome 與 failure reason；route-assisted candidate reselection、fallback eligibility 與最終 navigation result 仍由 Navigation execution 統一決定。

First Mile 的 planning implementation、entry scoring、acceptance tolerance、replanning limit、timeout、internal orchestration 與 stage transition 是否要求完全停止，均屬 detailed design 或待整合及實機驗證事項，不由本文件指定。本文件只要求 stage transition 可安全執行。

### On Route Strategy Contract

On Route 是 route-assisted movement 的必要階段：Navigation 沿 selected Route Graph route，從 selected route entry 移動至 selected route exit。On Route 不建立獨立 navigation execution，也不自行接受 Navigation Target 或產生最終 navigation result。

Selected route 必須：

- 由 selected route entry 通往 selected route exit；
- 由連續且相互連接的 Route Graph elements 組成；
- 遵守 Route Graph 定義的 connectivity、direction 與 availability constraints；
- 朝 Canonical Goal Pose 的方向形成完整 route-assisted candidate；
- 能轉換為目前環境下可安全追蹤的 active stage path。

On Route 使用 selected route entry、selected graph route、selected route exit、active Route Graph / resource-set identity、current pose / localization validity、有效環境障礙物資訊，以及 system planar odometry / validity。

Route Graph 約束 topology、movement direction 與可用 route；即時環境資訊約束目前 movement 是否仍可安全執行。Navigation 可為 obstacle avoidance 或 path tracking 調整 selected route 內的 active stage path，但不得：

- 靜默改變 selected graph route；
- 違反 graph connectivity、direction 或 availability constraints；
- 規劃或執行穿越已判定 occupied space 的 movement；
- 將 route-assisted movement 靜默降級為完整 free-space movement。

若局部調整已無法維持 selected route，On Route 必須回報 selected route blocked，不得繼續偏離路網。其 architecture-level outcome 為：

| Outcome | Semantics |
|---|---|
| Completed | AMR 已抵達 selected route exit，且可安全轉入 Last Mile 或 goal completion。 |
| Failed | Selected route 無法建立、維持或安全完成。 |

SYS-018 與 SYS-020 明確允許 First Mile 或 Last Mile 在零長度連接時為 Not Required；SYS-019 未提供 On Route 的省略語意，因此 On Route 不定義 Not Required outcome。

On Route 因目前環境阻塞而無法維持時，Navigation 必須先嘗試在不違反 selected route constraints 下維持安全 stage path；若仍失敗，必須重新選擇其他 usable Route Graph route。只有 route reselection 仍失敗時，才可能符合對應的 SYS-021 Free-space Fallback eligibility：

```text
selected route blocked
          │
          ▼
safe local path adjustment within selected route
          │ failed
          ▼
reselect another usable Route Graph route
          │
    ┌─────┴────────┐
    │              │
route found     reselection failed
    │              │
    ▼              ▼
continue        SYS-021 fallback eligibility
On Route
```

Route Graph 缺失、無效、與 active Map Package 不相容、resource-set identity mismatch，或 Navigation Configuration 無效，均屬 SYS-012 resource/configuration failure，不是 On Route blocked，也不得觸發 Free-space Fallback。Navigation 必須終止 execution、撤銷 autonomous motion command 並回報原因。

On Route 的 graph-search algorithm、route scoring、cost function、node / edge metadata schema、path generation、replanning limit、timeout、acceptance tolerance、internal orchestration，以及 stage transition 是否要求完全停止，均屬 detailed design 或待整合及實機驗證事項，不由本文件指定。本文件只要求 stage transition 可安全執行。

### Last Mile Strategy Contract

Last Mile 是 route-assisted movement 的正常連接階段：當 selected route exit 尚未直接符合 Canonical Goal Pose 時，Navigation 規劃並執行由該 exit 至 Canonical Goal Pose 的安全連接。即使此連接使用 Route Graph 範圍外的 free-space path，它仍是 route-assisted movement 的 Last Mile，不構成 Free-space Fallback。

Last Mile 使用 selected route exit、Canonical Goal Pose、current pose / localization validity、其所屬完整 route-assisted candidate、有效環境障礙物資訊，以及 system planar odometry / validity。其 architecture-level outcome 為：

| Outcome | Semantics |
|---|---|
| Not Required | Selected route exit 已直接符合 Canonical Goal Pose 的 position 與 orientation acceptance conditions。 |
| Completed | AMR 已由 selected route exit 安全抵達 Canonical Goal Pose 的 position 與 orientation acceptance conditions。 |
| Failed | 無法規劃、維持或安全完成 selected route exit 至 Canonical Goal Pose 的連接。 |

只有 selected route exit 已同時符合 Canonical Goal Pose 的 position 與 orientation acceptance conditions，Last Mile 才可判定 Not Required。只有位置相同但 orientation 尚未符合時，terminal alignment 所需的 movement 仍屬 Last Mile。

Last Mile Completed 不直接產生 Navigation Success。Navigation 必須再依 SYS-016 確認完整 arrival conditions：

```text
position accepted
        +
orientation accepted
        +
chassis stopped
        │
        ▼
Navigation Success
```

單一 selected route exit 無法安全連接 Canonical Goal Pose，不足以直接宣告 SYS-021 fallback eligibility。Navigation 必須先重新評估其他 usable route-assisted candidates；只要仍存在可透過其他 route exit 安全銜接目標的 route-assisted solution，就必須優先使用該 solution：

```text
selected exit cannot safely connect goal
                    │
                    ▼
reevaluate other usable route-assisted candidates
                    │
          ┌─────────┴────────────┐
          │                      │
alternative exit / route     no usable route-assisted
found                        candidate can connect goal
          │                      │
          ▼                      ▼
resume route-assisted        SYS-021 fallback eligibility
execution
```

Last Mile 只提供 stage outcome 與 failure reason；route-assisted candidate reselection、fallback eligibility、arrival determination 與最終 navigation result 仍由 Navigation execution 統一決定。

Last Mile 不擁有 Route Graph selection / loading、Station ID resolution、command arbitration 或 Drive Hardware。其 planning implementation、route-exit scoring、goal tolerance、terminal-alignment algorithm、replanning limit、timeout、internal orchestration、parameter 與 approach velocity profile 均屬 detailed design 或待整合及實機驗證事項，不由本文件指定。

### Reserved Free-space Fallback Contract

Free-space Fallback 是保留供後續版本擴充的 Navigation strategy boundary，不是 v0.1 的 active movement strategy。Navigation 仍須辨識下列 SYS-021 eligibility，以提供穩定的 failure semantics：

- Current Pose 無法連接任何可用 route entry；
- active、valid Route Graph 依 connectivity、direction 與 availability constraints 無法提供朝 Canonical Goal Pose 的 usable route；
- On Route 因目前環境阻塞而無法維持，且 Route Graph route reselection 失敗；
- 所有可用 route-assisted candidates 均無法由 route exit 透過 Last Mile 安全連接 Canonical Goal Pose。

Eligibility 是 failure classification boundary，不授權 v0.1 執行 free-space movement。v0.1 的必要行為為：

```text
route-assisted alternatives exhausted
                │
                ▼
SYS-021 eligibility identified
                │
                ▼
terminate Navigation execution
                │
                ├── revoke autonomous motion command
                ├── request safe stop through Motion Control
                └── report Failure: Free-space Fallback unavailable
```

Route Graph、Station Catalog、Navigation Configuration、Canonical Goal Pose 或 localization 的缺失、無效、不相容或 identity mismatch，分別屬於 resource、target 或 localization failure，不構成 SYS-021 eligibility。特別是「active、valid Route Graph 無 usable route」與「Route Graph 無效或缺失」必須保持可辨識。

任一時間不得存在未實作的 fallback movement command source。未來若要啟用 Free-space Fallback，必須先更新上游 capability / requirement baseline，定義其 execution、safety 與 verification obligations，並完成整合及實機驗證；不得僅透過 configuration 將此 reserved boundary 靜默啟用。

### Failure and Command-revocation Boundary

Navigation 不得在必要 resource、target 或 localization precondition 無效時開始 execution。進行中若 current stage 無法安全維持、localization 失效、使用者取消，或沒有可用的核准 strategy，Navigation 必須終止 execution、撤銷 autonomous motion command，並回報 Failure 或 Canceled。Motion Control 負責使撤銷後的底盤達到 safe stop；Navigation 不直接控制馬達。

### Excluded Responsibilities

Navigation 不負責：

- Station ID resolution 或外部 Goal Pose validation / normalization；
- Map Package、Route Graph、Station Catalog 或 Navigation Configuration 的 selection、loading、editing 或 validation ownership；
- global pose estimation、localization validity 判定或 `map → odom` publication；
- system planar odometry estimation 或 `odom → base_footprint` publication；
- Drive Hardware lifecycle、wheel command generation 或 motor communication；
- 多個 command source 的最終 arbitration；
- task queue、mission scheduling、fleet management 或 automatic retry；
- planning、control、internal orchestration、route algorithm、parameter 或 external interface 的 detailed design。

## 4.11 System Operation Coordination

System Operation Coordination 是 operating-flow selection、cross-subsystem lifecycle ordering 與 active command-authority assignment 的唯一 logical owner。它建立 Mapping Mode 或 Navigation Mode 所需的執行環境，但不取代各 subsystem 對自身 readiness、validity、fault 與輸出的 ownership。

此 responsibility 不要求建立專用 runtime coordinator。v0.1 只要求 deployment-time operating-flow selection，不要求 runtime dynamic mode switching；實現方式屬 downstream design。

### Responsibilities

- 接受部署或操作流程所選擇的 Mapping、Navigation 或 Inactive intent。
- 依 subsystem dependencies 啟動、停用並監控所選 operating flow。
- 只有在 mode-specific prerequisites 均成立時，才宣告 Mapping Mode 或 Navigation Mode active。
- 依 active operating mode 指派唯一 vehicle command authority。
- 確保 Mapping 與 Map Localization 不會同時擁有 `map → odom`。
- Mode 結束、transition 或必要 prerequisite 失效時，先撤銷 command authority，再協調 safe stop 與 subsystem deactivation。
- 聚合並回報 operating-flow startup、transition 與 shutdown failure；不得改寫原始 subsystem failure ownership。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-001、SYS-006、SYS-024 | Coordinator：建立並終止 Mapping operating flow；Mapping 保持建圖與結果的 primary ownership。 |
| SYS-010、SYS-012 | Coordinator：將 resource readiness 與 localization validity 作為 Navigation Mode prerequisites；原 subsystem 保持狀態判定 ownership。 |
| SYS-025 | Supporting owner：Navigation 取消後協調 authority revocation 與 flow termination。 |
| SYS-026、SYS-027、SYS-030 | Coordinator：在 fault、timeout、transition 或 shutdown 時協調 authority revocation 與 lifecycle ordering；Drive Hardware Interface 與 Motion Control 保持實際停止責任。 |

### Cross-subsystem Relationships

```text
Deployment / Operator-selected flow
                │
                ▼
     System Operation Coordination
                │
                ├── lifecycle ordering ──► required subsystems
                ├── prerequisite checks ◄── readiness / validity / fault
                ├── active mode ─────────► TF ownership constraints
                └── command authority ───► Motion Control
```

System Operation Coordination 決定何時可宣告 operating mode active；Motion Control 強制執行該 mode 對應的 command authority。System Operation Coordination 不產生 vehicle command、wheel command、map、pose、path 或 navigation result。

### Excluded Responsibilities

System Operation Coordination 不負責：

- Mapping、localization、planning、control 或 hardware communication；
- 判斷各 subsystem 內部資料是否有效；
- 取代 Drive Hardware Interface 或 Motion Control 的 safe-stop actions；
- navigation target resolution、resource validation 或 result aggregation；
- automatic recovery、automatic mode fallback 或 fault 後自動切換 operating flow；
- lifecycle manager、launch file、service、topic、timeout 或 restart policy 的 detailed design。

## 4.12 Robot Description

Robot Description 是 AMR geometry、joint relationships、base-frame semantics 與 sensor static-frame relationships 的唯一 authoritative owner。它為 Perception、State Estimation、Mapping、Map Localization、Motion Control 與 Navigation 提供一致的實體結構模型，但不擁有任何 dynamic state estimate 或 movement decision。

### Responsibilities

- 提供 AMR body geometry 與 footprint semantics。
- 提供 drive、caster 及其他必要 joint definitions 與 relationships。
- 定義 `base_footprint`、`base_link` 與其他 base-fixed frames 的 semantics。
- 定義 LiDAR、IMU 與其他 configured sensors 相對於 base frames 的 mounting relationships。
- 發布或提供 authoritative static transform relationships。
- 驗證 description 的必要內容完整、frame / joint identifiers 一致，且與目前 AMR configuration 相容。
- 提供 description readiness / validity，供 Mapping Mode 與 Navigation Mode activation 使用。
- Description invalid 或與 active hardware / sensor configuration 不相容時，禁止依賴該模型的 operating flow 啟動並回報原因。

### Requirement Allocation

| Requirement | Allocation |
|---|---|
| SYS-023 | Primary owner：提供機器人幾何、座標系、關節定義與 static frame relationships，供感知、定位、建圖與導航使用。 |
| SYS-031 | Provider：提供 Drive Hardware / Motion Control configuration validation 所需的 authoritative joint 與 geometry semantics；不擁有 hardware parameter validation。 |

### Cross-subsystem Relationships

```text
Robot Description
        │
        ├── body geometry / footprint semantics ──► Motion Control / Navigation
        ├── joint definitions / relationships ────► Drive and state consumers
        ├── base fixed-frame relationships ───────► State Estimation
        ├── sensor mounting relationships ────────► Perception
        │                                            Mapping
        │                                            Map Localization
        │                                            Navigation
        └── readiness / validity ─────────────────► System Operation Coordination
```

All consumers 必須使用同一 authoritative description，不得各自維護互相矛盾的 robot geometry、joint mapping 或 sensor mounting transforms。Description ready 只證明結構模型可用，不證明 sensor measurement、odometry、localization、Drive Hardware 或 Navigation 已 ready。

### Dynamic-frame Boundary

Robot Description 只擁有 static geometry 與 fixed relationships，不擁有：

```text
map → odom             owned by Mapping or Map Localization
odom → base_footprint  owned by State Estimation
dynamic joint state    owned by measured-state provider
```

Static description 不得發布或覆蓋上述 dynamic transforms / state。

### Excluded Responsibilities

Robot Description 不負責：

- `map → odom`、`odom → base_footprint` 或其他 dynamic transform ownership；
- joint-state measurement、odometry、localization 或 state estimation；
- sensor communication、measurement validity 或 calibration execution；
- vehicle command、kinematics execution、planning、control 或 navigation result；
- Drive Hardware lifecycle 或 hardware communication；
- description format、mesh、package / file layout 或 external interface 的 detailed design。

# 5. Cross-subsystem Architectural Contracts

## 5.1 Teleoperation and Autonomous Command Authority

任一時間只可有一個被授權的 vehicle motion command source。Mapping teleoperation 與 autonomous Navigation 不得同時控制 AMR，也不得以 command arrival order、last-writer-wins 或 command blending 決定實際運動。

### Authority States

| System State | Authorized Command Source | Required Treatment of Other Sources |
|---|---|---|
| Mapping Mode | External Teleoperation Tool 的 Manual Velocity Command | Navigation command 必須被拒絕或忽略。 |
| Navigation Mode | Navigation 的 autonomous motion command | Manual Velocity Command 必須被拒絕或忽略。 |
| Inactive / Transition / Fault | None | 所有 movement command 均無效；不得產生非零 wheel command。 |

Command authority 由 active operating mode 決定；Motion Control 不自行選擇 Mapping Mode 或 Navigation Mode。Motion Control 負責強制執行已決定的 authority，只接受目前被授權來源的有效 command。

### Authority-transition Contract

Command source 切換必須先撤銷舊來源，再授權新來源；不得存在 ownership overlap：

```text
revoke current command authority
                │
                ▼
reject further commands from old source
                │
                ▼
request chassis stop
                │
                ▼
confirm chassis stopped and Drive Hardware ready
                │
                ▼
authorize new command source
```

若停止確認、Drive Hardware readiness 或其他 transition precondition 未成立，新來源不得取得非零 command authority。Transition failure 必須維持 None authority、繼續嘗試安全動作並回報原因。

### Enforcement and Failure Contract

Motion Control 必須：

- 只將目前 authorized source 的 valid、fresh vehicle command 轉換為 wheel command；
- 拒絕或忽略 unauthorized source 的 command，使其不得影響 wheel output；
- 在 authority 撤銷、authorized source 失效、command timeout 或 Drive Hardware 不可用時輸出停止命令；
- 在沒有 authorized source 時禁止非零輸出；
- 不得融合 Manual Velocity Command 與 autonomous motion command。

Navigation 完成、失敗或取消時，必須撤銷 autonomous motion command。Mapping flow 結束或離開 Mapping Mode 時，必須撤銷 Manual Velocity Command。來源 process 終止不等於已完成安全切換；Motion Control 仍須依 command freshness 與 timeout contract 使底盤停止。

### Safety Boundary

External Teleoperation Tool 是 Mapping Mode 的人工 vehicle command source，不是 E-stop、safety controller、Navigation override 或 hardware emergency-stop mechanism。工具的停止命令與 process termination 不得取代實體 E-stop、Drive Hardware fault response 或 system safe-stop contract。

本文件不指定 command topic、message routing、mux implementation、priority number、QoS、timeout value 或 launch structure。這些屬 detailed design，但其實作必須維持上述單一 authority 與 transition contracts。

## 5.2 Operating Mode and Lifecycle

Operating mode 表示一組已成立的 subsystem lifecycle、ownership 與 command-authority conditions，不只是 configuration value 或 process 是否存在。v0.1 定義下列 states：

| State | Architectural Semantics |
|---|---|
| Inactive | 沒有 active Mapping flow、Navigation execution 或 vehicle command authority。 |
| Mapping Mode | Mapping prerequisites 已成立，Mapping 擁有 `map → odom`，Manual Velocity Command 已授權。 |
| Navigation Mode | Navigation resources 與 localization 等 prerequisites 已成立，Map Localization 擁有 `map → odom`，autonomous motion command 已授權。 |
| Transition | Authority 已撤銷或尚未授權，正在建立或拆除 operating flow；不得輸出非零 wheel command。 |
| Fault | 必要 prerequisite 已失效；不得授權非零 movement，系統正執行或已完成 fault handling。 |

Transition 是 lifecycle transient state，不是供操作員執行任務的 operating mode。v0.1 可在 startup 由 deployment / launch flow 人工選擇 Mapping 或 Navigation；本文件不要求不中斷的 runtime hot switching。

### Mapping Mode Contract

Mapping Mode 的必要 activation sequence 為：

```text
Robot Description ready
LiDAR / required perception ready
Drive Hardware Interface ready
Motion Control ready
State Estimation valid
            │
            ▼
Mapping active and owns map → odom
            │
            ▼
Manual Velocity Command authority granted
```

Mapping Mode 中，Map Localization 不得發布 `map → odom`，Navigation 不得擁有 active execution 或 autonomous command authority。Navigation Resource Management 可接收 Mapping Result，但 Map Package 儲存成功不等於 navigation-ready。

### Navigation Mode Contract

Navigation Mode 的必要 activation sequence 為：

```text
Robot Description ready
LiDAR / required perception ready
Drive Hardware Interface ready
Motion Control ready
State Estimation valid
Navigation resources ready
Approximate initial pose provided, when required
Map Localization valid and owns map → odom
            │
            ▼
Navigation may accept execution
            │
            ▼
autonomous motion command authority granted
```

Navigation Mode 中，Mapping 不得發布 `map → odom`，Manual Velocity Command 不得取得 authority。Navigation 或 localization process active、以及 initial pose 已提供，均不等於 Navigation Mode active；只有 Map Localization 已收斂、localization valid 且所有其他 prerequisites 成立後，Navigation 才可接受 execution 並產生有效 autonomous motion command。

### Mutually Exclusive Ownership

| Ownership | Mapping Mode | Navigation Mode |
|---|---|---|
| Vehicle command authority | External teleoperation | Navigation |
| `map → odom` | Mapping | Map Localization |
| Navigation execution | None | Navigation |
| Map construction | Mapping | None |

LiDAR Perception、IMU Perception、State Estimation、Motion Control、Drive Hardware Interface 與 Robot Description 可作為兩種 flow 的 shared dependencies，但 mode-specific ownership 不得重疊。

### Activation and Deactivation Ordering

Operating mode activation 必須遵守：

```text
start required subsystems
        │
        ▼
verify readiness and validity
        │
        ▼
activate mode-specific subsystem ownership
        │
        ▼
confirm all mode prerequisites
        │
        ▼
grant command authority
```

Operating mode 結束、切換或 fault handling 必須遵守：

```text
revoke command authority
        │
        ▼
request chassis stop
        │
        ▼
confirm chassis stopped when feedback is available
        │
        ▼
terminate active execution / flow
        │
        ▼
deactivate mode-specific subsystems
        │
        ▼
disable Drive Hardware when required
```

任一安全動作失敗不得阻止其餘安全動作之嘗試。停止無法確認、Drive Hardware not ready 或其他 transition prerequisite 未成立時，系統不得授權新的 command source，並必須維持 Transition 或 Fault state 及回報原因。

### Fault Contract

Active mode 的必要 prerequisite 失效時，System Operation Coordination 必須撤銷 command authority、阻止新的 mode-specific execution、協調 safe-stop actions 並保留原始 failure reason。Mode-specific examples 包括：

- Mapping 或 Navigation 共用的 Drive Hardware、Motion Control、State Estimation prerequisite 失效；
- Mapping Mode 的 Mapping owner 意外終止；
- Navigation Mode 的 resource readiness 或 localization validity 失效；
- Navigation Mode 的 Navigation execution owner 無法維持有效狀態。

Fault 不得自動將 Navigation Mode 轉成 Mapping Mode，也不得自動授權 teleoperation 作為 Navigation override。Fault recovery、restart policy 與重新進入 operating mode 的程序屬 detailed design，必須遵守相同 activation preconditions。

## 5.3 System-wide Contract Summary

本節集中列出所有 subsystem 與 implementation 必須維持的 system-wide invariants。各 subsystem 與前述 contract 章節仍是完整責任定義；本摘要不得被解讀為建立新的平行 owner。

| Contract | System-wide Invariant |
|---|---|
| Authoritative ownership | 每個 authoritative output 或 decision 在同一時間只能有一個 owner。 |
| Vehicle command | 任一時間只能有一個 authorized vehicle command source。 |
| Coordinate frame | 每條 authoritative transform 在同一時間只能有一個 owner / publisher。 |
| Resource identity | 同一 localization context 與 Navigation execution 不得混用不同 active resource sets。 |
| Validity propagation | Process、interface 或資料存在不等於 output valid 或 operation ready。 |
| Result and safety | Operation result、primary failure 與 safe-stop outcome 必須分別保存。 |

### Authoritative Ownership Invariant

```text
Drive Hardware access         → Drive Hardware Interface
wheel command generation      → Motion Control
system planar odometry        → State Estimation
active resource-set identity  → Navigation Resource Management
target normalization          → Navigation Target Resolution
global localization pose      → Map Localization
navigation execution / result → Navigation
operating mode / authority    → System Operation Coordination
```

Coordinator 或 consumer 可使用、轉送或聚合 authoritative output，但不得接管原 owner 的 readiness、validity、fault classification 或 result decision。Internal implementation component 的數量不得造成 architecture-level ownership 重疊。

### Vehicle-command Invariant

```text
Mapping Mode       → Manual Velocity Command only
Navigation Mode    → autonomous Navigation command only
Transition / Fault → no authorized non-zero command source
```

所有 vehicle movement command 必須經 Motion Control 與 Drive Hardware Interface 才能作用於 Drive Hardware。任何 subsystem 或 external tool 均不得繞過此 control chain，且不得以 last-writer-wins、arrival order、priority race 或 command blending 決定 authority。

### Coordinate-frame Invariant

```text
Mapping Mode       Mapping owns map → odom
Navigation Mode    Map Localization owns map → odom
All modes          State Estimation owns odom → base_footprint
All modes          Robot Description owns base_footprint → base_link
                   and sensor static transforms
```

Mapping 與 Map Localization 不得同時發布 `map → odom`。Initial Pose Provision 只初始化 Map Localization，不建立新的 TF owner，也不直接證明 transform 或 localization 已有效。

### Resource-identity Invariant

```text
one active resource-set identity
    ├── Map Package
    ├── Route Graph
    └── Station Catalog, when required
```

Map Localization context、Canonical Goal Pose 與 Navigation execution 必須與同一 active resource-set identity 關聯。Resource 缺失、無效、不相容或 identity mismatch 屬 resource/configuration failure，不得被重新分類為 Free-space Fallback eligibility。

### Validity-propagation Invariant

每個 authoritative data owner 必須提供可判斷的 readiness、validity 或 fault；consumer 必須在 operation 開始前及執行中使用該狀態。以下事實均不得單獨視為有效性證據：

```text
process active
interface or topic exists
message received
initial pose provided
resource loaded
        ≠
output valid or operation ready
```

Stale、invalid、unavailable 或 resource-identity mismatch 的 output 不得繼續作為有效輸入。Consumer 不得自行把 provider 宣告的 invalid 狀態改寫為 degraded success；任何 degraded operation 都必須先有上游 requirement 與明確 architectural contract。

### Result-and-safety Invariant

Operation result 與 safe-stop outcome 是正交資訊；每種 operation 的 terminal result set 由其上游 requirement 決定：

```text
Operation result                  Safe-stop outcome
├── Mapping                       ├── Stop Confirmed
│   ├── Success                   ├── Stop Requested, Unconfirmed
│   └── Failure                   └── Stop Failed
└── Navigation
    ├── Success
    ├── Failure
    └── Canceled
```

Safe-stop outcome 不得新增、刪除或改寫特定 operation 的 terminal result set。

Result reporting 必須在適用時保留：

- primary failure reason 與其 owning boundary；
- secondary safety failure；
- active movement stage 或 operating flow；
- safe-stop outcome 與其 evidence level。

Navigation Success 必須搭配 Stop Confirmed。Failure 或 Canceled 不得被後續停止異常覆蓋；停止異常必須作為 secondary safety failure 與 safe-stop outcome 一併回報。

# 6. Operational Flows

## 6.1 Mapping Operational Flow

Mapping operational flow 將 UC-001 串接為單一跨 subsystem 流程。它從使用者選擇 Mapping flow 開始，以成功儲存且可重新載入的 Map Package 或明確 Failure 結束；Route Graph、Station Catalog 與 Navigation readiness 不屬於此 flow 的完成條件。

### Activation

```text
Operator requests Mapping
          │
          ▼
System Operation Coordination
selects Mapping flow and enters Transition
          │
          ▼
verify Robot Description, required perception,
Drive Hardware, Motion Control and State Estimation
          │
          ▼
activate Mapping and grant map → odom ownership
          │
          ▼
confirm Mapping prerequisites
          │
          ▼
grant Manual Velocity Command authority
```

任一 prerequisite 未成立時，Mapping 不得宣告 active，Manual Velocity Command 不得取得 authority，System Operation Coordination 必須回報 startup failure。Map Localization 不得在 Mapping Mode 中同時發布 `map → odom`。

### Environment Exploration and Map Update

Mapping Mode 中存在兩條相互關聯但 ownership 分離的 data flow：

```text
Motion flow

External Teleoperation Tool
        │ Manual Velocity Command
        ▼
Motion Control
        │ wheel command
        ▼
Drive Hardware Interface
        │ measured wheel state
        ▼
Motion Control ── wheel odometry ──► State Estimation

Mapping flow

LiDAR Perception ── valid independent scan(s) ──┐
                                                │
State Estimation ── planar odometry / validity ─┼──► Mapping
                                                │       │
Robot Description ── frame relationships ───────┘       ├── active Occupancy Grid
                                                        ├── Mapping state
                                                        └── map → odom
```

External teleoperation 只負責提供人工 vehicle command；Mapping 不接收或轉送該 command。Mapping 只使用有效且足夠的 perception、system planar odometry 與 frame relationships 持續更新 Occupancy Grid，不得以 stale 或 invalid input 宣告有效更新。

Mapping 的 LaserScan input 仍遵守 independent-source-first contract：非必要不融合，且本文件不指定 merge algorithm。

### Completion and Package Validation

使用者完成環境巡覽後，flow 必須先撤銷 movement authority，再完成 map result：

```text
Operator requests Mapping completion
          │
          ▼
revoke Manual Velocity Command authority
          │
          ▼
reject further teleoperation commands
          │
          ▼
request chassis stop and evaluate stopped state
          │
          ▼
Mapping finalizes candidate Occupancy Grid
          │
          ▼
Navigation Resource Management stores Map Package
          │
          ▼
reload validation
          │
     ┌────┴────┐
     │         │
   passed    failed
     │         │
     ▼         ▼
Mapping Success   Mapping Failure
```

停止確認或其他 safety action 失敗不得阻止其餘安全動作、Map Package finalization、storage 與 reload validation 的嘗試。SYS-024 Mapping Result 仍依 Map Package 是否成功建立、儲存且可重新載入判定；safe-stop failure 不得覆蓋該 product result，但必須另行回報 safe-stop outcome，並使 operating flow 維持 Fault state。Candidate Occupancy Grid 可保留供診斷，但其本身不構成 SYS-024 Success。

Mapping Success 必須同時滿足：

```text
candidate Occupancy Grid produced
                +
Map Package stored
                +
Map Package reloadable
                │
                ▼
SYS-024 Mapping Success
```

Navigation Resource Management 負責 package storage 與 reload validation；Mapping 負責 candidate Occupancy Grid，並聚合兩邊 evidence 產生唯一 Mapping Result。任何一段失敗時，Mapping 均不得回報已建立可重複使用之 Map Package。

### Result Boundary

Mapping Success 只證明 Occupancy Grid 已建立，且 Map Package 已儲存並可重新載入：

```text
Mapping Success
      │
      └── Map Package stored and reloadable

Mapping Success
      ≠
Navigation Ready
```

Route Graph 與 Station Catalog 由後續 commissioning 建立或維護；Navigation Resource Set、Navigation Configuration 與 Map Localization 仍須各自通過 Navigation flow 的 prerequisites。

### Failure Flow

| Failure Boundary | Required Response |
|---|---|
| Mapping prerequisite invalid | 不啟動 Mapping、不授權 Manual Velocity Command，回報 startup failure。 |
| LiDAR、odometry 或 required frame input invalid during Mapping | Mapping 停止宣告有效更新並回報原因；System Operation Coordination 撤銷 authority 並協調停止。 |
| Manual Velocity Command stale / timeout | Motion Control 依 command freshness contract 使底盤停止並回報狀態。 |
| Drive Hardware fault or invalid feedback | Drive Hardware Interface 與 Motion Control 執行各自 fault / safe-stop responsibility。 |
| Candidate Occupancy Grid unavailable | Mapping 回報 Failure；不得要求 package success。 |
| Map Package storage or reload validation failed | Navigation Resource Management 回報 package-operation failure；Mapping 聚合為 SYS-024 Failure，且不得回報 Success。 |
| Flow cannot continue | 撤銷 teleoperation authority、嘗試使底盤停止、終止 Mapping flow 並保留原始 failure reason。 |

Teleoperation process 是否可重新啟動並繼續同一次 Mapping、Mapping pause / resume、automatic retry、mapping algorithm、map serialization 與 package file layout 均屬 detailed design，不由本 operational flow 指定。

## 6.2 Navigation Operational Flow

Navigation operational flow 將 UC-002 串接為單一跨 subsystem execution。它從 Navigation operating flow 的 prerequisites 建立開始，經 target resolution、route-assisted strategy construction 與 movement execution，以 Success、Failure 或 Canceled 結束。

### Navigation Mode Preparation

Navigation 接受 Navigation Target 前，必須完成：

```text
Robot Description ready
LiDAR / required perception ready
Drive Hardware Interface ready
Motion Control ready
State Estimation valid
Navigation Resource Set and Configuration ready
Approximate initial pose provided, when required
Map Localization converged and valid
        │
        ▼
Navigation may accept target
```

Initial Pose Provision 是 Map Localization 的初始化輸入，不是 Navigation Target。Localization process active 或 initial pose 已提供均不等於 localization valid。任一 prerequisite 未成立時，Navigation 不得接受 execution，System Operation Coordination 也不得授權 autonomous movement。

### Target Acceptance and Validation

```text
Terminal Navigation Client
        │ Station ID / Absolute Goal Pose
        ▼
Navigation Target Resolution
        │
        ├── invalid ──► reject and report target failure
        │
        ▼
Canonical Goal Pose
        │
        ▼
Navigation verifies execution preconditions
```

Navigation 接受 execution 前必須確認 Canonical Goal Pose 有效且與 active resource-set identity 關聯一致、必要 Navigation Resources / Configuration ready，且 localization 仍有效。Target failure、resource/configuration failure 與 localization failure 必須由原 responsibility owner 判定並分別回報，不得互相改寫。

### Route-assisted Strategy Construction

```text
Current Pose
Canonical Goal Pose
Active Route Graph
        │
        ▼
evaluate complete route-assisted candidates
        │
        ├── selected route entry
        ├── selected graph route
        └── selected route exit
```

Navigation 必須先確認 candidate 可形成完整 movement continuity：

```text
Current Pose
    └── First Mile
            └── On Route
                    └── Last Mile
                            └── Canonical Goal Pose
```

不得只因找到鄰近 route entry 就開始 movement；selected entry、graph route 與 exit 必須共同構成可朝 Canonical Goal Pose 安全前進的 route-assisted candidate。

v0.1 不執行 Free-space Fallback movement。找不到可安全執行的 route-assisted candidate 時：

- 若符合保留的 SYS-021 eligibility，Navigation 終止 execution、嘗試使底盤停止，並回報 Free-space Fallback unavailable；
- 若原因是 resource/configuration、target 或 localization invalid，回報對應 failure，不得分類為 fallback；
- 若仍存在其他 usable route-assisted candidate，必須優先選擇該 candidate，不得提前終止為 fallback unavailable。

### Movement Execution

```text
First Mile
  ├── Not Required
  ├── Completed
  └── Failed ──► exhaust usable route-assisted alternatives
                         │
                         ▼
On Route
  ├── Completed
  └── Blocked ──► safe local adjustment
                  └── route reselection
                      └── exhaust usable alternatives
                         │
                         ▼
Last Mile
  ├── Not Required
  ├── Completed
  └── Failed ──► exhaust usable route-assisted alternatives
```

任一時間只能有一個 active movement stage。Stage transition 前，舊 stage 必須停止產生有效 autonomous motion command，新 stage 才可取得 execution authority；Navigation 全程維持唯一 execution owner。

Navigation 將 active stage 的 autonomous motion command 提供給 Motion Control。Motion Control 只接受目前 Navigation Mode 授權來源的 valid、fresh command。Localization、active path、required environment measurement、system planar odometry 或其他必要 validity 失效時，Navigation 不得繼續該 stage 的有效 movement。

### Arrival and Result

```text
Last Mile Completed or Not Required
                │
                ▼
position accepted
        +
orientation accepted
        +
chassis stopped
        │
        ▼
Navigation Success
```

Last Mile outcome 不直接等於 Navigation Success。Navigation 只有在 SYS-016 的 position、orientation 與 chassis stopped conditions 全部成立時，才可回報 Success。

Navigation execution 的 terminal results 只有 Success、Failure 或 Canceled。所有 terminal path 均必須遵守：

```text
stop active movement stage
        │
        ▼
revoke autonomous motion command
        │
        ▼
request safe stop
        │
        ▼
preserve original result and reason
        │
        ▼
report final navigation result
```

Success 必須保留 arrival evidence；Canceled 必須保留使用者取消語意；Failure 必須保留 target、resource/configuration、localization、First Mile、On Route、Last Mile、Free-space Fallback unavailable、planning/control 或 hardware failure boundary。Safe-stop action 的額外失敗不得覆蓋原始 execution reason，但必須一併回報。

### Detailed-design Boundary

本 operational flow 不指定 navigation framework interface、internal orchestration、route interface、planning / control implementation、message routing、deployment structure、recovery behavior、timeout 或 retry policy。這些屬 subsystem 或 implementation design，但必須維持本節的單一 execution ownership、stage ordering、failure classification 與 command-revocation contracts。

## 6.3 Failure and Safe-stop Flow

Failure and safe-stop flow 統一規範跨 subsystem 的失效傳遞與停止責任。它不取代各 subsystem 的 failure ownership；其目的在於保留原始原因、阻止進一步 movement、嘗試使底盤停止，並分別回報 execution result 與 safe-stop outcome。

### Unified Failure Sequence

```text
failure detected by owning subsystem
                │
                ▼
mark affected output invalid
                │
                ▼
block new execution / movement
                │
                ▼
revoke active command authority
                │
                ▼
attempt controlled stop
                │
                ▼
disable Drive Hardware when required
                │
                ▼
report original failure
+ safe-stop outcome
```

任一安全動作失敗不得阻止其餘安全動作之嘗試。後續 safe-stop failure 必須追加回報，但不得覆蓋最先導致 execution 或 operating flow 終止的 primary failure。

### Failure Ownership

| Failure Boundary | Detection / Classification Owner |
|---|---|
| Navigation Target invalid | Navigation Target Resolution |
| Navigation Resource / Configuration invalid | Navigation Resource Management |
| Initial Pose invalid、localization invalid / lost | Map Localization |
| System planar odometry invalid | State Estimation |
| LiDAR / IMU measurement invalid | 對應的 Perception subsystem |
| First Mile、On Route、Last Mile 或 reserved fallback boundary | Navigation |
| Planning、tracking、arrival 或 navigation cancellation | Navigation |
| Command timeout、stale command 或 authority violation | Motion Control |
| Drive communication、feedback 或 device fault | Drive Hardware Interface |
| Operating-flow prerequisite loss | System Operation Coordination；原 prerequisite owner 保留根因判定。 |

上層 subsystem 可聚合 failure，但不得將原始分類改寫為無法追溯的 generic failure。Failure report 必須可同時表達 primary failure、後續 secondary safety failure 與 safe-stop outcome。

### Layered Stop Responsibilities

```text
Navigation / Mapping
    └── stop producing valid movement intent
            │
            ▼
System Operation Coordination
    └── revoke command authority
            │
            ▼
Motion Control
    └── issue stop command and prevent non-zero output
            │
            ▼
Drive Hardware Interface
    └── transmit stop / disable request and report response
            │
            ▼
Drive feedback
    └── provide evidence of actual chassis stopped state
```

「已要求停止」、「已送出停止命令」、「Drive Hardware 已接受」與「有效 feedback 已確認底盤停止」是不同狀態。只有最後一項成立時，software flow 才可宣告 Stop Confirmed。

### Safe-stop Outcome

| Outcome | Architectural Semantics |
|---|---|
| Stop Confirmed | 有效 Drive Hardware / chassis feedback 證明底盤已停止。 |
| Stop Requested, Unconfirmed | 已嘗試停止，但 feedback 缺失、無效或不足以確認實際停止。 |
| Stop Failed | Stop / disable action 明確失敗，或有效 feedback 顯示底盤仍在運動。 |

Safe-stop outcome 是附加於 Mapping、Navigation 或 operating-flow result 的 safety evidence，不取代或擴張該 operation 已定義的 terminal result set。Navigation Success 必須要求 Stop Confirmed；Navigation Canceled 或任何 operation Failure 可保留其原始 result，但若停止未確認或失敗，必須一併回報並維持 Fault state。

例如：

```text
Primary failure: Localization Lost
Secondary safety failure: Drive Communication Lost
Safe-stop outcome: Stop Requested, Unconfirmed
```

### Failure Timing

開始 execution / flow 前發現 prerequisite invalid 時：

```text
reject startup or target
    → do not grant command authority
    → do not start movement
    → report owning failure boundary
```

執行中 prerequisite 或 required output 失效時：

```text
invalidate affected output
    → stop active stage / flow
    → revoke command authority
    → attempt safe stop
    → report primary reason + safe-stop outcome
```

正常完成或使用者取消時：

```text
stop generating movement intent
    → revoke command authority
    → request and evaluate chassis stop
    → report Success or Canceled with stop outcome
```

### Command-loss and Drive-fault Contract

Navigation process、teleoperation process 或 command stream 消失時，Motion Control 不得維持最後一筆非零 command；command freshness timeout 後必須阻止非零輸出並要求停止。來源 process 終止不等於底盤已停止。

Drive communication 或 feedback 遺失時，Motion Control 仍須嘗試停止，Drive Hardware Interface 仍須嘗試 stop / disable。Feedback 不可用時不得宣告 Stop Confirmed；System Operation Coordination 必須維持 Fault state，且不得重新授權其他 command source。

### Physical E-stop Boundary

本 AMR 已知配備實體 E-stop 按鈕，且其實體停止功能已確認正常。實體 E-stop 是獨立於 software command path 的安全層，不是 Navigation、Mapping、Motion Control 或 software safe-stop flow 的替代實作。

Software safe stop 只負責撤銷 authority、阻止新命令、請求停止並依 feedback 判斷結果；它不得被宣稱等同於 E-stop、STO 或 certified safety function。當 software 無法確認停止或 Stop Failed 時，系統必須維持 Fault state、回報需要人工介入，並允許人員依現場安全程序使用實體 E-stop。已確認 E-stop 按鈕功能正常，不代表 STO、E-stop feedback integration、diagnostic coverage 或 safety certification 已被本架構驗證。

### Detailed-design Boundary

本 flow 不指定 stop timeout、deceleration / braking profile、retry count、USB reopen / automatic recovery、ROS interface、lifecycle transition、fault-code schema、logging backend，或 E-stop / STO 電氣設計。這些屬 detailed design 或獨立安全驗證範圍。
