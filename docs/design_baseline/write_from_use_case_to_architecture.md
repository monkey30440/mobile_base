# From Use Case to System Architecture

本文件定義 `mobile_base` 從新增或修改 Use Case，到完成 System Architecture 的唯一撰寫與收斂規範。

適用文件：

```text
docs/01_use_cases.md
docs/02_capabilities.md
docs/03_requirements.md
docs/04_architecture.md
```

本文件規範的是「如何形成設計基準」，不是目前產品功能本身。實際功能、需求與架構仍分別以 01–04 為 authoritative source。

# 1. Purpose and Scope

本規範用於：

- 新增 Use Case；
- 修改既有 Use Case；
- 將 backlog item 提升為正式 baseline；
- 修正 01–04 之間的 traceability 缺口；
- 因實機、平台或整合證據而重新檢查既有設計；
- 防止 implementation 或 subsystem internal design 反向主導 system intent。

本規範涵蓋：

- 各文件的 authority 與責任；
- 01→02→03→04 的撰寫順序；
- 各層允許與禁止的內容；
- traceability 與 requirement allocation；
- architecture decomposition、operational flow 與 system-wide contract；
- 逐題討論、approval gate 與最終一致性檢查；
- 何時回到上游文件修正。

本規範不涵蓋：

- `05_subsystem.md` 的撰寫格式；
- package、node、class 或 source-file design；
- ROS interface、parameter、algorithm 或 protocol design；
- implementation plan 與 verification procedure 的詳細格式。

# 2. Authority Model

## 2.1 Normative Chain

01–04 必須遵守單向 authority：

```text
User Goal / Approved Product Intent
                │
                ▼
01 Use Cases
                │ normative input
                ▼
02 Capabilities
                │ normative input
                ▼
03 Requirements
                │ normative input
                ▼
04 System Architecture
```

各文件回答不同問題：

| Document | Authoritative Question |
|---|---|
| 01 Use Cases | 使用者要完成什麼工作？ |
| 02 Capabilities | 系統必須具備哪些穩定能力？ |
| 03 Requirements | 哪些可觀察、可驗證的行為或限制必須成立？ |
| 04 Architecture | 系統如何分解責任、協作並維持跨 subsystem contract？ |

下游文件不得靜默改寫上游 intent：

```text
04 不得自行新增 03 未要求的 system behavior
03 不得為既有 04 補造 requirement
02 不得為既有 subsystem 補造 capability
01 不得為既有 implementation 補造 user intent
```

## 2.2 Downstream Boundary

```text
04 Architecture
        │ design basis
        ▼
05 Subsystem Design
        │ design basis
        ▼
Implementation / Configuration
        │ evidence
        ▼
Verification
```

05 與 implementation 可以：

- 實現 04 的 responsibility allocation 與 contracts；
- 提供可行性、效能、平台或實機證據；
- 揭露 01–04 的缺漏、矛盾或不可行假設；
- 提出上游 change request。

05 與 implementation 不可以：

- 成為 04 的 normative design source；
- 靜默新增 user-visible behavior；
- 因既有程式方便而改寫 requirement；
- 以 package、node 或 framework 結構取代 system decomposition。

若下游證據顯示 01–04 必須改變，應回到最早受影響的 authoritative layer，重新走完後續收斂流程。

## 2.3 Baseline and Backlog

- 01–04 只描述目前已核准的 design baseline。
- 尚未核准、future-only 或未排程的想法放入 backlog。
- 架構可以保留已由 requirement 定義的 extension boundary，但不得把未實作能力寫成目前可用功能。
- Design Baseline 表示設計已確認，不表示已實作、已整合或已完成實機驗證。

# 3. End-to-End Workflow

新增或修改 Use Case 時，必須依序完成：

```text
0. Establish change intent and evidence
1. Write or revise Use Case
2. Write or revise Capability
3. Write or revise Requirements
4. Audit 01–03 consistency
5. Analyze architecture impact
6. Revise System Architecture
7. Audit traceability and consistency
8. Approve the new design baseline
9. Hand off to 05 / implementation
```

不得跳過中間層直接由想法修改 04。若某層不需要修改，仍須說明為何既有內容已完整涵蓋新 intent。

## 3.1 Incremental Discussion Rule

Architecture work 應一次只處理一個明確問題：

```text
identify one issue
        │
        ▼
explain evidence and consequence
        │
        ▼
propose the smallest conceptual correction
        │
        ▼
obtain approval
        │
        ▼
edit and verify
        │
        ▼
move to the next issue
```

不得把尚未確認的設計決定藏在大型 rewrite 中。概念決定與文件編輯必須分開：先確認，後寫入。

## 3.2 Evidence Rule

設計依據應標明 evidence type：

- approved user / product intent；
- current normative document；
- official version-specific platform documentation；
- repository source evidence；
- runtime or ROS graph evidence；
- integration evidence；
- real-hardware evidence；
- assumption or unresolved question。

不同 evidence 不得互相冒充。例如：

- process active 不代表 output valid；
- topic 存在不代表資料正確；
- source code 支援不代表實機已驗證；
- kernel 或 configuration 名稱不代表 end-to-end timing 已證明；
- design approved 不代表 feature frozen。

# 4. Writing 01_use_cases.md

## 4.1 Purpose

Use Case 描述使用者為完成一個有意義結果而與系統進行的端到端工作流程。

Use Case 必須保持 user-visible，不描述 subsystem 如何實現。

## 4.2 Required Structure

每個 Use Case 至少包含：

```text
# UC-xxx 名稱

## 目的
## 參與者
## 前置條件
## 觸發條件
## 基本流程
## Alternative Flow, when applicable
## Failure / Cancellation Flow, when applicable
## 完成條件
## 使用系統能力
```

可依 workflow 需要補充 input variants、manual step 或 result semantics，但不得藉此引入 internal component。

## 4.3 Content Rules

Use Case 應回答：

- 誰發起工作？
- 想達成什麼結果？
- 開始前哪些 user-visible condition 必須成立？
- 什麼事件觸發流程？
- 正常流程如何從開始走到完成？
- 哪些重要替代流程仍能達成相同目標？
- 哪些失敗或取消情況必須讓使用者知道？
- 何時才算完成？

使用者認知相同、只因 input format 或 internal strategy 不同的流程，優先合併為同一 Use Case。

例如：

```text
Station target ─┐
                ├── one user goal: navigate to destination
Pose target ────┘
```

不要因 target type 不同就建立兩套 Navigation Use Cases，除非 actor、目的、完成條件或 user-visible lifecycle 確實不同。

## 4.4 Forbidden Content

除非技術本身就是經核准的 user contract，Use Case 不得指定：

- subsystem、package、node 或 class；
- ROS topic、service、action 或 message；
- algorithm、planner、controller 或 filter；
- file schema、database 或 protocol；
- Behavior Tree 或 lifecycle implementation；
- internal retry、state machine 或 framework。

不佳：

```text
使用者呼叫某 Action，某 Node 再呼叫某 Planner。
```

較佳：

```text
使用者提交目標；系統驗證並解析目標，完成工作或回報原因。
```

## 4.5 Use-case Review Gate

進入 02 前必須確認：

- 目的、actor、trigger 與 completion condition 清楚；
- basic flow 可從 trigger 走到完成；
- 重要 failure / cancellation path 已描述；
- 相同 user intent 未被不必要拆分；
- 沒有 internal design leakage；
- 已取得明確 approval。

# 5. Writing 02_capabilities.md

## 5.1 Purpose

Capability 描述系統為支持一個或多個 Use Cases，必須長期具備的能力。Capability 應在技術實作改變後仍成立。

## 5.2 Required Structure

每個 Capability 至少包含：

```text
# CAP-xxx 名稱

## 目的
## 系統能力
## 輸入, when applicable
## 核心語意或策略, when applicable
## 輸出
## 使用情境
## 對應 Use Case
```

## 5.3 Derivation Rule

Capability 必須直接由已核准 Use Case 推導：

```text
Use Case workflow step
        │
        ▼
required stable system ability
```

每項 Capability 都必須能回答：

- 它支持哪個 Use Case？
- 若拿掉它，哪個 user workflow 無法完成？
- 它描述的是能力還是元件？
- 換掉內部技術後，這句話是否仍成立？

## 5.4 Canonical-model Rule

多種 external input 表達相同 intent 時，Capability 應要求先正規化，再進入共同 execution：

```text
External Form A ─┐
External Form B ─┼──► Resolution ──► Canonical Form ──► Core Execution
External Form C ─┘
```

新增 input type 時，優先擴充 resolution boundary，不應讓 core execution 增加平行流程。

## 5.5 Separate Intent, Resource, Strategy, and Execution

Capability 必須區分：

| Concept | Question |
|---|---|
| Intent | 使用者要達成什麼？ |
| Resource | 系統可使用哪些資料或基礎資源？ |
| Strategy | 系統依目前條件選擇什麼達成方式？ |
| Execution | 系統如何執行並產生結果？ |

不得把 resource 或 strategy 編入 user intent 的身份，除非使用者確實把它視為不同工作。

## 5.6 Forbidden Content

Capability 不得依賴：

- 特定 ROS package 或 framework；
- node、topic、service、action；
- algorithm 或 parameter；
- source-code structure；
- 未核准的 future capability。

不佳：

```text
系統可透過 Framework X 的 Plugin Y 導航。
```

較佳：

```text
系統可自主導航至使用者指定之目標。
```

## 5.7 Capability Review Gate

進入 03 前必須確認：

- 每項 Capability 都可追溯到 Use Case；
- Use Case 的每個必要 system behavior 都有 Capability 支持；
- Capability 是能力，不是 component list；
- input、resource、strategy 與 execution 沒有混淆；
- 不包含 implementation technology；
- 已取得明確 approval。

# 6. Writing 03_requirements.md

## 6.1 Purpose

Requirement 將 Capability 轉換為可觀察、可驗證，且可在 04 配置 owner 的 system obligation。

## 6.2 Required Form

每項 requirement 使用穩定且唯一的 ID：

```text
## SYS-xxx 名稱

系統應……
```

同一 requirement 可以包含正常行為、必要限制與失敗行為，但不應塞入多個彼此無關的責任。

## 6.3 Requirement Quality Rules

每項 requirement 必須回答：

- 由哪個 Use Case／Capability 推導？
- 系統必須做什麼或維持什麼限制？
- 如何觀察 Success／Failure？
- 哪個 architecture responsibility 可以擁有它？
- 未來如何驗證？
- 是否不必要地指定 implementation？

Requirement 必須使用可判定語意，例如：

- 應提供；
- 應拒絕並回報原因；
- 不得開始或繼續；
- 只有在條件成立時才可；
- 失效時應終止、停止或標示 invalid。

避免只寫：

- 應適當處理；
- 應具有良好效能；
- 應盡可能安全；
- 應使用最佳方法。

## 6.4 Observable, Not Invented Numeric Precision

需要 threshold、timeout、tolerance、limit 或 timing 時：

- 若已有核准 evidence，寫入可驗證值或引用其 authoritative configuration boundary；
- 若尚無 evidence，Requirement 應要求該條件必須經整合或實機驗證確立；
- 不得為了看起來精確而虛構數值。

Architecture 可以配置參數 ownership 與 verification obligation，但不應猜測 operational value。

## 6.5 Failure Classification

Requirement 應區分不同 failure boundary，不得用模糊的單一 Failure 吞掉重要原因。

例如應區分：

- input invalid；
- resource/configuration invalid；
- state/localization invalid；
- execution-stage failure；
- hardware/communication failure；
- cancellation；
- safe-stop outcome。

Fallback eligibility 不得被 resource、configuration 或 invalid input 靜默觸發；兩者必須由 requirement 明確區分。

## 6.6 Traceability Table

03 必須維護至少下列 traceability：

| Requirement | Use Case | Capability |
|---|---|---|
| SYS-xxx | UC-xxx | CAP-xxx |

每個 SYS requirement 必須至少映射一個 approved UC 與 CAP。無上游來源的 requirement 應刪除、修正，或先補齊真正的 user/system need。

## 6.7 Forbidden Content

Requirement 原則上不得指定：

- package、node、class；
- topic、service、action 或 message routing；
- algorithm、plugin 或 framework internal；
- file layout 或 source structure；
- 為既有 implementation 量身補造的行為。

若標準、protocol 或具體 platform version 本身是必要 external constraint，必須說明它為何是 requirement，而不是直接把 solution 當需求。

## 6.8 Requirement Review Gate

進入 04 前必須確認：

- 每項 SYS 都有 UC／CAP traceability；
- 每個必要 Capability 都由一項以上 SYS 支持；
- Requirement 可觀察並具有 verification path；
- 正常、失敗、取消與 safety semantics 無矛盾；
- requirement IDs 唯一且沒有 stale entry；
- 沒有 implementation leakage；
- 01–03 已完成共同 consistency review 並取得 approval。

# 7. Writing 04_architecture.md

## 7.1 Purpose

04 定義：

- system decomposition；
- responsibility allocation；
- cross-subsystem relationships；
- operational flows；
- system-wide architectural contracts。

04 不描述任何單一 subsystem 的 internal design。

## 7.2 Normative Input Rule

04 只能以已核准的 01–03 作為 normative input。

可以使用其他資料做為：

- platform capability evidence；
- implementation feasibility evidence；
- real-hardware constraint evidence；
- contradiction or risk discovery material。

但這些資料不能靜默創造 01–03 未定義的 product behavior。若證據要求新行為，先回到最早受影響的上游文件修改並核准。

## 7.3 Required Architecture Content

04 至少應包含：

```text
1. Purpose, Scope and Authority
2. Architecture Drivers
3. System Context
4. System Decomposition and Responsibility Allocation
5. Cross-subsystem Architectural Contracts
6. Operational Flows
```

### Purpose, Scope and Authority

說明：

- 本文件的 system-level 責任；
- normative inputs；
- downstream documents；
- architecture 與 internal design 的邊界。

### Architecture Drivers

將需求群組整理為真正影響 decomposition 或 contracts 的 driver。不要完整複製 03，也不要把技術偏好包裝成 driver。

### System Context

定義：

- system boundary；
- external actors、tools、devices、environment；
- 外部交換的 intent、measurement、resource、command 與 result；
- system 不允許 external entity 繞過的控制或 safety boundary。

### System Decomposition

依責任分解 subsystem，而不是依現有 package 或 process 名稱分解。

每個 subsystem 至少定義：

```text
## 4.x Subsystem Name

一段 purpose / ownership statement

### Responsibilities
### Requirement Allocation
### Cross-subsystem Relationships
### Architecture-level Contracts, when required
### Excluded Responsibilities
```

### Cross-subsystem Contracts

集中定義多個 subsystem 都必須遵守的不變條件，例如：

- authoritative ownership；
- command authority；
- coordinate-frame ownership；
- resource identity；
- readiness / validity propagation；
- result and safe-stop semantics；
- operating-mode lifecycle。

### Operational Flows

以 end-to-end 方式串接 Use Case：

```text
activation / prerequisites
        ↓
input acceptance / validation
        ↓
execution stages
        ↓
completion / result
        ↓
failure and safe-stop path
```

Operational flow 描述 subsystem 間的順序與責任，不展開 subsystem internal state machine。

## 7.4 Responsibility Allocation

每項 SYS requirement 必須在 04 具有可辨識 allocation：

| Allocation Role | Meaning |
|---|---|
| Primary owner | 對 authoritative behavior／result 負最終責任。 |
| Provider / Contributor | 提供必要資料、evidence 或局部結果，不取代 Primary owner。 |
| Consumer | 使用 authoritative input，並遵守其 validity contract。 |
| Coordinator | 協調 lifecycle 或跨 subsystem ordering，不接管原 owner 的判定。 |

規則：

- 每個 authoritative output／decision 只可有一個 Primary owner；
- 多個 subsystem 可以共同實現 requirement，但必須分清最終 owner；
- `Shared` 只能暫時表示責任尚需分解，不能作為最終 authoritative-result ownership；
- 若 requirement 無法配置，優先檢查 decomposition 或 requirement 是否錯誤；
- 不得為了配合現有 component 而扭曲 requirement。

## 7.5 Ownership Audit

至少檢查：

```text
Who owns the external intent normalization?
Who owns each authoritative resource identity?
Who owns each authoritative state estimate?
Who owns each dynamic transform?
Who assigns command authority?
Who enforces command authority?
Who owns execution?
Who aggregates the final result?
Who owns fault classification?
Who owns physical-device access?
```

常見錯誤：

- coordinator 與 executor 都宣稱決定相同 policy；
- provider 與 aggregator 各自發布完整結果；
- driver 與 controller 都產生同一 odometry；
- mapping 與 localization 同時發布相同 TF；
- 兩個 command source 以 arrival order 決定車體運動。

## 7.6 Canonical Interface and Resource Identity

不同 external forms 應在進入 core execution 前正規化：

```text
external variants
        ↓
validation / resolution
        ↓
canonical internal form
        ↓
one execution boundary
```

與場域或 deployment 綁定的資料應有單一 active identity。使用同一 operation 的 map、graph、catalog、configuration 或 target 不得跨 identity 混用。

Resource loaded 不等於 valid；valid 不一定等於 operation ready。每一層狀態必須有 owner 與 consumer rule。

## 7.7 Validity Contract

04 必須明確區分：

```text
process active
interface exists
message received
resource loaded
initialization input provided
        ≠
authoritative output valid
        ≠
operating flow ready
```

Provider 負責宣告 readiness、validity、fault 與 freshness；consumer 負責在開始前及執行中使用該狀態。Consumer 不得自行將 invalid 改寫為 degraded success，除非上游 requirement 已核准 degraded behavior。

## 7.8 Result and Safety Contract

Product／operation result 與 safe-stop outcome 必須正交：

```text
Operation-specific Result
        +
Primary Failure Reason, when applicable
        +
Secondary Safety Failure, when applicable
        +
Safe-stop Outcome
        +
Operating State
```

停止請求、命令已送出、硬體已接受與 feedback 已確認停止是不同 evidence level。不得因 safe-stop failure 覆蓋原始 operation result，也不得因 product success 隱藏 safety failure。

## 7.9 Mature-solution-first Rule

當 architecture 依賴外部 platform capability 時：

```text
required capability
        ↓
official version-specific documentation
        ↓
mature capability available?
        ├── yes: configure or compose
        └── no: identify smallest gap
                    ↓
               minimal custom boundary
```

Preference order：

```text
configuration
    ↓
composition
    ↓
thin adapter
    ↓
small extension
    ↓
custom subsystem
    ↓
custom framework
```

04 只記錄因此形成的 system responsibility 或 constraint，不展開 framework internal design。

## 7.10 Architecture Forbidden Content

04 不得包含：

- 單一 subsystem 的 internal component decomposition；
- package、node、class 或 source-file structure；
- ROS topic、service、action、message routing 或 QoS；
- algorithm、filter、planner、controller 或 internal orchestration；
- protocol register、packet 或 conversion formula；
- parameter value、timeout value 或 tolerance；
- file name、schema 或 directory layout；
- detailed recovery policy；
- verification procedure；
- 由 05 或 implementation 反向帶入的設計結論。

具名工具或 platform 只有在它是經 01–03 核准的 external contract 時才能出現在 04；若只是 implementation choice，應使用 architecture-level generic term。

## 7.11 Architecture Review Gate

04 完成前必須確認：

- 每個 SYS requirement 都有 allocation 或 contract；
- 每個 authoritative output／decision 都有單一 owner；
- provider、consumer、coordinator 與 aggregator 角色清楚；
- system context、decomposition、contracts 與 operational flows 一致；
- command、TF、resource identity、validity、result 與 safety 無重複 owner；
- 正常、替代、失敗、取消與 future-only boundary 未互相矛盾；
- 04 沒有單一 subsystem internal design；
- 05 只作 leakage diagnostic，不作 design basis；
- 所有 conceptual issue 已逐項取得 approval。

# 8. Change-impact and Backtracking Rules

## 8.1 Start at the Earliest Affected Layer

| Change Type | Start Here |
|---|---|
| 新的 user goal、actor、trigger 或 completion condition | 01 |
| 既有 workflow 需要新的穩定 system ability | 02；若 user flow 也改變則回 01 |
| 新的 observable behavior、constraint 或 failure semantics | 03；若 capability 也改變則回 02 |
| 只改 responsibility allocation 或 cross-subsystem relationship | 04 |
| 只改 subsystem internal design | 05，不改 01–04 |
| 只改 implementation／configuration | implementation layer |

若無法確定，從較上游開始檢查；不得從 04 或 05 猜測 user intent。

## 8.2 Architecture-impact Questions

修改 04 前至少回答：

- 新 requirement 是否已有 owner？
- 是否需要新的 subsystem，或只是既有 responsibility 的擴充？
- 是否新增 authoritative data／decision？
- 是否改變 command、TF、resource、validity 或 result contract？
- 是否影響 Mapping／Navigation operational flow？
- 是否讓兩個 subsystem 重複擁有同一責任？
- 是否引入 future-only capability？
- 是否可由成熟方案的 configuration／composition 滿足？

新增 subsystem 是最後手段。若既有 subsystem 能在不破壞 cohesion 與 ownership 的情況下承擔責任，優先擴充既有 boundary。

## 8.3 Contradiction Rule

發現兩個 authoritative-looking definitions 不一致時：

1. 停止新增設計；
2. 找出各自 authority 與 evidence；
3. 以較上游 approved intent 為基準；
4. 一次解決一個 contradiction；
5. 更新所有受影響文字、diagram、allocation 與 traceability；
6. 再繼續下一個議題。

不得只選擇對目前 implementation 最方便的版本。

# 9. Traceability and Closure

完整 traceability chain：

```text
UC-xxx
   ↓
CAP-xxx
   ↓
SYS-xxx
   ↓
Primary Architecture Owner
   ↓
Cross-subsystem Contract / Operational Flow
   ↓
Downstream Verification Obligation
```

## 9.1 Upward Traceability

- 每個 CAP 都能找到 supporting UC。
- 每個 SYS 都能找到 supporting UC 與 CAP。
- 每個 architecture driver 都能找到 supporting SYS。
- 沒有因現有 component 而孤立存在的 requirement。

## 9.2 Downward Traceability

- 每個 SYS 都有 Primary owner 或明確的 authoritative aggregation owner。
- Contributor 的局部結果不會被誤當成完整 system result。
- 每個 Use Case 都有完整 operational flow。
- 重要 failure path 有 detection owner、propagation、stop responsibility 與 result boundary。

## 9.3 Coverage Is Not Closure

只在 04 搜尋到 `SYS-xxx` 不代表已完成 allocation。還必須確認：

- role 是否正確；
- owner 是否唯一；
- diagram 與文字是否一致；
- result 是否有最終 aggregator；
- failure 是否保留原始 owner；
- consumer 是否遵守 validity contract。

# 10. Review Checklist

## 10.1 01–03 Review

- [ ] Use Case 描述 user workflow，不描述 internal design。
- [ ] 相同 user intent 未因 input／strategy 不同而不必要拆分。
- [ ] Capability 描述穩定能力，不綁定技術。
- [ ] Requirement 可觀察、可驗證且可配置 owner。
- [ ] 所有 SYS 具有 UC／CAP traceability。
- [ ] Failure、cancellation、fallback 與 safety semantics 可區分。
- [ ] 未核准未來能力仍留在 backlog。
- [ ] 01、02、03 已依序取得 approval。

## 10.2 Architecture Review

- [ ] 04 只以 01–03 為 normative input。
- [ ] System boundary 與 external entities 清楚。
- [ ] Decomposition 依 responsibility，而不是依 package。
- [ ] 每個 subsystem 有 responsibilities 與 excluded responsibilities。
- [ ] 每個 SYS 有明確 allocation。
- [ ] 每個 authoritative output／decision 只有一個 owner。
- [ ] Command authority decision 與 enforcement 分離。
- [ ] Raw measurement、derived state 與 system-authoritative state 分離。
- [ ] Dynamic TF 與 static TF owner 唯一。
- [ ] Resource identity 與 compatibility contract 完整。
- [ ] Process active／resource loaded 未被誤當 output valid。
- [ ] Product result、safe-stop outcome 與 operating state 分離。
- [ ] Mapping 與 Navigation operational flow 從 prerequisite 到 result 閉合。
- [ ] Diagram、表格與文字沒有矛盾。
- [ ] 04 沒有 single-subsystem internal design 或具名 implementation leakage。

## 10.3 Mechanical Review

- [ ] ID 唯一且編號正確。
- [ ] Heading 層級與編號連續。
- [ ] 無 TODO、TBD、FIXME 或 placeholder。
- [ ] 無 obsolete subsystem name 或 stale terminology。
- [ ] 無舊流程、舊 diagram 或 contradictory statement。
- [ ] Markdown／diff whitespace check 通過。
- [ ] 變更只涵蓋預期文件與概念。

# 11. Approval Gates

每一層都必須有明確 gate：

```text
Gate 1: Use Case approved
Gate 2: Capability approved
Gate 3: Requirements and traceability approved
Gate 4: Architecture issues approved one by one
Gate 5: Requirement allocation complete
Gate 6: Internal-design leakage audit complete
Gate 7: Final consistency review complete
```

未通過 Gate 3，不得開始 04 的 responsibility decomposition。未通過 Gate 7，不得將 04 視為新的 Design Baseline。

Approval 應針對具體內容，不得把「繼續」解讀為核准尚未提出的未來設計。

# 12. Definition of Done

一次 Use Case 新增或修改只有在下列條件全部成立時，才完成 01–04 closure：

- 01 的 workflow、failure 與 completion semantics 已核准；
- 02 已定義支持該 workflow 的穩定能力；
- 03 已建立 observable requirements 與 UC／CAP traceability；
- 04 已完成 requirement allocation；
- 新 intent 已納入正確 operational flow；
- authoritative owner、resource、state、command、TF、result 與 safety contracts 無衝突；
- future-only scope 明確留在 backlog 或 reserved boundary；
- implementation detail 未洩漏到 01–04；
- affected documents 已完成 consistency review；
- 使用者已確認新的 01–04 Design Baseline。

完成 01–04 只表示可以開始 downstream subsystem design，不表示 implementation 或 verification 已完成。

# 13. Minimal Worked Example

以下範例只示範層級轉換，不定義 `mobile_base` 的新功能。

## 13.1 Use Case

```text
目的：使用者要求系統完成某項工作。
觸發：使用者提交 Target A 或 Target B。
基本流程：系統驗證 target，完成工作並回報結果。
失敗流程：target 無效時拒絕並回報原因。
完成條件：工作完成且結果已回報。
```

## 13.2 Capability

```text
系統可以接受多種 target 表達、驗證並正規化為共同 target，完成同一核心工作。
```

## 13.3 Requirements

```text
SYS-A：系統應接受 Target A 與 Target B。
SYS-B：系統應驗證 target；無效 target 應拒絕並回報原因。
SYS-C：有效 target 應正規化為 Canonical Target。
SYS-D：系統應使用 Canonical Target 執行工作並回報結果。
```

## 13.4 Architecture

```text
External Target
      │
      ▼
Target Resolution
      │ Canonical Target
      ▼
Execution
      │
      ▼
Result
```

Allocation：

| Requirement | Primary Owner |
|---|---|
| SYS-A、SYS-B、SYS-C | Target Resolution |
| SYS-D | Execution |

此例的重點是：多種 external forms 在 boundary 正規化，core execution 不因 input type 增加平行流程；具體 message、node、algorithm 與 package 留給 downstream design。

# 14. Document Maintenance

- 本文件是 01–04 authoring workflow 的唯一方法基準。
- 方法改變時更新本文件，不在其他 baseline 文件建立重複規則。
- 01–04 的產品內容改變時更新其 authoritative document，不把產品結論寫回本方法文件。
- 歷史決策由 version control 或專門 decision record 保存，不在 current baseline 並列互相矛盾版本。
- `05_subsystem.md` 完成重構後，應另行建立 downstream subsystem-authoring 規範；不得把 05 internal-design 規則塞入本文件。
