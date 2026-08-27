> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# Reuse Assessment

> **Current architecture decision (2026-08-27):** Kinematic-ICP is the selected production LiDAR odometry solution. It consumes physical front LiDAR `/scan_front` and encoder wheel odometry `/diff_drive_controller/odom`, publishes `/lidar_odometry`, and feeds the EKF together with IMU yaw rate. SLAM (`slam_toolbox`) and AMCL consume physical front LiDAR `/scan_front`. Nav2 costmaps and Collision Monitor consume independent `/scan_front` and `/scan_rear` directly. `dual_laser_merger` and merged `/scan` are completely removed from production runtime. RF2O candidate assessments below are retained only as superseded selection history and are not current architecture authority.

# 1. Purpose, Scope and Authority

本文件逐項評估 exact-version 成熟方案對 `mobile_base` v0.1 system requirements 的覆蓋程度，記錄其適用條件、限制、evidence 與尚未覆蓋的最小缺口，作為後續 System Architecture 的受控 feasibility evidence。

本文件回答「現有成熟方案能覆蓋多少」，不回答「產品應該需要什麼」，也不決定 system decomposition、responsibility ownership 或 subsystem internal design。

## 1.1 Assessment Authority and Inputs

`03_requirements.md` 是本文件唯一的 assessment scope。`01_use_cases.md` 與 `02_capabilities.md` 提供每項 requirement 的上游 intent 與 traceability context；01–03 均為已核准 baseline。

本文件對下列 assessment conclusion 具有權威性：

- candidate mature solution 與被查證的 exact version／platform；
- requirement coverage status 與 covered scope；
- known constraints 與適用條件；
- evidence type、source、驗證範圍與尚缺 evidence；
- 尚未覆蓋的 requirement fragment 與 minimum gap；
- 交給 `05_architecture.md` 評估的 architecture considerations。

本文件可以使用 ROS 2 Jazzy、Nav2 Jazzy、exact package version、hardware vendor baseline、repository source、runtime、integration 與 real-hardware results 作為 evidence。Assumption 或尚待查證事項必須明確標示，不得寫成已確認能力。

## 1.2 Scope

本文件必須對 `03_requirements.md` 的每個唯一 `SYS-xxx` 建立獨立且可追溯的 coverage record。可以依成熟方案領域安排查證順序，也可以比較多個候選方案，但不得以 package-level summary 取代單一 requirement conclusion。

每項 assessment 至少涵蓋：

- requirement 原始行為或限制；
- candidate mature solution；
- exact version 與適用 platform；
- coverage status；
- covered scope 與 known constraints；
- uncovered gap；
- evidence 與未驗證範圍；
- downstream architecture consideration。

套件存在、可安裝、process active、interface exists 或 topic 有資料，只能證明對應觀察事實，不代表 requirement 已被完整覆蓋。

## 1.3 Prohibited Decisions

本文件不得：

- 新增、刪除、弱化或重新解釋 01–03 的 product intent 或 requirement；
- 因候選方案能力不足而把部分 requirement 靜默標示為不需要；
- 決定 system decomposition、subsystem responsibility 或 authoritative owner；
- 將 candidate package 直接視為已核准 architecture selection；
- 將 uncovered gap 直接定義成 custom node、package、subsystem 或 framework；
- 展開 subsystem internal component、ROS interface routing 或 source implementation；
- 把未查證版本的泛稱能力寫成 coverage conclusion；
- 把尚待 integration 或 real-hardware validation 的行為寫成已完整驗證。

## 1.4 Upstream Issue and MVP Simplification Rule

若成熟方案無法完整覆蓋某項 requirement，04 應先記錄實際 coverage、constraints 與 minimum gap，不得自行降低 requirement。

若該 gap 使 v0.1 成本或複雜度不符合 MVP 原則，可以提出明確的 requirement-change candidate，內容至少說明：

- 原 requirement 中建議簡化或延後的範圍；
- 成熟方案無法覆蓋的 evidence；
- 對 Use Case、Capability、failure semantics、safety 與 verification 的影響；
- 簡化後仍能維持的 MVP 核心價值；
- 建議移至後續版本或 backlog 的範圍。

Requirement-change candidate 不是已核准變更。處理流程為：

```text
04 發現成熟方案 coverage gap
        ↓
提出 MVP requirement-change candidate 與影響
        ↓
停止該 requirement 的 assessment conclusion
        ↓
回到最早受影響的 01／02／03 討論與核准
        ↓
重新進行受影響的 04 assessment
```

若建議簡化會破壞核心 Use Case 完成條件、安全底線或必要 failure behavior，不得僅因成熟套件不支援而妥協。未取得使用者核准前，不修改 01–03；其他不受影響的 requirements 可以繼續盤點。

## 1.5 Downstream Boundary

`05_architecture.md` 必須使用本文件已核准的 coverage、constraints、evidence 與 minimum-gap conclusions，但最終 solution selection、system decomposition、responsibility allocation 與 cross-subsystem contracts 仍由 05 決定。

下列關係必須保持：

- `Fully Covered` 不代表 05 必須採用該 candidate；
- `Partially Covered` 不代表必須新增 subsystem 或 custom component；
- `Not Covered` 不代表可以刪除或弱化 requirement；
- `Needs Verification` 不得被 05 改寫成已確認能力；
- candidate comparison 不取代 architecture decision；
- minimum gap 不取代 06 subsystem design 或 downstream implementation design。

Authority chain 為：

```text
01–03 Approved Product Intent and Requirements
        ↓
04 Reuse Coverage, Constraints, Evidence, and Minimum Gaps
        ↓
05 System Architecture Decisions
        ↓
06 Subsystem Design
        ↓
Implementation and Verification
```

`05_architecture.md`、`06_subsystem.md` 與 `07_backlog.md` 應待本文件完成並核准後，再依序重新審視。

# 2. Coverage Status and Assessment Record

每個 `SYS-xxx` 必須具有獨立的 requirement-level assessment record，並使用一個主要 Coverage Status。Coverage Status 只描述成熟方案在指定版本與條件下能覆蓋多少 requirement，不代表 implementation、integration 或 real-hardware verification 已完成，也不直接核准 05 的 solution selection。

## 2.1 Coverage Status

| Status | Meaning | Required Record |
|---|---|---|
| `Fully Covered` | 成熟方案在指定 exact version／platform 與適用條件下，完整提供 requirement 所需行為，沒有需要 custom behavior 的已知缺口。必要 configuration、remapping 與標準 composition 不構成 custom gap。 | 明確記錄完整 covered scope、適用條件與 evidence；`Uncovered Gap` 填寫 `None`。 |
| `Partially Covered` | 成熟方案只覆蓋 requirement 的一部分，仍有可明確界定的 capability、interface、integration 或 project-specific gap。 | 分別記錄 covered requirement fragment 與 uncovered requirement fragment，不得只寫「需要客製化」。 |
| `Not Covered` | 已查證合理候選方案，但核心 requirement behavior 沒有成熟方案可提供，或候選能力與 requirement 明確不相容。 | 記錄查證過的候選方案、版本、evidence 與缺少的核心行為。 |
| `Needs Verification` | 現有 evidence 不足以對 coverage 做可靠判斷。 | 記錄待回答的具體問題、所需 evidence 與下一個可執行的 verification action。 |
| `Not Applicable` | 某一候選方案經查證後不適用於此 requirement。 | 說明不適用原因；不得作為 requirement 最終 coverage conclusion，也不得用來跳過 requirement。 |

每個 requirement 最終必須取得 `Fully Covered`、`Partially Covered`、`Not Covered` 或仍有明確 closure action 的 `Needs Verification`。`Not Applicable` 只描述單一 candidate，不描述 requirement 本身不需要實現。

## 2.2 Coverage and Verification Are Independent

Coverage 與 verification 是不同判斷：

- Coverage 回答成熟方案的 documented／evidenced capability 是否涵蓋 requirement。
- Verification 回答該能力在目前 project version、composition、configuration、target platform 與實體 AMR 上已被證明到哪一層。

因此 `Fully Covered` 不代表：

- 套件已安裝或 configuration 已完成；
- interfaces 已與其他 components／subsystems 整合；
- runtime data semantics 與 validity 已確認；
- target platform 或 real hardware 已驗證；
- 05 必須選擇該 candidate。

同樣地，單一 process active、interface exists、topic received 或一次實機成功，不足以單獨證明整個 requirement 為 `Fully Covered`；coverage conclusion 必須對應 requirement 的完整語意與適用條件。

## 2.3 Required Requirement Record

每個 requirement 使用下列固定結構：

```markdown
## SYS-xxx Requirement Name

### Required Behavior / Constraint

<保持 03 原始語意的摘要，不新增、弱化或重新解釋 requirement。>

### Candidate Assessment: <Candidate Name>

| Field | Assessment |
|---|---|
| Candidate Mature Solution | <套件、platform capability 或 `None`> |
| Exact Version / Platform | <被查證的版本與環境> |
| Coverage Status | <Fully Covered / Partially Covered / Not Covered / Needs Verification / Not Applicable> |
| Covered Scope | <已覆蓋的 requirement fragment> |
| Known Constraints | <適用條件與限制> |
| Uncovered Gap | <未覆蓋內容；沒有則填 `None`> |
| Evidence | <證據類型、來源與實際證明範圍> |
| Missing Evidence | <尚待官方、source、integration 或 real-hardware 證明的部分；沒有則填 `None`> |

### Architecture Considerations

<只列出交給 05 評估的選項或限制，不指定 subsystem、owner 或 internal design。>

### MVP Change Candidate

<沒有則填 `None`；若有，記錄建議簡化／延後範圍及影響，不得視為已核准 requirement change。>
```

`Required Behavior / Constraint` 是便於閱讀的摘要，`03_requirements.md` 仍是 requirement 原文的 authoritative source。若摘要無法在不改變語意的情況下縮寫，應直接引用 requirement ID 並以精確轉述描述，不得為了縮短表格而刪除 failure、safety 或 acceptance semantics。

## 2.4 Multiple Candidate Records

同一 requirement 有多個合理候選方案時，每個 candidate 必須使用獨立的 `Candidate Assessment`，並各自記錄 exact version、coverage、constraints、gap 與 evidence；不得將不同候選的優點合併成一個實際不存在的完整方案。

多候選 assessment 後應增加：

```markdown
### Candidate Comparison

<比較各候選的 coverage、constraints、evidence quality、missing evidence 與 minimum gaps；不在 04 做最終 architecture selection。>
```

若只有一個合理 candidate，不需要建立空白 comparison section；但仍必須說明 candidate 搜尋範圍，避免把第一個找到的方案誤認為唯一成熟方案。

## 2.5 MVP Change Candidate Boundary

`MVP Change Candidate` 欄位只記錄可能需要回到 01–03 討論的變更建議：

- `None` 表示 assessment 未提出上游變更，不代表 requirement 已被完整覆蓋。
- 有內容表示 requirement assessment 因可能的 MVP scope change 尚未 closure。
- 該 candidate 未經上游核准前，不得用來提高 Coverage Status、縮小 Uncovered Gap 或視為 03 已修改。
- 上游修改核准後，必須依新 baseline 重新完成受影響 requirement 的 assessment record。

# 3. Exact-version and Evidence-source Rules

Coverage conclusion 必須以可追溯且範圍相符的 evidence 支持。Evidence 的層級取決於它實際能證明的事實，不因來源名稱、文件權威性或測試成功而自動提升為完整 requirement coverage。

## 3.1 Evidence Hierarchy

### 3.1.1 Official Exact-version Evidence

優先使用與 target version／platform 相符的 authoritative source，例如：

- ROS 2 Jazzy 官方文件；
- Nav2 Jazzy package API、configuration guide 與 release documentation；
- 套件指定版本的官方文件與 release notes；
- hardware vendor 正式 manual、specification 或 protocol documentation；
- 已核准的 project hardware／driver design baseline。

Official exact-version evidence 可以證明該版本正式宣告的 capability、interface、configuration 與 known constraints；不能單獨證明本專案已正確設定、跨套件整合成立或目標 AMR 實機行為有效。

### 3.1.2 Source Evidence

Source evidence 包含指定 version／revision 的 source code、plugin export、launch、configuration schema 或 automated test。它可以確認實際 implementation 是否包含某項 logic，以及補足官方文件未明確描述的 interface、failure 或 lifecycle behavior。

Source evidence 不能單獨證明 build、runtime、integration 或 real-hardware behavior。若檢查目前 repository source，必須記錄 commit／revision 與 file path；若檢查 upstream source，必須記錄 package version、tag 或 commit。

### 3.1.3 Build and Installation Evidence

Build／installation evidence 包含 package 可安裝、workspace build 成功、binary 存在或 plugin 可載入。它可以證明指定 version 與 platform 的基本相容性及 dependency closure，不能單獨證明 interface semantics、runtime validity 或 requirement coverage。

### 3.1.4 Runtime Interface Evidence

Runtime interface evidence 包含 process active、node／lifecycle state、interface exists、topic／service／action 可見或收到實際 message。它可以證明 runtime entity 與部分資料流存在。

除非同時驗證 semantic、frame、time、validity、ownership、failure behavior 與 requirement 所需結果，否則 runtime interface evidence 不足以單獨證明完整 requirement coverage。

### 3.1.5 Integration Evidence

Integration evidence 應驗證多個 components 或 subsystems 組合後的 end-to-end contract，包括適用的 producer／consumer compatibility、frame、QoS、lifecycle、resource identity、validity propagation、normal flow 與 failure flow。

Integration evidence 可以證明某一 composition 在指定 configuration 與環境下成立，但不得無條件推廣到未測試的版本、platform、resource set 或 operating condition。

### 3.1.6 Real-hardware Evidence

Real-hardware evidence 必須來自目標 AMR、sensor、M1 drive hardware、target compute platform 或實際 operating environment，並記錄硬體、software、configuration、測試條件與 observed result。

它可以證明特定條件下的實體 device behavior、timing、noise、motion、stopping、localization 或 navigation outcome；單次成功不得被推廣為所有條件皆有效。Motion、fault、safe-stop 與 hardware behavior 的 closure 不得只依一般套件文件或模擬結果。

### 3.1.7 Assumption

Assumption 是尚未由上述 evidence 證明的推測、預期或待確認事項。Assumption 可以被記錄以形成 verification question，但不得支持 `Fully Covered`，且 Coverage Status 必須保持 `Needs Verification`，直到取得足以回答該問題的 evidence。

## 3.2 Required Evidence Citation

每筆用於支持 coverage、constraint 或 gap conclusion 的 evidence 至少記錄：

```text
Evidence Type: Official | Source | Build / Installation | Runtime Interface | Integration | Real Hardware | Assumption
Source: <直接文件連結、repository path、test result 或 evidence artifact>
Exact Version / Revision: <distribution、package version、tag、commit、document revision 或 hardware revision>
Target Platform: <OS、ROS distribution、compute／hardware platform 或 Not Applicable>
Observed or Documented Scope: <此 evidence 實際證明的內容>
Limitations: <不能由此 evidence 推論的內容與適用限制>
Access Date / Test Date: <YYYY-MM-DD>
```

Evidence link 應直接指向支持該 conclusion 的頁面、section 或 artifact，不只指向 project homepage。若無法提供穩定連結，必須記錄足以重新定位來源的 title、version、section、file path 或 command／result artifact。

## 3.3 Exact-version Rule

- ROS 2 與 Nav2 capability 必須以 Jazzy 對應文件或實際部署之 exact package version 查證。
- Hardware capability 必須記錄 model、firmware、protocol／manual revision 與必要 configuration baseline。
- Repository evidence 必須記錄 commit 或明確說明為 current uncommitted workspace evidence。
- 不得以其他 ROS distribution、package latest 文件或不同 hardware revision 無條件代表 target version。
- 若只能找到相鄰版本 evidence，必須標記版本差異與 `Needs Verification`，直到 target version 已確認。
- 沒有 exact version／revision 時，不得將 requirement 標記為 `Fully Covered`。

## 3.4 Evidence Use and Closure Rules

- Official evidence 優先用於判斷成熟方案設計上是否具備能力。
- Source evidence 用於補足文件不清楚處或確認實際 implementation，不取代 runtime／hardware verification。
- Build、runtime、integration 與 real-hardware evidence 各自只能支持其實際觀察範圍。
- Evidence quality 不取代 requirement completeness；必須逐一對照完整 requirement fragments。
- Coverage Status 與 Missing Evidence 必須同時保留，不得因 `Fully Covered` 隱藏尚未完成的 project verification。
- Safety-critical 或 hardware-dependent conclusion 必須明確列出所需 integration／real-hardware evidence；未完成前不得宣稱 end-to-end verified。

## 3.5 Contradictory Evidence

若 official documentation、source、runtime、integration 或 real-hardware evidence 互相矛盾：

1. 將受影響的 Coverage Status 標記為 `Needs Verification`；
2. 保留各 evidence 的 version、scope、condition 與 observed difference；
3. 確認是否比較了不同版本、configuration、platform 或 requirement fragment；
4. 一次處理一個可驗證的矛盾；
5. 取得能區分各假設的 evidence 後，再更新 coverage conclusion。

不得只選擇最符合目前 implementation 偏好的 evidence，也不得以較低層 evidence 無條件推翻適用版本的 authoritative statement；若 real-hardware result 與官方說明不一致，必須保留實際結果並界定適用條件與風險。

# 4. Candidate Comparison and Minimum-gap Rules

Reuse assessment 必須先確認成熟方案可透過 configuration 或 standard-interface composition 覆蓋多少 requirement，再界定最小缺口。不得因第一個候選方案不完整就直接推導 custom implementation，也不得為了避免 custom code 而合併互不相容的候選能力。

## 4.1 Candidate Search Order

每個 requirement 依下列順序搜尋與評估：

```text
official standard capability
        ↓
mature solution with project configuration
        ↓
composition of mature solutions through stable standard interfaces
        ↓
thin adapter for mechanical boundary mismatch
        ↓
minimum custom behavior gap
```

若第一個合理成熟方案已為 `Fully Covered`，且查證後沒有同等合理的替代方案，不必為了形式建立虛構候選；但 assessment 必須記錄搜尋過的官方 capability domain、package family 或 alternative category。

候選搜尋不要求列出所有可能套件，只要求涵蓋與 target version／platform 相符、維護狀態合理且能實際支持 requirement 的成熟選項。停止搜尋的理由必須可追溯。

## 4.2 Candidate Comparison

同一 requirement 有兩個以上合理候選時，使用下列比較欄位：

| Criterion | Candidate A | Candidate B |
|---|---|---|
| Exact Version / Platform | | |
| Coverage Status | | |
| Covered Requirement Fragments | | |
| Known Constraints | | |
| Required Configuration | | |
| Composition Dependencies | | |
| Interface Compatibility | | |
| Missing Evidence | | |
| Uncovered Gap | | |
| Maintenance / Support Status | | |

04 的 comparison conclusion 只描述各候選的 coverage、constraints、evidence quality 與 minimum gaps，不決定最終 solution。05 必須基於整體 system decomposition、ownership、cross-subsystem contracts 與 operational flows 做 architecture selection。

不得把 Candidate A 的某項能力與 Candidate B 的另一項能力合併描述為任一候選自身具備的能力。若預期兩者共同使用，必須建立明確的 composition candidate。

## 4.3 Composition Coverage

多個成熟方案組合後可以形成一個 composition candidate。只有同時符合下列條件，composition 才可以被評估為 `Fully Covered`：

- 各 component 的 exact version／platform 與 individual coverage 已查證；
- 透過公開、穩定且 semantics 相容的 interface 連接；
- producer／consumer responsibility 與 data ownership 可清楚界定；
- 不需要 custom policy 才能決定 requirement 的核心 behavior；
- 組合後涵蓋 requirement 的全部 fragments；
- composition dependency、configuration 與 integration risk 已記入 constraints／Missing Evidence。

若 interface compatibility、lifecycle、data semantic、validity propagation 或 failure handling 尚未確認，應記錄為 `Composition Gap` 或 `Evidence Gap`，不得只將各套件 feature lists 相加而判定 `Fully Covered`。

## 4.4 Thin-adapter Boundary

Thin adapter 只處理不改變 product／architecture policy 的機械性邊界差異，例如：

- message／data format conversion；
- unit conversion；
- frame name 或 field mapping；
- 小範圍 protocol wrapping；
- 不改變 semantic 的 standard-interface adaptation。

Thin adapter 不得：

- 決定 navigation、mapping、control 或 recovery strategy；
- 判斷 system safety、operation success 或 final result；
- 成為 authoritative state、resource、command 或 policy owner；
- 補造 requirement 未定義的 behavior；
- 承擔原成熟方案欠缺的核心 capability；
- 因持續加入 policy 而實質成為新的 subsystem。

只要 adapter 需要做上述任一決策，其缺口必須重新分類為 `Custom Behavior Gap`，並交由 05／06 決定 responsibility 與 internal design。

## 4.5 Gap Classification

每個未 closure 的缺口必須使用下列一種主要分類；必要時可以列出相依的次要分類：

| Gap Type | Meaning | 04 Treatment |
|---|---|---|
| `Configuration Gap` | 成熟能力已存在，但 target project 的 parameter、resource 或 deployment configuration 尚未確立。 | 記錄所需 configuration 與 validation，不據此推導 custom behavior。 |
| `Composition Gap` | 個別成熟能力存在，但以標準介面組合後的 compatibility、lifecycle、semantic 或 failure flow 尚未 closure。 | 記錄 composition dependency 與所需 integration evidence。 |
| `Adapter Gap` | 只缺不改變核心 semantic／policy 的機械性介面轉換。 | 記錄轉換邊界、preserved semantic 與 verification obligation。 |
| `Custom Behavior Gap` | 成熟方案確實缺少 requirement 所需的核心 behavior。 | 精確描述最小 missing behavior；不在 04 決定 node、package、subsystem 或 algorithm。 |
| `Evidence Gap` | 候選方案可能已有能力，但現有 evidence 不足以可靠判斷。 | Coverage 保持 `Needs Verification`，並記錄 closure question 與 evidence action。 |

只有 `Custom Behavior Gap` 可以作為後續考慮 custom code 的依據；它仍不代表 05 必須建立新 subsystem，也不代表 06 必須建立新 component。

## 4.6 Required Minimum-gap Record

`Partially Covered`、`Not Covered` 或 `Needs Verification` 的 candidate 必須依適用情況記錄：

```text
Gap Classification: <Configuration / Composition / Adapter / Custom Behavior / Evidence Gap>
Requirement Fragment: <尚未 closure 的精確 requirement fragment>
Existing Coverage: <成熟方案已提供的能力>
Configuration Limitation: <configuration 為何已足夠、尚未確立或無法補足>
Composition Limitation: <composition 是否可行及尚缺什麼>
Minimum Missing Behavior: <最小缺失；非 Custom Behavior Gap 時可填 None>
Required Inputs: <缺口 closure 所需輸入>
Required Outputs: <缺口 closure 所需輸出>
Constraints: <version、platform、semantic、safety 或 operating constraints>
Required Verification: <官方、source、integration 或 real-hardware evidence>
Architecture Decision Needed: <交給 05 的 choice／constraint，不指定 owner 或 internal design>
```

Gap 必須直接對應 requirement fragment，不得只寫「需要客製化」、「需要整合」或「尚待處理」。若一個 broad gap 同時包含多種原因，應拆成可獨立 closure 的最小 gaps。

## 4.7 MVP Escalation

若 minimum gap 的預期成本、風險或複雜度明顯超過 v0.1 MVP 價值，04 可以依 1.4 節提出 `MVP Change Candidate`。該 candidate 不得改變目前 Coverage Status 或縮小 gap；只有上游 01–03 正式修改並核准後，才能依新的 requirement baseline 重新 assessment。

# 5. Assessment Order and Completion Rules

Reuse assessment 依成熟方案領域集中查證，以減少版本、package family 與 evidence context 的重複切換；但每個 `SYS-xxx` 仍必須獨立拆解、判定、核准與記錄。領域群組只決定工作順序，不取代 requirement-level coverage conclusion。

## 5.1 Assessment Order

Requirement assessment 依下列順序進行：

```text
Robot Description
        ↓
Perception and Odometry
        ↓
Motion and Drive
        ↓
Mapping
        ↓
Target, Resource, and Localization
        ↓
Navigation Execution
        ↓
Route-assisted Strategy
```

對應 requirements：

| Domain | Requirements |
|---|---|
| Robot Description | SYS-023 |
| Perception and Odometry | SYS-003、SYS-004、SYS-005 |
| Motion and Drive | SYS-022、SYS-026、SYS-027、SYS-028、SYS-029、SYS-030 |
| Mapping | SYS-001、SYS-002、SYS-006、SYS-007、SYS-024、SYS-034 |
| Target and Localization | SYS-008、SYS-009、SYS-032、SYS-033、SYS-010 |
| Navigation Execution | SYS-011、SYS-014、SYS-015、SYS-016、SYS-017、SYS-025 |
| Route-assisted Strategy | SYS-013、SYS-018、SYS-019、SYS-020、SYS-021 |

若 assessment evidence 顯示必須調整順序，只能為了解除明確 dependency 或共同 evidence 阻塞；不得以調整順序同時核准多個 requirements。

## 5.2 Per-requirement Workflow

一次只處理一個 `SYS-xxx`，並依序完成：

```text
restate the approved 03 requirement
        ↓
decompose it into verifiable requirement fragments
        ↓
search exact-version mature candidates
        ↓
record candidate evidence and constraints
        ↓
determine coverage and classify gaps
        ↓
identify Architecture Considerations
        ↓
obtain user approval
        ↓
write the record and update the checklist
```

不得在目前 requirement 尚未完成時，預先把後續 requirement 的 candidate、coverage、gap 或 MVP conclusion 寫入 04。共同 evidence 可以先被發現，但只能在輪到相應 requirement 時完成適用性判斷與核准。

## 5.3 Requirement-fragment Rule

每個 requirement 必須拆成可分別對照成熟能力的 fragments，並保留原始 requirement 中適用的：

- normal behavior；
- input、output 與 acceptance semantics；
- prerequisite 與 validity gate；
- alternative／not-required semantics；
- failure、cancel 與 result behavior；
- stopping 或 safety obligation；
- evidence-bound operational condition。

Coverage Status 以完整 requirement 的全部必要 fragments 為準。只有部分 fragments 被成熟方案覆蓋時，不得因主要功能名稱相符而判定 `Fully Covered`。

Fragments 只用於 assessment，不建立新的 requirement IDs，也不得把一個完整 requirement 拆成彼此獨立、可任意捨棄的需求。

## 5.4 Shared Evidence Across Requirements

同一份 official document、source、integration result 或 real-hardware result 可以支持多個 requirements，但每個 assessment record 必須分別說明：

- 支持哪一個 requirement fragment；
- evidence 的 version、scope 與 condition 是否相符；
- 不能由該 evidence 推論的內容；
- 是否仍有 requirement-specific Missing Evidence。

不得以「Nav2 支援導航」、「SLAM Toolbox 支援建圖」或「ros2_control 支援底盤」等 package-level statement 一次關閉多個 requirements。若共同 evidence 後續被推翻或條件改變，所有引用該 evidence 的 requirement records 都必須重新開啟並檢查。

## 5.5 Completion with Needs Verification

Coverage Status 為 `Needs Verification` 的 requirement assessment 可以標記 checklist 完成，但只表示「目前 evidence gap 已被完整記錄」，不表示成熟方案 coverage 已 closure。

必須同時符合：

- 未決問題具體且可回答；
- 缺少的 evidence type、version、scope 與取得方式明確；
- 下一個 verification action 可執行；
- downstream 風險與不可假設的內容明確；
- 05 不會把它誤讀為已確認 capability；
- 沒有未揭露的 requirement fragment。

若 `Needs Verification` 會阻止任何合理 architecture choice，04 final review 必須將其列為進入 05 前的阻塞；若 05 可以保留明確 constraint 或 choice，則可作為未 closure verification obligation handoff，但不得被隱藏。

## 5.6 Per-requirement Definition of Done

每個 requirement assessment 只有在下列條件全部成立時才可標記完成：

- Requirement ID、名稱與 Required Behavior／Constraint 保持 03 原始語意。
- 所有必要 requirement fragments 已列出，沒有遺漏 failure、safety、cancel、validity 或 acceptance semantics。
- 合理的 mature-candidate 搜尋範圍與停止理由明確。
- 每個 candidate 的 exact version／platform 明確；無法確認時使用 `Needs Verification`。
- Coverage Status、Covered Scope、Known Constraints 與 Uncovered Gap 已核准。
- Coverage Status 與 project Missing Evidence 已分開記錄。
- 每個未 closure fragment 都有適當 gap classification 與 minimum-gap record。
- Evidence citation 記錄 type、source、version／revision、platform、scope、limitations 與 date。
- Architecture Considerations 只提出交給 05 的 choice／constraint，沒有先配置 owner 或 internal design。
- `MVP Change Candidate` 為 `None`，或已依 1.4 節完成上游處理並重新 assessment。
- 多候選未被混合為不存在的完整方案；需要時已有 Candidate Comparison。
- Assessment conclusion 已取得使用者核准、寫入本文件並更新 checklist。
- Markdown、traceability 與 GitNexus 變更範圍檢查通過。

## 5.7 Domain Transition Gate

只有目前 domain 的 requirements 均已有已核准 records，或未完成項目已明確標記 `[!]` 且不會污染後續 assessment，才能進入下一個 domain。Domain transition 不代表共同 candidate 已被 05 選用，只表示該領域的 requirement-level reuse evidence 已形成可審查 baseline。

# 6. Requirement Assessments

## 6.1 Robot Description

## SYS-023 Robot Description

### Required Behavior / Constraint

系統必須提供機器人幾何、座標系與關節定義，供感知、定位、建圖與導航使用。必要 fragments 為 geometry definition、frame definition、joint definition，以及 downstream consumers 可取得語意正確的模型與 transforms。

### Candidate Assessment: URDF + robot_state_publisher

| Field | Assessment |
|---|---|
| Candidate Mature Solution | URDF + `robot_state_publisher`；Xacro 作為可選的模型維護工具 |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；研究時 Jazzy metadata：`urdf` 2.10.1-2、`robot_state_publisher` 3.3.4-1、`xacro` 2.1.1-1；部署版本仍須確認 |
| Coverage Status | `Fully Covered`（成熟方案 capability 層級） |
| Covered Scope | URDF 表達 geometry、links 與 joints；`robot_state_publisher` 依模型及 `JointState` 發布 fixed／movable transforms；Xacro 可維護並產生 URDF |
| Known Constraints | 真實尺寸、collision geometry、frame semantics、joint data、sensor mounting 與 authoritative joint-state source 仍是 project-owned data／configuration；`joint_state_publisher` 不得被視為實機真實回授 |
| Uncovered Gap | Custom Behavior Gap：`None`；Configuration／Data Asset 與 Evidence Gaps 尚存 |
| Evidence | ROS 2 Jazzy 官方 URDF、`robot_state_publisher`、Xacro 文件及 Jazzy release metadata；本地 `ref/FIH_AMR_ROBOT_V2.0_0731` 含 84 links、83 joints、底盤／輪／IMU／LiDAR frames 與 meshes；詳見 `research/sys-023-robot-description.md` |
| Missing Evidence | Target image 實際版本；install／parse；TF tree 結構、語意與唯一 publisher；sensor `frame_id`；downstream integration；實機尺寸與 mounting validation |

### Minimum-gap Record

```text
Gap Classification: Configuration Gap / Evidence Gap
Requirement Fragment: 提供本 AMR 語意與幾何正確、可供各 downstream consumers 使用的 model 與 transforms。
Existing Coverage: URDF/Xacro representation 與 robot_state_publisher runtime transform publishing。
Configuration Limitation: 成熟套件無法提供 project-specific geometry、frames、joints、meshes 與 mounting data。
Composition Limitation: 必須提供正確模型、單一 TF ownership 與 authoritative JointState source，並完成 consumer integration。
Minimum Missing Behavior: None
Required Inputs: 已核准 geometry、frame／joint semantics、sensor mounting 與 joint-state authority。
Required Outputs: 可安裝的 robot description、robot_description，以及 consumers 所需的有效 TF segments。
Constraints: 不得產生 duplicate TF owner；不得以 joint_state_publisher 假造實機回授。
Required Verification: Target-version、parse／install、TF、sensor-frame、integration 與 real-hardware geometry validation。
Architecture Decision Needed: 05 決定 authoritative model owner、TF ownership boundary 與 movable-joint feedback responsibility。
```

### Architecture Considerations

05 應從成熟的 URDF／`robot_state_publisher` 能力出發，決定 authoritative description owner、runtime publication 與 TF／joint-state ownership；不需要為 SYS-023 建立 custom model framework。

### MVP Change Candidate

`None`。成熟方案能力足以支持 SYS-023，不需要為 MVP 弱化 requirement。

## 6.2 Perception and Odometry

## SYS-003 LiDAR Perception

### Required Behavior / Constraint

系統必須提供 LiDAR 掃描資料供建圖、定位與導航使用。必要 fragments 為取得平面掃描量測、使用具有 time／frame／range semantics 的 ROS 2 標準表示、保留各 LiDAR source identity，以及實際 TF、QoS、時序、validity 與資料品質可供 downstream operations 使用。

### Candidate Assessment: sick_scan_xd + LaserScan

| Field | Assessment |
|---|---|
| Candidate Mature Solution | 每具 picoScan 使用獨立 `sick_scan_xd` instance，發布 `sensor_msgs/msg/LaserScan` |
| Exact Version / Platform | 本地參考 `sick_scan_xd` 3.9.0、revision `a562c5d098de21f6284359f4dfea97e93bd2b4d5`；目標 ROS 2 Jazzy／Ubuntu 24.04，target image artifact 尚待確認 |
| Coverage Status | `Fully Covered`（成熟方案 capability 層級） |
| Covered Scope | picoScan100／150 ROS 2 driver、LaserScan 發布，以及以不同 IP、UDP port、node、topic 與 frame identity 支援多裝置獨立來源 |
| Known Constraints | 每具裝置需獨立 network／ROS identity；full-frame、layer／echo、frame suffix、QoS、UDP loss 與 scan validity 必須依配置及實機確認 |
| Uncovered Gap | Custom Behavior Gap：`None`；Configuration Gap 與 Evidence Gap 尚存 |
| Evidence | ROS 2 Jazzy `sensor_msgs/msg/LaserScan` 官方介面、SICK 官方 `sick_scan_xd` 與本地 3.9.0 reference；詳見 `research/sys-003-lidar-perception.md` |
| Missing Evidence | Target artifact、雙 LiDAR 同時運行、topic／frame／QoS、TF、measurement validity、failure behavior、downstream integration 與實機資料品質 |

### Minimum-gap Record

```text
Gap Classification: Configuration Gap / Evidence Gap
Requirement Fragment: 兩具 LiDAR 的獨立 scans 必須以正確 identity、semantics、validity 與品質供 Mapping、Localization、Navigation 使用。
Existing Coverage: sick_scan_xd 提供 picoScan ROS 2 driver 與標準 LaserScan output。
Configuration Limitation: 必須確立各裝置 IP、UDP port、node、topic、frame、echo/layer 與 QoS。
Composition Limitation: 各 downstream consumer 對多來源的原生能力與使用方式尚待各自查證。
Minimum Missing Behavior: None
Required Inputs: 兩具 sensor identity、network、scan mode、frame mounting 與 consumer requirements。
Required Outputs: 兩個具有獨立 identity 與 validity evidence 的 LaserScan sources。
Constraints: Independent-source-first；非必要不得融合；不得假設 driver active 等於 scan valid。
Required Verification: Jazzy build/install、雙裝置 runtime、received-message semantics、TF、QoS、failure isolation、downstream integration 與 real-hardware quality。
Architecture Decision Needed: 05 決定各 source ownership、validity contract 與 downstream relationships，不預設 merged scan。
```

### Selected LaserScan Merge Candidate

ROS 2 Jazzy `dual_laser_merger` 0.3.1 定案為 RF2O 上游的成熟 merge 方案。它可在兩個 `LaserScan` inputs 具有正確 TF、近似時間同步與相容 QoS 時，透過 PointCloud2／PCL 中介處理產生供 RF2O 使用的單一 merged `LaserScan`。

此選擇不改變 independent-source-first baseline：兩個原始 `LaserScan` 仍各自保留，`dual_laser_merger` 只為需要單一 scan 的 RF2O 提供衍生輸入。尚待 closure 的內容為：

- 兩個 input topics、frames、QoS 與 approximate-time synchronization tolerance；
- output frame、角度範圍、解析度與 RF2O input remapping；
- 遮蔽、重疊取值、CPU、latency、單一來源 dropout 與 failure semantics；
- Jazzy target platform integration 與實機結果。

### Architecture Considerations

05 應保留每具 LiDAR 的 source identity、frame、validity 與唯一 software ownership。Mapping、Localization、Navigation 是否直接使用多個 sources，必須依各 consumer 的成熟能力與 evidence 決定，不由 SYS-003 預設融合資料路徑。

### MVP Change Candidate

`None`。成熟 driver 能提供獨立標準 scans；目前不需要弱化 SYS-003，也不需要為 MVP 導入 merge。

## SYS-004 IMU Perception

### Required Behavior / Constraint

系統必須提供 IMU 量測資料供定位使用。必要 fragments 為取得有效 IMU measurements、使用 ROS 2 標準表示、維持正確 unit／axis／frame／time semantics，並揭露足以讓 localization 正確使用或拒絕資料的限制與 validity evidence。

### Candidate Assessment: tdk_ros2_imu

| Field | Assessment |
|---|---|
| Candidate Mature Solution | `tdk_ros2_imu`，TDK IIM-42652 HandBoard IMU V1 ROS 2 serial driver |
| Exact Version / Platform | Package 0.1.0；inspected workspace revision `f05d8cbb43a812e39c0b038c56baee8ada699b2c`；ROS 2 target dependencies 尚未 pin |
| Coverage Status | `Fully Covered`（reusable-capability 層級） |
| Covered Scope | USB serial packet acquisition、header／XOR checksum validation、SI unit conversion，以及以 sensor-data QoS 發布 configurable-frame `sensor_msgs/msg/Imu` |
| Known Constraints | 使用 host ROS publish time；保留 device axes；covariance 為 unknown；orientation 以上電姿態為基準且無磁力計造成 yaw drift；checksum warning 與 fatal serial failure 不構成獨立 measurement-validity interface |
| Uncovered Gap | Custom Behavior Gap：`None`；Configuration Gap 與 Evidence Gap 尚存 |
| Evidence | 使用者確認套件已驗證可直接套用；本地 package 0.1.0 source／tests／device guide；ROS 2 Jazzy `sensor_msgs/msg/Imu` 官方語意；詳見 `research/sys-004-imu-perception.md` |
| Missing Evidence | 既有驗證紀錄的環境與範圍、target Jazzy dependencies、acquisition-time error／jitter、mounting／axis／TF、covariance policy、calibration／bias／noise、QoS、failure propagation、localization configuration 與實機定位貢獻 |

### Minimum-gap Record

```text
Gap Classification: Configuration Gap / Evidence Gap
Requirement Fragment: IMU measurements 必須具有 localization 可正確解讀的 unit、axis、frame、time、uncertainty 與 validity semantics。
Existing Coverage: tdk_ros2_imu 讀取、驗證、轉換並發布標準 Imu message；使用者確認套件可直接套用。
Configuration Limitation: 必須確立 port、frame/TF、localization 使用欄位、covariance policy 與 QoS。
Composition Limitation: Localization 是否使用 orientation、angular velocity、linear acceleration 或其子集，須依 yaw drift、timestamp 與 uncertainty evidence 決定。
Minimum Missing Behavior: None
Required Inputs: 實體 mounting、frame semantics、定位需求、noise/bias 與 timing evidence。
Required Outputs: 具有已知限制與正確 configuration 的 sensor_msgs/msg/Imu stream。
Constraints: Host publish time 非 acquisition time；device axes 不自動轉換；zero covariance 表示 unknown；yaw 非 absolute heading。
Required Verification: Target Jazzy runtime、axis/TF、units、timestamp jitter、covariance handling、calibration、failure behavior、QoS、localization integration 與 real hardware。
Architecture Decision Needed: 05 決定 IMU measurement validity boundary 與 localization relationship；不假定所有 Imu fields 都應被融合。
```

### Architecture Considerations

05 應將 `tdk_ros2_imu` 視為可直接重用的 measurement provider，同時保留 host timestamp、axis／frame、unknown covariance、power-on-relative orientation 與 yaw drift constraints。使用者確認的套件驗證不等同 downstream localization 已完成驗證。

### MVP Change Candidate

`None`。現有 reusable package 能提供 SYS-004 所需 IMU measurements，不需要為 MVP 弱化 requirement。

## SYS-005 System Odometry

### Required Behavior / Constraint

系統必須使用 wheel odometry、RF2O odometry 與 IMU 資訊，透過成熟狀態估測方案產生可供定位、建圖與導航使用的平面里程資訊。輸入異常或逾時時，可以依狀態估測方案的原生行為，使用其餘有效量測或 prediction 持續產生里程資訊。

### Candidate Assessment: wheel odometry + RF2O + IMU + robot_localization EKF

| Field | Assessment |
|---|---|
| Candidate Mature Solution | Wheel odometry producer + `dual_laser_merger` + `rf2o_laser_odometry` + `tdk_ros2_imu`，透過 `robot_localization` EKF 融合；RF2O 使用 merged `LaserScan` 作為單一 scan input |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；`robot_localization` Jazzy 3.8.3；`dual_laser_merger` Jazzy 0.3.1；本地 `rf2o_laser_odometry` 0.1.0、revision `b38c68e46387b98845ecbfeb6660292f967a00d3`；`tdk_ros2_imu` 0.1.0；wheel odometry producer exact package／revision 尚待確認 |
| Coverage Status | `Fully Covered`（成熟方案 capability 層級） |
| Covered Scope | `robot_localization` 可透過標準 `nav_msgs/msg/Odometry` 與 `sensor_msgs/msg/Imu` inputs 融合多個來源、拒絕超過設定 threshold 的量測，並在 sensor timeout 時以其餘有效量測或 prediction 持續發布 system odometry；可配置為唯一 `odom -> base_footprint` publisher；RF2O 可從一個 merged `LaserScan` 估測 planar laser odometry |
| Known Constraints | RF2O 原生只訂閱一個 `LaserScan`，不負責雙 scan merge；其他 odometry TF publishers 必須停用；prediction 會延續先前狀態且 uncertainty 隨時間累積；三路 input fields、frames、timestamps、covariances 與 TF-at-measurement semantics 必須一致且可驗證 |
| Uncovered Gap | Custom Behavior Gap：`None`；LaserScan merge 與 EKF 的 configuration／composition 及 evidence gaps 尚存 |
| Evidence | ROS 2 Jazzy `robot_localization` 官方文件與 ROS Index；RF2O 0.1.0 source 顯示單一 `laser_scan_topic`、單一 subscription 與 scan-stamped odometry；本地 wheel odometry、TDK IMU source review；詳見 `research/sys-005-system-odometry.md` |
| Missing Evidence | Wheel odometry exact candidate；`dual_laser_merger` 同步／TF／重採樣／遮蔽／latency／dropout；三路 covariance、field selection、timestamp age、TF、freshness；EKF convergence、failure propagation、target-platform integration 與實機結果 |

### Minimum-gap Record

```text
Gap Classification: Configuration Gap / Composition Gap / Evidence Gap
Requirement Fragment: 成熟方案 capability 已完整覆蓋；尚須建立本專案可用的三來源 composition 與 configuration evidence。
Existing Coverage: robot_localization 提供多來源 EKF fusion、measurement rejection、sensor-timeout prediction、filtered odometry 與可配置的 odom -> base_footprint publication；RF2O 提供單一 LaserScan-derived odometry。
Configuration Limitation: EKF planar fields、frames、TF publication、frequency、timeouts、queues、rejection thresholds 與各 measurement covariance 尚未確立。
Composition Limitation: merged LaserScan -> RF2O -> EKF 與 wheel odometry／IMU 的 time、frame、covariance、source dropout 與 prediction behavior 仍需 closure。
Minimum Missing Behavior: None
Required Inputs: Wheel odometry、merged-LaserScan-derived RF2O odometry、IMU，以及其 frame、timestamp 與 covariance configuration。
Required Outputs: Authoritative system odometry 與唯一 odom -> base_footprint transform。
Constraints: 允許依 robot_localization 原生行為使用其餘有效量測或 prediction 持續輸出；EKF 必須是唯一 odom -> base_footprint publisher。
Required Verification: Exact-version configuration review；timestamp／TF／covariance measurements；單一路與多路 input dropout；prediction drift／uncertainty；target-platform integration 與 real-hardware motion tests。
Architecture Decision Needed: 05 決定 authoritative output／TF relationship、merged LaserScan dependency及 source dropout／prediction 對 downstream 的 system-wide contract；04 不指定 internal algorithm。
```

### Architecture Considerations

05 應以 `dual_laser_merger -> merged LaserScan -> RF2O odometry`、wheel odometry 與 IMU 進入 EKF 作為已核准的 composition constraint，並維持 EKF 對 system odometry 與 `odom -> base_footprint` 的唯一發布關係。05 應明確記錄 input 異常或逾時時，允許 `robot_localization` 依原生行為使用其餘有效量測或 prediction 持續輸出；merge 的參數與 failure semantics 留待後續 architecture／subsystem design closure。

### MVP Change Candidate

`None`。成熟方案 capability 已覆蓋核准的 SYS-005 行為。

## 6.3 Motion and Drive

## SYS-022 Base Motion Control

### Required Behavior / Constraint

系統必須接收底盤速度命令，依差速輪運動學轉換為左右輪命令，並透過底盤硬體介面控制實體底盤完成移動。SYS-022 只評估基本 command-to-wheel-control behavior；故障、command timeout、limits、feedback validity、安全啟停與 shutdown configuration 分別由 SYS-026–031 評估。

### Candidate Assessment: ros2_control + diff_drive_controller

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` + `ros2_controllers/diff_drive_controller` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；2026-08-13 Jazzy rosdistro metadata：`ros2_control` 4.47.0-1、`ros2_controllers` 4.42.1-1；target image installed versions 尚待確認 |
| Coverage Status | `Fully Covered`（成熟 controller capability 層級） |
| Covered Scope | 接收 `geometry_msgs/msg/TwistStamped` body velocity command；使用 `linear.x`、`angular.z`、wheel separation 與 wheel radius 執行 differential-drive inverse kinematics；輸出左右 wheel joint velocity commands 至標準 ros2_control hardware command interfaces |
| Known Constraints | 需要正確的 wheel joint names、geometry、directions、units 與有效 velocity command interfaces；實體移動依賴 downstream M1 hardware interface 與 drive readiness；controller 的 odometry／TF 能力不取得 SYS-005 system odometry ownership |
| Uncovered Gap | Custom Behavior Gap：`None`；Configuration Gap、hardware-interface dependency 與 Evidence Gap 尚存 |
| Evidence | ROS 2 Jazzy `diff_drive_controller` user／interface documentation、mobile robot kinematics、ros2_control control-loop boundary與 Jazzy rosdistro release metadata；本地 M1 design baseline 與 legacy controller 僅作 project boundary reference；詳見 `research/sys-022-base-motion-control.md` |
| Missing Evidence | Target installed versions、plugin discovery、controller configuration／activation、topic／remap／QoS、wheel interfaces、geometry／sign／unit、M1 integration，以及實機 forward／reverse／rotation／curved motion |

### Minimum-gap Record

```text
Gap Classification: Configuration Gap / Evidence Gap
Requirement Fragment: 成熟 controller capability 已完整覆蓋；尚須建立 project configuration、M1 hardware composition 與實機移動 evidence。
Existing Coverage: diff_drive_controller 接收 TwistStamped body command、執行差速輪 inverse kinematics，並輸出 wheel velocity commands；ros2_control 提供標準 controller-to-hardware control-loop boundary。
Configuration Limitation: Wheel joints、radius、separation、direction／correction multipliers、topic/remap、QoS、update rate、feedback mode 與 lifecycle activation 尚未確立。
Composition Limitation: M1 hardware component 必須 export／consume 正確 wheel velocity command interfaces，並提供設定所需的 measured wheel state interfaces。
Minimum Missing Behavior: None
Required Inputs: TwistStamped body velocity command、wheel geometry／joint configuration，以及可運作的 M1 ros2_control hardware interfaces。
Required Outputs: 具有正確方向、尺度與單位的左右 wheel velocity commands，並使實體底盤依命令移動。
Constraints: 不由 SYS-022 重新定義 fault、timeout、limits、feedback validity、安全啟停或 shutdown behavior；不得由 diff_drive_controller 取得 authoritative odom -> base_footprint ownership。
Required Verification: Exact installed version、controller active/interfaces claimed、command-to-wheel calculation、zero command、M1 integration，以及實機 forward／reverse／rotation／curved motion。
Architecture Decision Needed: 05 決定標準 controller／hardware composition 與 ownership boundary；保留 TwistStamped canonical command 和 SYS-005 system-odometry ownership。
```

### Architecture Considerations

05 應以 `TwistStamped -> diff_drive_controller -> wheel velocity command interfaces -> M1 ros2_control hardware interface` 作為成熟 composition 候選，保留 controller 與 project-specific device boundary。M1 protocol、driver readiness 與實體故障行為不是取代成熟差速控制器的理由，應由其各自 requirements 與後續 design 處理。

### MVP Change Candidate

`None`。成熟方案 capability 已完整覆蓋 SYS-022，不需要為 MVP 自訂差速運動學或弱化 requirement。

## SYS-026 Base Fault Handling

### Required Behavior / Constraint

當底盤 hardware interface 回傳 `ERROR` 時，系統必須停止使用該硬體介面的 controller，並使其錯誤狀態可被觀察。SYS-026 不再要求解析特定 M1 fault、主動執行 vendor stop command或確認實體底盤已停止。

### Candidate Assessment: ros2_control hardware-error handling

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` Controller Manager 與 `hardware_interface::SystemInterface` error contract |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；2026-08-13 Jazzy rosdistro metadata：`ros2_control` 4.47.0-1；target image installed version 尚待確認 |
| Coverage Status | `Fully Covered`（成熟 framework capability 層級） |
| Covered Scope | Hardware `read()`／`write()` 可回傳 `return_type::ERROR`；Controller Manager 停止所有使用該 hardware command／state interfaces 的 controllers；controller／hardware lifecycle state change 可由 `~/activity` 觀察 |
| Known Constraints | Hardware plugin 仍須決定何時回傳 `ERROR`；controller stopped 不保證實體底盤已停止；`~/activity` 表示 managed state，不提供 vendor-specific fault details |
| Uncovered Gap | Custom Behavior Gap：`None`；Configuration Gap 與 Evidence Gap 尚存 |
| Evidence | ROS 2 Jazzy `SystemInterface` API 與 Controller Manager hardware-error behavior；詳見 `research/sys-026-base-fault-handling.md` |
| Missing Evidence | Target installed version；hardware `ERROR` injection；受影響 controllers 實際停止；`~/activity` lifecycle/error state 可觀察性，以及 target composition runtime evidence |

### Minimum-gap Record

```text
Gap Classification: Configuration Gap / Evidence Gap
Requirement Fragment: 成熟 framework capability 已完整覆蓋；尚須確認 target composition 的 ERROR propagation、controller stop 與state observability。
Existing Coverage: ros2_control 提供 hardware ERROR return、dependent-controller stop與lifecycle state visibility。
Configuration Limitation: 必須確立 hardware/controller lifecycle composition，以及 `~/activity` 的觀察方式與retention expectations。
Composition Limitation: M1 hardware plugin 必須將其自行判定的硬體問題映射為 ros2_control `ERROR`；SYS-026 不規範該判定的 vendor-specific細節。
Minimum Missing Behavior: None
Required Inputs: Hardware `read()`／`write()` return status。
Required Outputs: 停止使用該 hardware interfaces 的 controllers，以及可觀察的controller／hardware error lifecycle state。
Constraints: Controller stopped 不得宣稱 physical base stopped；不由 SYS-026 要求 M1 alarm interpretation、JG0、zero-RPM confirmation、fault details或recovery policy。
Required Verification: Target installed version、hardware ERROR injection、dependent-controller stop與`~/activity` state observation。
Architecture Decision Needed: 05 定義 generic hardware ERROR propagation與system-wide observation relationship，不擴張回vendor-specific physical-stop contract。
```

### Architecture Considerations

05 應直接採用 ros2_control 的 hardware `ERROR` propagation：M1 hardware interface 回傳 `ERROR` 後，由 Controller Manager 停止使用該硬體介面的 controllers，並透過managed lifecycle state提供可觀察性。05 不得由 SYS-026 反向推導 M1-specific fault framework或physical-stop confirmation。

### MVP Change Candidate

`None`。核准後的簡化 requirement 已由成熟 framework capability 完整覆蓋。

## SYS-027 Motion-command Timeout

### Required Behavior / Constraint

底盤執行運動期間，若系統未在設定之逾時時間內收到有效的新速度命令，必須使底盤停止；逾時值與停止行為必須經整合及實機驗證。必要 fragments 為判斷速度命令 freshness、逾時後產生停止用命令，以及以整合與實機 evidence 確認逾時設定和實際停止結果。

### Candidate Assessment: ros2_control + diff_drive_controller command timeout

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` + `ros2_controllers/diff_drive_controller` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Jazzy rosdistro metadata：`ros2_controllers` 4.42.1-1；target image installed version 尚待確認 |
| Coverage Status | `Fully Covered`（成熟 controller capability 層級，適用於 non-chained `TwistStamped` input 與非零 `cmd_vel_timeout`） |
| Covered Scope | 非 chained 模式依 `TwistStamped.header.stamp` 判斷 command age；超過非零 `cmd_vel_timeout` 後將 linear／angular reference 設為零，經已設定的 velocity／acceleration／jerk limits 與差速運動學後寫入左右輪 velocity command interfaces |
| Known Constraints | `cmd_vel_timeout=0.0` 會停用 timeout；controller 必須 active 且 update loop 持續執行；Jazzy 4.42.1 的 topic input 固定為 `TwistStamped`；chained mode 不使用 subscriber command-age timeout；limiters 可能使命令逐步減速而非單一 update 直接歸零 |
| Uncovered Gap | Custom Behavior Gap：`None`；Configuration／Composition 與 Evidence Gaps 尚存 |
| Evidence | ROS 2 Jazzy `diff_drive_controller` user documentation、migration guide，以及 `ros2_controllers` 4.42.1 tagged source、parameter definition 與 tests；詳見 `research/sys-027-motion-command-timeout.md` |
| Missing Evidence | Target installed version；timeout、timestamp／clock 與 limiter configuration；controller update execution；hardware command delivery；wheel／body feedback；最壞停止時間、停止距離及實體底盤停止結果 |

### Minimum-gap Record

```text
Gap Classification: Configuration Gap / Composition Gap / Evidence Gap
Requirement Fragment: 成熟 controller capability 已覆蓋 command freshness timeout 與停止命令；尚須確認 target composition 的設定、命令傳遞與實體停止結果。
Existing Coverage: 非 chained diff_drive_controller 依 TwistStamped timestamp 判斷 command age，逾時後將 body reference 設為零，並將經 limiters 與差速運動學處理的 wheel velocity commands 寫入 ros2_control interfaces。
Configuration Limitation: 必須使用非零 cmd_vel_timeout，建立 clock／timestamp contract，並決定 timeout 後的 immediate-zero 或 limited-deceleration profile。
Composition Limitation: Native timeout 適用於 non-chained topic path；controller update loop、hardware interface 與 motor drive 必須在 command source 中斷時仍能傳遞及執行停止命令。
Minimum Missing Behavior: None
Required Inputs: 有效且 clock-consistent 的 TwistStamped commands、非零 timeout，以及選定的 velocity／acceleration／jerk limits。
Required Outputs: 逾時後的零 body reference 與相應左右輪停止命令，最終使實體底盤停止。
Constraints: Chained mode 必須重新配置 command-freshness owner 並重做 coverage assessment；controller zero／ramp command 不得被當作 physical stop 已證明。
Required Verification: Exact installed version、fresh／stale command behavior、timeout detection timing、wheel command 與 hardware write、wheel／body feedback、最壞停止時間及停止距離之整合與實機測試。
Architecture Decision Needed: 05 保留 non-chained TwistStamped timeout path、非零 timeout constraint 與實體停止 verification obligation；若選擇 chained mode，必須重新分配 freshness responsibility 並回到 04 重評。
```

### Architecture Considerations

05 應以 non-chained `TwistStamped -> diff_drive_controller` 與非零 `cmd_vel_timeout` 作為使用原生 timeout capability 的 composition constraint。逾時後的 reference 歸零可由已設定的 limiters 形成受控減速，但 controller command 不代表實體底盤已停止；hardware delivery、wheel／body feedback、停止時間與停止距離必須保留為 integration／real-hardware verification obligations。若 05 改採 chained mode，必須明確重新分配 command-freshness ownership，並重新開啟 SYS-027 assessment。

### MVP Change Candidate

`None`。成熟 controller capability 已覆蓋 SYS-027，不需要新增 custom watchdog 或弱化 requirement。

## SYS-028 Base Motion Limits

### Required Behavior / Constraint

系統必須將 AMR 的直線與旋轉速度，以及相應的加速與減速，限制於設定之 operational limits；限制值必須依操作需求選定，並於部署前完成整合及實機驗證。必要 fragments 為 linear／angular velocity limits、各方向的 acceleration／deceleration limits、operational value selection，以及 integration／real-hardware evidence。

### Candidate Assessment: diff_drive_controller body-motion limiters

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_controllers/diff_drive_controller` built-in linear／angular `SpeedLimiter` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；`ros2_controllers` 4.42.1；target image installed version 尚待確認 |
| Coverage Status | `Fully Covered`（成熟 controller capability 層級） |
| Covered Scope | 分別限制 `linear.x` 與 `angular.z` 的正／反向 velocity，以及正／反向 acceleration／deceleration；限制後才執行 differential-drive inverse kinematics |
| Known Constraints | 所需限制值預設為 `.NAN`，代表未啟用，必須明確配置；limiter 依賴前兩次已限制命令與 controller update period；controller 必須 configured／active 且 update loop 正常執行；jerk limiting 可用但不是 SYS-028 requirement |
| Uncovered Gap | Custom Behavior Gap：`None`；Configuration Gap 與 Evidence Gap 尚存 |
| Evidence | `ros2_controllers` 4.42.1 tagged `diff_drive_controller` source、generated parameter definition、`SpeedLimiter` wrapper、官方 tests，以及 ROS 2 Jazzy `control_toolbox::RateLimiter` API；詳見 `research/sys-028-base-motion-limits.md` |
| Missing Evidence | Operational limit 數值；target installed version；參數實際載入；update timing；正／反向速度與加減速 integration behavior；實體 AMR body motion evidence |

### Minimum-gap Record

```text
Gap Classification: Configuration Gap / Evidence Gap
Requirement Fragment: 成熟 controller capability 已完整覆蓋；尚須選定並驗證 AMR body-domain operational limits。
Existing Coverage: diff_drive_controller 對 linear.x 與 angular.z 分別提供正／反向 velocity、acceleration 與 deceleration limiting，並在 inverse kinematics 前套用。
Configuration Limitation: 必須為 linear.x 與 angular.z 明確設定 finite min/max velocity，以及正／反向 acceleration/deceleration values；.NAN 表示相應限制未啟用。
Composition Limitation: 無額外 Composition Gap；沿用 SYS-022 已選定的 diff_drive_controller composition。
Minimum Missing Behavior: None
Required Inputs: 依操作需求核准的 AMR 直線／旋轉速度與正／反向加減速度 limits。
Required Outputs: 經 operational limits 約束的 AMR body velocity command，再轉換為左右輪命令。
Constraints: Controller 必須 active 且 update period 有效；wheel speed 與 motor RPM 只作 body limits 的下游可行性與配置檢查，不是 SYS-028 的獨立 fragments；不得把 command shaping 宣稱為 certified safety function。
Required Verification: Exact installed version、parameter-load evidence、positive／negative linear／angular steps、acceleration／deceleration、direction reversal、update timing，以及實體 AMR body velocity／acceleration measurements。
Architecture Decision Needed: 05 保留 body-domain operational-limit contract與下游 feasibility relationship；限制值由 configuration、integration 及實機 evidence 確立，不在 architecture 文件虛構。
```

### Architecture Considerations

05 應以 `diff_drive_controller` 的 body-domain limiters 作為 SYS-028 的成熟能力，並把 operational values 視為 evidence-bound configuration。Wheel geometry、wheel speed 與 motor RPM 必須用來確認核准的 body limits 可被實體底盤實現，但它們是下游推導與裝置約束，不重新成為 SYS-028 的 requirement fragments，也不據此新增 custom limiter。

### MVP Change Candidate

`None`。成熟 controller capability 已完整覆蓋 SYS-028，不需要新增 velocity-smoother／limiter node 或弱化 requirement。

## SYS-029 Base State Feedback

### Required Behavior / Constraint

系統必須提供由馬達驅動器有效回授取得的左右輪位置與速度狀態，供里程估測、控制與診斷使用；無有效回授時，不得以命令值取代量測狀態，並必須將狀態視為不可用或故障。必要 fragments 為 measured position／velocity acquisition、validity、standard consumption／observation、no-command-substitution，以及 invalid-state propagation。

### Candidate Assessment: ros2_control measured wheel-state path

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` `SystemInterface` state interfaces + `ros2_controllers/diff_drive_controller` closed-loop feedback + `joint_state_broadcaster` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；`ros2_control` 4.47.0；`ros2_controllers` 4.42.1；target image installed versions 尚待確認 |
| Coverage Status | `Partially Covered` |
| Covered Scope | Framework 可承載左右輪 `position`／`velocity` state interfaces；`diff_drive_controller` closed-loop 模式使用 wheel position 或 velocity feedback；standard broadcaster 可發布 states；hardware cycle 可用 `ERROR` 表達失敗 |
| Known Constraints | `open_loop=true` 不使用外部 wheel state interfaces，而以 command 計算 odometry，因此不符合 SYS-029；generic framework 不理解 M1 protocol、driver identity、raw units、position rollover 或 feedback freshness／validity |
| Uncovered Gap | Custom Behavior Gap：既有 M1Driver／M1Hardware device boundary 內的雙馬達回授取得／驗證、driver-to-wheel mapping、unit／sign conversion、continuous position tracking、cached-state availability／freshness，以及禁止 command-to-state substitution並傳遞 invalid/no-feedback `ERROR` |
| Evidence | `ros2_control` 4.47.0 tagged hardware state／read／error contracts、Controller Manager error behavior；`ros2_controllers` 4.42.1 tagged `diff_drive_controller` feedback semantics 與 `joint_state_broadcaster`；已核准 M1Driver／M1Hardware baseline；詳見 `research/sys-029-base-state-feedback.md` |
| Missing Evidence | Target installed versions；M1 state decode／validation／conversion／rollover tests；A2 cache timing／freshness；state-interface export；closed-loop consumption；broadcaster observation；invalid-feedback injection 與 target-AMR state correctness |

### Minimum-gap Record

```text
Gap Classification: Custom Behavior Gap / Configuration Gap / Composition Gap / Evidence Gap
Requirement Fragment: 從兩顆 M1 馬達取得有效 measured position／velocity，轉為左右輪 states；無有效回授時不得以 command 取代，且狀態必須視為 unavailable／fault。
Existing Coverage: ros2_control 提供標準 position／velocity state interfaces、hardware read ERROR seam、closed-loop controller consumption與standard state broadcasting。
Configuration Limitation: 必須配置 open_loop=false、選定 diff_drive_controller position或velocity feedback mode，並一致設定 joint names與interfaces。
Composition Limitation: M1Hardware exported states、closed-loop diff_drive_controller與joint_state_broadcaster必須透過標準interfaces組合；A2 cached-state timing須納入freshness validation。
Minimum Missing Behavior: 在既有M1Driver／M1Hardware內驗證雙驅動器回授、完成driver mapping與unit/sign conversion、追蹤continuous position、判斷latest state availability／freshness，且invalid／missing feedback不得更新為command-derived state並須回傳hardware ERROR。
Required Inputs: 驗證成功且包含兩顆預期driver identity之M1 measured RPM／position state，以及核准的mapping、gear ratio、sign與position scale。
Required Outputs: 左右輪measured position [rad]／velocity [rad/s] state interfaces；invalid／missing feedback時的hardware ERROR／unavailable state。
Constraints: open_loop=true禁止用於滿足SYS-029；topic收到數值不等於freshness已證明；不得由本需求新增custom feedback node、fault taxonomy或recovery framework。
Required Verification: Decode／mapping／conversion／rollover／no-cache tests、successful-cache replacement、invalid-feedback ERROR與no-command-substitution、closed-loop runtime consumption、state publication及實機方向／速度／位置一致性。
Architecture Decision Needed: 05 保留M1 measured-state authority、standard ros2_control state boundary、closed-loop-only constraint與invalid-state system relationship；不指定device-boundary internal algorithm。
```

### Architecture Considerations

05 應以 M1Driver／M1Hardware 作為 measured wheel-state 的裝置邊界，透過標準 ros2_control `position`／`velocity` state interfaces 提供給 closed-loop `diff_drive_controller` 與需要的 broadcaster／consumers。`open_loop=true` 不得用於滿足 SYS-029。無有效回授時必須沿既有 hardware `ERROR` seam 傳遞 unavailable／fault condition，但不得由 SYS-029 額外推導新的 feedback node、診斷 schema 或 recovery framework。

### MVP Change Candidate

`None`。完整 measured-feedback requirement 必須保留；custom gap 已限制在既有 M1 device adaptation boundary，不需要新增 subsystem。

## SYS-030 Safe Base Enable and Stop

### Required Behavior / Constraint

系統只有在底盤通訊正常、無馬達驅動器警報、輪端停止且驅動器已確認可運動後，才能接受非零運動命令。底盤停用或系統關閉時，必須嘗試使底盤停止、確認停止並停用馬達驅動；任一安全動作失敗不得阻止其餘安全動作之嘗試。狀態轉換等待時間與停止確認條件必須經實機驗證。

### Candidate Assessment: ros2_control lifecycle + M1 device admission／shutdown behavior

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` hardware lifecycle + Controller Manager resource／lifecycle management + `ros2_controllers/diff_drive_controller` deactivation halt behavior |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；`ros2_control` 4.47.0；`ros2_controllers` 4.42.1；target image installed versions 尚待確認 |
| Coverage Status | `Partially Covered` |
| Covered Scope | Framework 將 movement command interfaces 限制在 ACTIVE hardware，管理 controller／hardware lifecycle 與 interface claiming；`diff_drive_controller::on_deactivate()` 會 halt 並將左右輪 command interfaces 寫為零 |
| Known Constraints | Lifecycle callback 只提供執行 seam 與成功／失敗回傳；framework 不理解 M1 communication、alarm／status、RPM、SVON／SVOFF 或 JG0；controller 零命令不等於 JG0 已送達、實體已停止或 drive 已停用 |
| Uncovered Gap | Custom Behavior Gap：既有 M1Driver／M1Hardware 內的 activation admission、bounded JG0／zero-RPM／SVOFF confirmation，以及前一步失敗時仍逐一嘗試其餘 stop／confirm／disable／disconnect actions 的 bounded best-effort sequencing |
| Evidence | ROS 2 Jazzy／`ros2_control` 4.47.0 hardware lifecycle、hardware-component authoring與Controller Manager contracts；`diff_drive_controller` 4.42.1 tagged deactivation source／tests；已核准 M1Driver／M1Hardware baseline；詳見 `research/sys-030-safe-base-enable-stop.md` |
| Missing Evidence | Target installed versions；actual lifecycle composition；SVON／SVOFF poll delay／count；zero-RPM threshold／sample count／deadline；各步失敗注入；normal deactivation與system shutdown path；實體停止與drive state evidence |

### Minimum-gap Record

```text
Gap Classification: Custom Behavior Gap / Configuration Gap / Composition Gap / Evidence Gap
Requirement Fragment: 非零命令前的M1 communication／alarm／zero-RPM／motion-enabled admission，以及停用／關閉時的stop、stop confirmation、drive disable與independent action attempts。
Existing Coverage: ros2_control提供hardware/controller lifecycle與command-interface gate；diff_drive_controller停用時將wheel command interfaces歸零。
Configuration Limitation: 必須選定並實機驗證communication timeout、SVON/SVOFF poll delay/count、zero-RPM threshold／consecutive samples與total transition deadline。
Composition Limitation: Controller只能在M1Hardware activation admission成功後啟用；normal deactivation與system shutdown都必須到達同一核准的bounded device sequence，不能只依賴destructor。
Minimum Missing Behavior: M1Hardware依M1Driver結果檢查communication、兩顆drive alarm與actual RPM，SVON後bounded確認motion-enabled；停用時獨立嘗試JG0、zero-RPM確認、SVOFF／狀態確認與disconnect，累積各步結果而不得因單一步驟失敗提前略過後續actions。
Required Inputs: M1 communication結果、兩顆driver identity／alarm／status／actual RPM，以及核准的transition timing與zero-stop criteria。
Required Outputs: Admission成功後才可用的movement command interfaces；停用／關閉時各stop／confirm／disable／disconnect action的attempt/result與aggregate lifecycle outcome。
Constraints: ACTIVE、controller halt、zero command、JG0 sent、zero RPM confirmed、SVOFF sent與SVOFF confirmed是不同claims；這是operational safety behavior，不取代實體E-stop或構成功能安全認證。
Required Verification: Admission拒絕情境、無early nonzero command、JG0／poll／SVOFF／disconnect逐步失敗注入、remaining-action attempts、normal deactivation／system shutdown，以及target-AMR停止與drive state measurements。
Architecture Decision Needed: 05 保留framework lifecycle gate與M1 device admission／shutdown relationship、independent bounded-attempt contract及evidence boundaries；不新增generic safety manager或指定device internal algorithm。
```

### Architecture Considerations

05 應將 ros2_control lifecycle 視為標準 system seam，並將 M1Driver／M1Hardware 視為 M1 admission、JG0、zero-RPM confirmation、SVOFF confirmation 與 bounded best-effort shutdown sequence 的既有裝置邊界。`BEST_EFFORT` controller switching 不得被誤認為 vendor actions 的獨立嘗試保證；controller command 歸零也不得被當作 physical stop 或 drive disable evidence。此 operational safety behavior 不取代已正常工作的實體 E-stop。

### MVP Change Candidate

`None`。完整 admission與bounded safe-stop／disable behavior 必須保留；缺口限定於既有 M1 device boundary，不需要新增 generic safety manager。

## 6.4 Mapping

## SYS-001 Map Creation

### Required Behavior / Constraint

系統應建立可供定位與導航使用的二維 Occupancy Grid 地圖；建圖功能無法完成初始化並進入可處理建圖資料的狀態時，應回報失敗及原因。

### Candidate Assessment: slam_toolbox online asynchronous mapping

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `slam_toolbox` online asynchronous mapping |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Jazzy release `slam_toolbox` 2.8.5-1；target image installed version 尚待確認與固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | Managed lifecycle 原生提供 configure／activate 初始化邊界、transition result與失敗diagnostics；成功進入ACTIVE後，可接收單一選定的`sensor_msgs/msg/LaserScan`與TF／odometry，執行二維pose-graph SLAM並發布`nav_msgs/msg/OccupancyGrid`與Mapping Mode所需的`map -> odom` |
| Known Constraints | 「進入可處理狀態」定義為configure／activate成功且lifecycle ACTIVE，不代表已收到或處理runtime scan；必須設定frames／mapping parameters、提供sensor TF及`odom -> base`，且Mapping Mode只能有一個`map -> odom` owner；`teleop_twist_keyboard`只是人工建圖的command source |
| Uncovered Gap | `None`；不需要自製 SLAM、Occupancy Grid 產生器或雙 LiDAR merge behavior |
| Evidence | ROS 2 Jazzy `slam_toolbox` 2.8.5 package／API documentation、upstream 2.8.5 interface與algorithm說明、official `online_async_launch.py`／`mapper_params_online_async.yaml`、Jazzy bloom release metadata；詳見 `research/sys-001-map-creation.md` |
| Missing Evidence | Target image installed version；正常configure／activate與無效solver／plugin／parameter等初始化失敗注入；selected scan／TF／odometry整合；exclusive`map -> odom` ownership；部署參數；目標場域之覆蓋、幾何一致性、障礙物表現及後續定位／導航fitness |

候選搜尋涵蓋ROS 2 Jazzy成熟二維SLAM package family。`slam_toolbox`與ROS 2 managed lifecycle已完整提供SYS-001的map-creation、初始化狀態與failure-diagnostic behavior，不需要自製mapping component、start timeout或首筆scan confirmation gate。ACTIVE後尚無scan或runtime TF／odometry不可用，不屬於SYS-001初始化失敗；持續更新與runtime input behavior留在SYS-006。地圖儲存、Navigation Mode startup load與Map Package read-back分別留在SYS-002、SYS-007與SYS-024。

### Architecture Considerations

05 應保留Mapping Mode的configure／activate supervision、selected scan、TF／odometry integration與`map -> odom` exclusive-ownership contracts；初始化成功界線是lifecycle ACTIVE，不追加runtime input readiness gate。雙LiDAR維持independent-source-first；SYS-001只要求選定足以建圖的scan source，不因其他consumer使用merged scan而要求Mapping也必須融合。參數與真機map fitness留在後續composition、configuration與verification closure。

### MVP Change Candidate

`None`。

## SYS-002 Map Storage

### Required Behavior / Constraint

系統應將建圖結果儲存為 Map Package；無法儲存 Map Package 時，系統應回報失敗及原因。

### Candidate Assessment: nav2_map_server map saver

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `nav2_map_server` 的 `map_saver_cli` 或 lifecycle `map_saver`／`nav2_msgs/srv/SaveMap` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Jazzy release `nav2_map_server` 1.3.12-1；target image installed version 尚待確認與固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 從選定的 `nav_msgs/msg/OccupancyGrid` topic 取得地圖，依指定 basename 寫出 image 與 YAML metadata；在人工選定的場域目錄以固定 basename `map`、PGM image format 與 trinary map mode 產生 `map.pgm`、`map.yaml`；以 service boolean／CLI process result 回報成功或失敗，並以原生 ROS logs 回報失敗原因 |
| Known Constraints | 必須預先建立／選定可寫且可持久保存的場域目錄，指定 authoritative map topic、完整 basename、format、mode、threshold 與 timeout；同名檔案會直接覆寫，image 與 YAML 分步寫入而非原子 package transaction |
| Uncovered Gap | `None`；目前 requirement 未要求 structured error code、錯誤 taxonomy、原子寫入或自動復原，不需要自製 map encoder、file writer 或 package manager |
| Evidence | ROS 2 Jazzy `nav2_map_server` 1.3.12 package／API documentation、upstream 1.3.12 `map_io.cpp`、Jazzy `map_saver.cpp`、`nav2_msgs/srv/SaveMap` 與 Jazzy binary release metadata；詳見 `research/sys-002-map-storage.md` |
| Missing Evidence | Target image installed version；authoritative map topic QoS／freshness；target volume path、permission與persistence；成功產生非空 `map.pgm`／`map.yaml`；no-map timeout、invalid parameters、目錄／權限／filesystem failure 的 result 與 log；overwrite policy，以及寫入失敗後可能殘留部分更新檔案的操作與結果規則 |

候選搜尋同時檢查 `nav2_map_server` 與 `slam_toolbox` 的 persistence interfaces。`slam_toolbox/save_map` 可作為較窄的 image-map convenience wrapper，但 `nav2_map_server` 的標準 SaveMap contract 可明確指定 topic、basename、format、mode 與 thresholds，並與後續 map-server reload 使用相同 MapIO format，因此是較直接且與 SLAM implementation 解耦的 reuse candidate。`slam_toolbox/serialize_map` 產生的 pose-graph／scan data 用於繼續建圖或 toolbox localization，不是目前 `map.pgm`、`map.yaml` 所構成的 Map Package。

目前同一場域以一個人工命名目錄集中管理、不同場域使用不同目錄名稱、目錄內採固定檔名，只需要 path selection 與 configuration。`route_graph.geojson`、`stations.yaml` 與 Navigation configuration 是分離的 Navigation Resources；共同放在場域目錄不代表它們由 SYS-002 建立或儲存。SaveMap 的 boolean／process result 與原生 logs 已滿足目前的失敗及原因回報；image 與 YAML 分步寫入可能留下 partial residue，但該次操作仍回報失敗，儲存後能否重新解析則由 SYS-024 判定。Navigation Mode startup load 留在 SYS-007。

### Architecture Considerations

05 應保留 authoritative candidate Occupancy Grid 到 persistent Map Package 的標準儲存關係，以及 per-site directory selection、fixed basename、filesystem persistence、overwrite、failure result／logs 與 partial-write constraints。它不應新增自製 resource manager，只因標準 saver 不替專案命名場域或建立 parent directory；儲存後的 read-back validation 由 SYS-024 負責。

### MVP Change Candidate

`None`。

## SYS-006 Continuous Map Update

### Required Behavior / Constraint

建圖進行期間，系統應於取得新的有效感知與里程資料後更新目前二維 Occupancy Grid；資料暫時不可用時，系統應保留目前地圖並等待後續有效資料，直到使用者完成或終止建圖。

### Candidate Assessment: slam_toolbox online asynchronous mapping

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `slam_toolbox` online asynchronous mapping |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Jazzy release `slam_toolbox` 2.8.5-1；target image installed version 尚待確認與固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | Active mapping session 透過 TF message filter 接收可轉換的單一 selected `LaserScan`，取得 scan timestamp 的 odometry pose，依 pause／throttle／time／travel／heading條件接受後續measurements並更新pose graph，再依`map_update_interval`將current graph rasterize／發布為`nav_msgs/msg/OccupancyGrid`；暫時不可用的資料會等待或被捨棄，既有graph／map保留，後續有效資料可在同一session繼續處理 |
| Known Constraints | 「有效資料」是通過scan interface、TF／odometry與mapping acceptance rules的measurement，不是每筆raw scan都必須改圖或一對一立即發布；`map_update_interval`只控制current graph的輸出刷新週期，且publisher必須active並至少有一個subscriber；暫時沒有有效input不會自動終止建圖；pause不等於使用者完成或終止 |
| Uncovered Gap | `None`；不需要自製continuous-map updater、scan queue或Occupancy Grid refresh loop |
| Evidence | ROS 2 Jazzy `slam_toolbox` 2.8.5-1 release metadata；upstream 2.8.5 `slam_toolbox_common.cpp`／`slam_toolbox_async.cpp` 的scan admission、odom lookup、measurement acceptance、map refresh與lifecycle source；official async configuration／launch；詳見 `research/sys-006-continuous-map-update.md` |
| Missing Evidence | Target image installed version；selected scan與scan-stamped TF／odometry freshness及QoS；message-filter drops、accepted-scan rate、CPU load與map publication cadence；暫時失去input期間既有地圖保留且恢復後可繼續更新；AMR移動後map content確實新增／修正；使用者完成／終止並deactivate後不再接受新measurement或發布mapping updates |

SYS-001 已證明成熟套件能建立二維 Occupancy Grid；本項進一步確認 active Mapping session 會持續接受符合條件的後續 measurement、更新 pose graph，並按設定刷新 current Occupancy Grid。暫時缺少或無效的 scan／TF／odometry 會等待或被捨棄，既有 graph／map 保留並等待後續有效資料；這正是目前 SYS-006 核准的原生等待語意，因此不需要自訂 input-health monitor、failure classifier 或 automatic termination seam。

### Architecture Considerations

05 應保留 selected authoritative scan、scan-stamped TF／odometry、measurement acceptance、map refresh subscriber、Mapping Mode lifecycle，以及使用者完成／終止後deactivate並停止更新的composition contracts。雙LiDAR維持independent-source-first，`teleop_twist_keyboard`只提供移動命令；SYS-006不要求merge、input-health monitor、automatic failure termination或custom mapping controller。Map Package儲存與read-back分別由SYS-002與SYS-024負責，不由本項提前定義。

### MVP Change Candidate

`None`。

## SYS-007 Map Load

### Required Behavior / Constraint

系統應在 Navigation Mode 啟動期間載入所選定的 Map Package，將其中的二維 Occupancy Grid 提供給地圖定位與導航功能使用；Map Package 無法載入時，不得進入 navigation-ready 狀態，並應回報原因。

### Candidate Assessment: Navigation2 localization startup composition

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `nav2_bringup/localization_launch.py map:=<selected map.yaml>`，組合 `nav2_map_server` lifecycle `map_server`、`nav2_lifecycle_manager` 與 `nav2_amcl` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 1.3.12／binary release 1.3.12-1；target image installed versions 尚待確認與固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | Launch argument將所選`map.yaml`寫入`map_server.yaml_filename`；map server在configure期間解析YAML／image並建立Occupancy Grid；lifecycle manager只有在map server與AMCL均configure成功後才activate；active map server以reliable／transient-local QoS發布地圖供AMCL及後續Nav2 consumers使用；載入失敗會記錄原因、使map server configure失敗並中止localization managed-node bringup |
| Known Constraints | V0.1只支援Navigation Mode startup loading，不要求runtime `LoadMap`、hot switch或AMCL接收第二張地圖；map load success只證明Occupancy Grid可用，不代表initial pose已提供、AMCL已有新的pose／TF輸出或其他人工管理Navigation Resources內容正確 |
| Uncovered Gap | `None`；不需要自製map parser、loader、publisher或AMCL map adapter |
| Evidence | Navigation2 1.3.12 official `localization_launch.py`；Jazzy `nav2_map_server`／MapIO、`nav2_lifecycle_manager`與AMCL docs／source；詳見 `research/sys-007-map-reload.md` |
| Missing Evidence | Target image installed versions；實際非空場域Map Package；正常啟動時map server與localization lifecycle ACTIVE及authoritative `/map`內容／QoS；YAML不存在、metadata錯誤、image不存在／損壞時的原因log、lifecycle startup failure，以及navigation-ready維持false |

目前操作以人工選定場域後執行official localization launch為baseline：

```text
selected maps/<site>/map.yaml
  -> localization_launch.py map argument
  -> map_server configure: YAML + image -> OccupancyGrid
  -> lifecycle manager activates map_server and AMCL
  -> authoritative /map available to localization and navigation consumers
```

SYS-007只判定Navigation Mode startup期間的Map Package載入與localization managed-node bringup；它不另外定義AMCL收斂或localization-valid gate。其他Navigation Resources由使用者依01–02的MVP操作規則人工建立、選擇與確認；Runtime `LoadMap`雖為upstream附帶能力，但不列入本項covered scope、configuration或acceptance evidence。

### Architecture Considerations

05 應將Map Package selection與startup load放在Navigation Mode的localization bringup關係中，保留selected per-site `map.yaml`、map topic／frame／QoS、ordered lifecycle startup，以及load failure阻止navigation-ready的contract。不得因upstream存在`LoadMap`就新增runtime換圖責任，也不得把map load success等同AMCL已有pose／TF輸出或人工管理的其他Navigation Resources已被系統驗證。

### MVP Change Candidate

`None`。

## SYS-024 Map Package Read-back

### Required Behavior / Constraint

系統應於 Map Package 儲存後，確認其中的地圖可重新解析為二維 Occupancy Grid；無法解析時，系統應依標準解析結果回報失敗及原因。

### Candidate Assessment: Navigation2 MapIO read-back

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 `nav2_map_server` public MapIO `loadMapFromYaml()` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Jazzy release `nav2_map_server` 1.3.12-1；target image installed version 尚待確認與固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 讀取指定`map.yaml`與其image reference，解析metadata與image並轉換為`nav_msgs/msg/OccupancyGrid`；以public `LOAD_MAP_STATUS`判定success／failure，並以標準status與原生logs回報YAML／image解析失敗原因 |
| Known Constraints | SYS-024只採標準parser結果，不額外判定grid非空、地圖品質、定位fitness或Navigation Resources相容性；read-back必須指向剛儲存的同一Map Package；直接MapIO call不建立／activate map server，也不發布或替換`/map` |
| Uncovered Gap | `None`；不需要自製parser、額外validation layer、error taxonomy或map server |
| Evidence | Navigation2 Jazzy `nav2_map_server` 1.3.12-1 release metadata；upstream 1.3.12 public `map_io.hpp`／`map_io.cpp`之`loadMapFromYaml()`、`LOAD_MAP_STATUS`與原生exception logs；詳見 `research/sys-024-mapping-result.md` |
| Missing Evidence | Target image installed version；實際Map Package成功解析；`MAP_DOES_NOT_EXIST`、`INVALID_MAP_METADATA`、`INVALID_MAP_DATA`之status與log；read-back path確實指向同一儲存結果，且操作不產生`/map` side effect |

MapIO公開且與node object無關的`loadMapFromYaml()`已完整提供Map Package到Occupancy Grid的標準read-back。`LOAD_MAP_SUCCESS`就是目前SYS-024的成功條件；`MAP_DOES_NOT_EXIST`、`INVALID_MAP_METADATA`、`INVALID_MAP_DATA`及同次原生logs提供失敗與原因。呼叫public library API並轉送標準結果屬integration／composition，不形成custom behavior gap。

### Architecture Considerations

05 應保留SYS-002 SaveMap成功後，以剛儲存的authoritative `map.yaml`執行一次direct MapIO read-back並保留標準status／logs的順序關係。此read-back不應啟動MapServer或發布`/map`；Navigation Mode startup load仍由SYS-007負責，地圖品質與實機定位表現分別留給後續verification與SYS-010的AMCL整合證據。

### MVP Change Candidate

`None`。

## SYS-034 Manual Movement Control

### Required Behavior / Constraint

建圖期間，系統應接受使用者提供之手動速度命令以控制 AMR 移動巡覽環境；該移動控制應遵守既有底盤運動控制、運動限制、命令逾時與安全啟停需求。未提供手動速度命令或命令停止時，建圖程序不應因此終止。

### Candidate Assessment: teleop_twist_keyboard

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `teleop_twist_keyboard` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Debian package `ros-jazzy-teleop-twist-keyboard` 2.4.1-1noble.20260612.132037（upstream 2.4.1） |
| Coverage Status | `Fully Covered` |
| Covered Scope | 捕捉終端 raw TTY 按鍵輸入，映射為標準 ROS 2 速度命令；原生支援 `stamped` 參數以發布 `geometry_msgs/msg/TwistStamped`（或預設 `Twist`），精確契合下游 controller command contract；支援線速度與角速度步進調整與方向控制；操作員輸入非移動鍵或中斷結束時主動發布零速；按鍵閒置停止發布時由下游 `diff_drive_controller` 原生逾時停止機制（SYS-027）接管保護；速度命令通過既有 S7 安全與限幅鏈（SYS-028／SYS-030）；建圖程序獨立維持（SYS-006） |
| Known Constraints | 必須在具備 TTY／stdin 的終端執行；Jazzy `diff_drive_controller` 4.42.1 topic input 固定為 `TwistStamped`，故整合時需設定 `stamped:=true`；預設發布 topic 為 `cmd_vel`，可透過標準 CLI remap 對接 controller input；Mapping Mode 下單一 command producer 無衝突，不需 command mux 或 mode manager |
| Uncovered Gap | `None`；不需要自製 teleop 節點、mode manager 或 safety gateway |
| Evidence | ROS 2 Jazzy `teleop_twist_keyboard` 2.4.1 源碼與參數宣告（`stamped`、`frame_id`、`speed`、`turn`）、Dockerfile baseline（第 17 行已安裝）及 container 內 `dpkg -s` 驗證；詳見 `research/sys-034-manual-movement-control.md` |
| Missing Evidence | target Jetson／AMR 實機鍵盤操作移動驗證；操作員停止按鍵後主動發布零速與逾時停止之分層驗證；建圖巡覽過程中 Occupancy Grid 持續更新端對端驗證 |

候選搜尋涵蓋 ROS 2 Jazzy 官方手動控制套件。`teleop_twist_keyboard` 已完整提供建圖巡覽所需之鍵盤手動速度命令生成與標準 Twist / TwistStamped 發布能力。

在介面相容性上：Jazzy 官方 `ros2_controllers` 4.42.1 之 `diff_drive_controller` 在非 chained 模式下訂閱 `geometry_msgs/msg/TwistStamped`，而 `teleop_twist_keyboard` 2.4.1 原生具備 `stamped` 參數（設為 `true` 時即發布含 timestamp 與 frame_id 之 `TwistStamped`），並可透過標準 CLI remap（如 `cmd_vel:=/diff_drive_controller/cmd_vel`）對接。此屬標準 ROS 2 composition / launch configuration 範疇，不構成 custom gap。

在停止與逾時語意上，系統具備清晰的分層行為：
1. **主動停止（Active Zero Command）**：操作員按下非移動按鍵（如 `k` 或空白鍵）時，節點主動發布零速命令；操作員以 `CTRL-C` 退出時，節點亦於清理階段發布零速命令，由下游 controller 執行主動煞停。
2. **無命令閒置與通訊逾時（Stale Command Protection）**：當操作員放開按鍵、未繼續輸入時，`teleop_twist_keyboard` 保持阻塞等待輸入而不發布新命令；此時下游 `diff_drive_controller` 依據 `SYS-027` 之 `cmd_vel_timeout` 機制判定命令逾時，自動將 reference velocity 歸零並安全煞停底盤。
3. **建圖持續性**：底盤依上述任一機制停止時，建圖節點（`slam_toolbox`）依 `SYS-006` 維持現有地圖，不中斷 Mapping session。

在 Mapping Mode 下，由於 Nav2 自主導航未啟動，`teleop_twist_keyboard` 為唯一的運動命令來源，不涉及多來源衝突或仲裁。手動命令透過標準 topic 進入 S7 Base Control，完全受 `diff_drive_controller` 的 `SpeedLimiter`（SYS-028）與 `M1Hardware` 安全啟停閘門（SYS-030）約束，不形成任何繞過 S7 的控制旁路。因此不需要新增 custom gap。

### Architecture Considerations

05 應將 `teleop_twist_keyboard` 定位為 Mapping Mode 下外部使用者輸入來源，透過 `stamped:=true` 與 topic remapping 將標準 `geometry_msgs/msg/TwistStamped` 銜接至 S7 Base Control 之命令輸入介面。在 Mapping Mode 下不應引入 `twist_mux`、mode manager 或額外 safety proxy，以維持 MVP 與避免過早結構（Avoid Premature Structure）。

### MVP Change Candidate

`None`。

## SYS-008 Navigation Target

### Required Behavior / Constraint

系統應支援以下 Navigation Target：

- Station
- Goal Pose

### Candidate Assessment: NavigateToPose canonical goal plus terminal target-form adapter

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 `nav2_msgs/action/NavigateToPose`，canonical goal使用`geometry_msgs/msg/PoseStamped` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2／`nav2_msgs` Jazzy release 1.3.12-1；target image installed version 尚待確認與固定 |
| Coverage Status | `Partially Covered` |
| Covered Scope | Goal Pose可由標準`PoseStamped`完整表達frame、timestamp、position與orientation，並由SYS-009正規化為同一canonical型別；通過SYS-033 validation後，可沿用`NavigateToPose.Goal.pose`交給Nav2 |
| Known Constraints | Nav2的navigation action與Simple Commander只接受pose goal，沒有Station ID欄位或Station target variant；SYS-008只要求接收並區分兩種外部target form，不負責Station查表、合法性判定、資源相容性或導航執行 |
| Uncovered Gap | 最小terminal-facing target input schema／adapter：接受並明確區分Station與Goal Pose，Goal Pose原樣交給SYS-009，Station ID原樣交給SYS-032；不包含normalization、Station resolution或canonical-pose validation |
| Evidence | Navigation2 Jazzy 1.3.12-1 `NavigateToPose.action`與Nav2 Simple Commander `goToPose()`官方API；ROS 2 Jazzy `geometry_msgs/msg/PoseStamped` interface；詳見 `research/sys-008-navigation-target.md` |
| Missing Evidence | Target image installed version；兩種terminal forms之實際語法與discriminator；Goal Pose欄位完整交給SYS-009；Station ID原樣交給SYS-032；未通過SYS-033前不送入Nav2 |

成熟Nav2完整覆蓋pose goal representation，但不提供Station ID target form，因此整體為Partially Covered。最小缺口只存在於terminal input boundary：辨識target form後，Goal Pose交給SYS-009，Station ID交給SYS-032；兩路形成canonical `PoseStamped`後共同由SYS-033驗證。Navigation Resources由使用者依MVP操作規則人工確認，不形成runtime admission responsibility，也不重複計入SYS-008 gap。不得因這個薄seam新增Mission Core、Station Registry、自訂navigation action、Web Panel或Docking scope。

### Architecture Considerations

05 應保留`人工確認場域資料夾 -> terminal input -> target-form discriminator -> Goal Pose交SYS-009／Station ID交SYS-032 -> canonical PoseStamped -> SYS-033 validation -> Nav2`的收斂關係。核心導航只接收validated canonical `PoseStamped`；Station與Goal Pose是外部輸入形式，不應在後續planner／controller形成兩條執行路徑。Relative Pose不在目前SYS-008 scope。

### MVP Change Candidate

`None`。

## SYS-009 Goal Pose Normalization

### Required Behavior / Constraint

系統應接受使用者透過終端提交以公尺表示之絕對 `x`、`y`，以及以度表示之 `yaw-deg` Goal Pose，並將其正規化為目前導航全域座標框架中的 canonical `geometry_msgs/msg/PoseStamped`；系統應保留其絕對位置與方向語意，將 `yaw-deg` 轉換為 quaternion，並依操作規則設定 frame 與 timestamp。必要欄位缺失或無法解析時，系統應拒絕該目標並回報原因。

### Candidate Assessment: standard PoseStamped and tf2 with thin terminal normalization adapter

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy standard `geometry_msgs/msg/PoseStamped`、REP-103單位慣例、`tf2` quaternion APIs與標準CLI argument parser，組合一個最小terminal normalization adapter |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；`geometry_msgs` Jazzy release 5.3.8-1、`tf2` Jazzy release 0.36.22-1；target image installed versions與CLI implementation language尚待確認與固定 |
| Coverage Status | `Partially Covered` |
| Covered Scope | `PoseStamped`提供frame／stamp／position／orientation標準結構；REP-103固定ROS內部長度與角度單位；tf2提供roll／pitch／yaw quaternion建立、normalization與message conversion；標準argument parser可拒絕missing／unparseable options並回報原因 |
| Known Constraints | V0.1外部CLI contract固定為absolute `x`／`y` meters與`yaw-deg` degrees；adapter須執行degrees-to-radians、設定2D `z=0`／roll=0／pitch=0、依操作規則填入global frame與timestamp，且不得將輸入解讀為relative displacement；finite／TF／frame／quaternion最終有效性由SYS-033負責 |
| Uncovered Gap | 最小terminal CLI／normalization adapter：解析`nav_goal pose --x <m> --y <m> --yaw-deg <deg>`，組合成熟conversion APIs並輸出canonical `PoseStamped`；不需要自訂pose message、quaternion algorithm或navigation action |
| Evidence | ROS 2 Jazzy `geometry_msgs/msg/PoseStamped`與REP-103；tf2 0.36.22-1 `Quaternion::setRPY()`／`normalize()`及`tf2_geometry_msgs::toMsg()`官方API／source；詳見 `research/sys-009-target-validation-resolution.md` |
| Missing Evidence | Target installed versions；CLI語法與option parser；degrees-to-radians及quaternion conversion；absolute x／y與yaw語意保留；frame／timestamp policy；missing／unparseable option reasons；輸出交給SYS-033而非直接送入Nav2 |

成熟ROS 2型別與tf2完整覆蓋canonical pose representation與角度轉換機制，但不提供專案核准的`nav_goal pose --x --y --yaw-deg`操作介面，因此整體為Partially Covered。自訂範圍只是一個薄terminal adapter；不得把SYS-033的pose-validity policy、SYS-032的Station resolution或人工Navigation Resource確認納入本項。

### Architecture Considerations

05 應保留`terminal Goal Pose -> SYS-009 normalization -> canonical PoseStamped -> SYS-033 validation`關係，並把global frame與timestamp視為明確operation policy。CLI與conversion可以組合成熟library，但不得讓navigation execution直接理解`x／y／yaw-deg`或建立第二種核心goal type。Relative Pose不在v0.1 scope。

### MVP Change Candidate

`None`。

## SYS-032 Station Target Resolution

### Required Behavior / Constraint

系統應使用目前場域之 Station Catalog，將使用者提交的 Station ID 解析為該 Station 預先定義之 canonical `geometry_msgs/msg/PoseStamped`；Station ID 為空、找不到對應 Station 或無法解析時，系統應拒絕該目標並回報原因。

### Candidate Assessment: standard PoseStamped plus thin Station resolver

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy standard `geometry_msgs/msg/PoseStamped`與通用configuration／YAML parsing能力，組合一個最小Station resolver；Navigation2沒有原生Station ID或Station Catalog API |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；`geometry_msgs` Jazzy release 5.3.8-1、Navigation2 Jazzy release 1.3.12-1；Catalog parser與target image installed versions尚待05／06選定及固定 |
| Coverage Status | `Partially Covered` |
| Covered Scope | `PoseStamped`提供resolved target的標準表示；通用parser可讀取後續核准的Catalog資料格式；SYS-008提供Station form與原始ID，使用者依MVP操作規則提供人工確認的目前場域Catalog，SYS-033接續驗證resolved pose |
| Known Constraints | Nav2不提供Station ID、canonical Station Catalog或lookup／resolution API；lookup必須對目前Catalog採deterministic exact match，保留命中pose之frame／stamp／position／orientation，不得把Station ID默認等同Route Graph node ID |
| Uncovered Gap | 最小Station resolver：接收非空Station ID，在目前有效Catalog精確查找，輸出預定義canonical `PoseStamped`；empty、not found或命中資料無法形成`PoseStamped`時拒絕並回報可辨識原因 |
| Evidence | ROS 2 Jazzy `geometry_msgs/msg/PoseStamped`；Navigation2 Jazzy 1.3.12-1 `NavigateToPose`／Waypoint Follower／Docking公開interfaces之scope檢查；詳見 `research/sys-032-station-target-resolution.md` |
| Missing Evidence | Target installed versions；Station Catalog後續核准schema／parser；exact-match與case／whitespace policy；empty／unknown／unresolvable reason；resolved pose欄位保真與SYS-033 handoff；不同場域Catalog isolation |

成熟ROS 2與Nav2提供pose goal表示及下游navigation consumer，但沒有專案需要的Station semantics，因此不能判為Fully Covered。最小自訂範圍只是一個薄lookup／resolution boundary；Catalog selection與場域內容正確性由使用者人工負責，parser失敗由resolver沿用成熟parser原因，pose validity由SYS-033負責。Waypoint Follower、Docking、Mission Core與Station Registry均不需要納入。

### Architecture Considerations

05 應保留`人工確認目前場域Station Catalog -> terminal Station ID -> SYS-032 parse／exact lookup -> canonical PoseStamped -> SYS-033 validation`關係。Station Catalog是人工管理的navigation resource，不代表必須建立runtime registry；Station target也不得因部署資料格式而與Route Graph node identity耦合。具體Catalog schema、parser與resolver internal API留給05／06收斂。

### MVP Change Candidate

`None`。

## SYS-033 Canonical Goal Pose Validation

### Required Behavior / Constraint

系統應於導航開始前驗證 canonical `geometry_msgs/msg/PoseStamped`。其位置與方向數值應為有限值、座標框架不得為空且應可轉換至目前導航使用之全域座標框架、方向 quaternion 應有效；驗證失敗時，系統應拒絕該目標並回報原因。只有通過驗證的 canonical `PoseStamped` 才可提供給後續導航流程。

### Candidate Assessment: standard numeric and tf2 validation primitives plus thin combined gate

| Field | Assessment |
|---|---|
| Candidate Mature Solution | C++ standard finite-number checks、ROS 2 Jazzy `tf2`／`tf2_ros` quaternion與transform APIs，組合一個最小pre-navigation canonical-pose validator／gate |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；`tf2`／`tf2_ros` Jazzy release 0.36.22-1、`geometry_msgs` 5.3.8-1、Navigation2 1.3.12-1；target image installed versions尚待確認與固定 |
| Coverage Status | `Partially Covered` |
| Covered Scope | `std::isfinite`可檢查position／orientation components；tf2可計算quaternion norm並提供transform availability、timeout與error detail；Nav2可接收通過驗證的canonical `PoseStamped`，其goal handling保留為提交後defense-in-depth |
| Known Constraints | `PoseStamped` message definition本身不執行validation；Nav2 `goalReceived()`／`initializeGoalPose()`發生在goal提交後，只覆蓋部分robot-pose／goal-transform條件，不完整檢查finite values、quaternion與project-level rejection reason；quaternion tolerance、TF timeout、frame／timestamp policy須由後續configuration固定 |
| Uncovered Gap | 最小combined validator／gate：依序聚合finite、nonempty frame、TF transformability與valid quaternion檢查；任一失敗即拒絕、回報可辨識原因且不得提交下游，全部通過才原樣轉交canonical `PoseStamped` |
| Evidence | ROS 2 Jazzy `tf2`／`tf2_ros` Buffer與Quaternion官方API／source；C++ finite-number standard；Navigation2 1.3.12-1 `NavigateToPoseNavigator::goalReceived()`／`initializeGoalPose()` source；詳見 `research/sys-033-canonical-goal-pose-validation.md` |
| Missing Evidence | Target installed versions；finite components matrix；empty frame；quaternion zero／non-unit tolerance；TF connected／missing／extrapolation與timeout reasons；frame／timestamp policy；任一失敗均不送入Nav2，以及valid pose欄位保真 |

成熟API完整提供各項validation primitives，但沒有一個upstream元件在Nav2 goal提交前形成SYS-033要求的完整組合與單一target-admission decision，因此為Partially Covered。缺口是薄gate，不是自製TF、quaternion math或navigation validator framework；map bounds、occupancy、path feasibility、人工Navigation Resource確認與localization不在本項。

### Architecture Considerations

05 應保留SYS-009與SYS-032兩路輸出共同進入SYS-033後才可送往導航的唯一gate。Requirement分開是為了traceability與獨立驗證，不表示必須建立三個ROS nodes；05可將target-form handling、normalization／resolution與共同validation收斂在同一個薄terminal-facing boundary，但須維持可分別測試的責任與failure reasons。

### MVP Change Candidate

`None`。

## SYS-010 Map Localization

### Required Behavior / Constraint

系統應根據已載入地圖與可用的感知及里程資料估測 AMR 位姿，並提供標準定位 pose 與 `map → odom` transform，供導航功能使用。當 AMR 開機位置無法可靠得知時，系統應接受使用者提供目前地圖中的 approximate initial pose，作為定位初始化輸入。

### Candidate Assessment: Navigation2 AMCL localization

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 `nav2_amcl`，搭配`nav2_map_server`、localization lifecycle composition及RViz `2D Pose Estimate` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2／`nav2_amcl` Jazzy release 1.3.12-1；target image installed versions尚待確認與固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | AMCL使用loaded `nav_msgs/msg/OccupancyGrid`、selected `LaserScan`及odom／TF估測map pose，發布`amcl_pose`並維護`map -> odom`；接受standard `/initialpose`或`SetInitialPose`輸入，RViz `2D Pose Estimate`可提供v0.1人工approximate initial pose；標準lifecycle composition管理configure／activate |
| Known Constraints | SYS-010不再要求project-level localization-valid、convergence threshold、navigation admission、loss termination或專屬failure classification；缺少scan／map／odom／TF時依AMCL原生等待、drop、warning或無新輸出行為；`map -> odom`必須維持單一authoritative owner |
| Uncovered Gap | `None`；不需要自製localizer、initial-pose adapter、convergence monitor或localization admission gate |
| Evidence | Navigation2 Jazzy 1.3.12-1 `nav2_amcl`官方documentation、interfaces與source；`nav2_bringup/localization_launch.py`、RViz standard Initial Pose tool；詳見 `research/sys-010-map-localization.md` |
| Missing Evidence | Target installed versions；實際map／scan／odom／TF frames與QoS；AMCL parameters與sensor model；唯一`map -> odom` authority；RViz Initial Pose操作；正常pose／TF輸出、input／TF缺失原生行為，以及目標場域實機定位表現 |

AMCL原生完整覆蓋目前簡化後的定位、standard pose／TF output及人工Initial Pose需求，因此為Fully Covered。Runtime input暫時缺失或TF不可用不新增project health policy；其原生行為需由整合與實機evidence確認。自動定位、固定開機點與保存上次pose不在v0.1 scope。

### Architecture Considerations

05 應保留Map Package、selected scan、odom／TF到AMCL的標準composition，AMCL對`map -> odom`的exclusive ownership，以及v0.1 RViz Initial Pose操作流程。不得重新加入04已移除的custom localization-valid gate；下游Nav2使用標準pose／TF時的原生失敗行為留在相應navigation requirements與integration verification。

### MVP Change Candidate

`None`。

## SYS-011 Path Planning

### Required Behavior / Constraint

系統應使用目前位姿與 active navigation stage 的目標，透過 Navigation2 產生有效且非空的路徑。無法產生路徑時，系統不得開始該 stage 的路徑追蹤，並應回報 Navigation2 原生規劃失敗結果。

### Candidate Assessment: Navigation2 Planner Server

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 `nav2_planner` Planner Server與`nav2_core::GlobalPlanner` plugin |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed version與selected planner plugin尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | `ComputePathToPose`可使用current robot pose或explicit start與active-stage `PoseStamped` goal呼叫selected planner；Planner Server等待global costmap ready、執行必要TF轉換、拒絕empty path，成功回傳`nav_msgs/msg/Path`，失敗回傳原生error code與message |
| Known Constraints | 「有效」限於selected planner依configured global costmap、footprint、frames與plugin constraints接受且產生的non-empty path，不代表physical-safety certification；只有planning success後才可將path交給SYS-015開始tracking |
| Uncovered Gap | `None`；不需要自製planner、stage orchestrator、alternative manager或failure taxonomy |
| Evidence | Navigation2 1.3.12 `planner_server.cpp`、`ComputePathToPose.action`、`nav2_core::GlobalPlanner`及Planner Server官方configuration；詳見`research/sys-011-path-planning.md` |
| Missing Evidence | Target installed versions與selected planner plugin；實際frames／TF／global costmap／footprint配置；各active stage成功path；empty／no-path／TF／timeout等失敗結果；planning失敗時未開始`FollowPath`；實機planning latency與path suitability |

Navigation2 Planner Server已完整提供目前SYS-011要求的active-stage path computation、non-empty path acceptance與原生failure result。標準BT Sequence可使後續`FollowPath`只在`ComputePathToPose`成功後執行，因此失敗時不開始tracking也不需額外project gate。

### Architecture Considerations

05 應直接組合Planner Server、selected global planner plugin與標準BT planning-to-tracking sequence。SYS-011只擁有單一active stage的path computation；First Mile／On Route／Last Mile continuity、route-assisted alternatives、path tracking、停止、導航結果及`Free-space Fallback unavailable`分別由SYS-013、SYS-015、SYS-017及SYS-018～021承擔，不得在SYS-011建立重複orchestration責任。

### MVP Change Candidate

`None`。

## SYS-014 Obstacle Avoidance

### Required Behavior / Constraint

導航期間，系統應使用有效之環境障礙物資訊，避免規劃或執行穿越已判定占用區域之運動；無法維持可安全執行之導航時，系統應嘗試使底盤停止並回報失敗。

### Candidate Assessment: Navigation2 collision-aware navigation composition

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 layered global/local costmaps、collision-aware planner/controller、Planner/Controller Server、standard BT failure propagation及`nav2_collision_monitor` defense-in-depth |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed versions與selected plugins尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | sensor observations的marking／clearing與freshness；static/dynamic occupied costs及footprint inflation；planning與local trajectory collision checks；stale costmap、no-path或no-valid-control failure；Controller Server zero-velocity stop attempt及native error；Collision Monitor command-chain stop／slow／limit zones與source-timeout blocking behavior |
| Known Constraints | Collision Monitor是核准納入的defense-in-depth，但不是hard-real-time、safety-certified或實體E-stop替代品；zero velocity只證明software stop attempt，不證明底盤已實際停止；transparent、遮蔽、超出range或未被sensor/costmap標記的真實障礙不在occupied-cell保證內 |
| Uncovered Gap | `None`；不需要自製costmap、collision algorithm、obstacle-avoidance controller或failure taxonomy |
| Evidence | Navigation2 1.3.12 `nav2_costmap_2d`、Smac Planner、MPPI／Regulated Pure Pursuit、Planner／Controller Server、BT與Collision Monitor官方documentation/source；詳見`research/sys-014-obstacle-avoidance.md` |
| Missing Evidence | Target installed versions；實際LaserScan sources、QoS／TF／freshness；costmap marking／clearing／inflation；planner/controller collision injection；Collision Monitor sources/zones/source timeout/TF failure與cmd_vel chain；native failure與zero command；實機detection、braking及physical stop |

成熟Nav2 composition已完整覆蓋SYS-014，Custom Behavior Gap為None。Collision Monitor雖非原始normative behavior不可或缺的元件，仍依核准決策納入MVP成熟方案，提供更靠近速度命令輸出的額外stop／slow／limit防線；它不得取代核心costmap/planner/controller avoidance flow。

### Architecture Considerations

05 應保留`obstacle observations -> global/local costmaps -> collision-aware planner/controller -> Controller Server/BT failure`主流程，並把Collision Monitor放在核准的velocity-command chain中作defense-in-depth。Perception提供measurement，costmaps擁有occupied representation，planner/controller擁有collision avoidance，Nav2 action提供native failure，motion/base負責命令傳遞與physical-stop evidence；SYS-014不重複SYS-011、SYS-015、SYS-017或SYS-022／027／030責任。

### MVP Change Candidate

`None`。

## SYS-015 Path Tracking

### Required Behavior / Constraint

系統應透過 Navigation2 `FollowPath` 控制 AMR 追蹤目前 active navigation stage 的有效路徑，並使用設定的 controller 與 progress checker 判定能否繼續追蹤。無法繼續追蹤時，系統應停止該 stage 的路徑追蹤、嘗試使底盤停止，並回報 Navigation2 原生追蹤失敗結果。追蹤接受條件應經整合及實機驗證。

### Candidate Assessment: Navigation2 Controller Server and FollowPath

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 Controller Server、`FollowPath`、selected `nav2_core::Controller` plugin、Progress Checker、Goal Checker及standard BT composition |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed versions與selected controller/progress plugins尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 接受non-empty `nav_msgs/msg/Path`；以selected controller持續產生velocity commands；監控controller、path、TF、local costmap與progress；提供distance/speed feedback；無法繼續時終止`FollowPath`、發布zero velocity並回傳原生error code/message |
| Known Constraints | Progress Checker判定是否持續移動，不等同跨controller通用的lateral path-deviation量測；追蹤接受條件須依selected controller、progress policy與實機結果固定；zero velocity是software stop attempt，不證明physical stop |
| Uncovered Gap | `None`；不需要自製path follower、tracking monitor、stage orchestrator或failure taxonomy |
| Evidence | Navigation2 1.3.12 Controller Server、`FollowPath.action`、Progress/Goal Checker、MPPI／Regulated Pure Pursuit及standard BT官方documentation/source；詳見`research/sys-015-path-tracking.md` |
| Missing Evidence | Target installed versions與selected plugins；controller/local costmap/TF/odom/rate配置；First Mile、On Route、Last Mile實際path tracking；progress/failure injection；native error/result；zero-command chain；實機tracking error、latency及停止表現 |

Navigation2原生Controller Server與FollowPath完整覆蓋單一active stage的tracking、continue/failure判定、zero-velocity stop attempt及原生結果，因此Custom Behavior Gap為None。SYS-015不再重複stage transition、route-assisted candidate或fallback classification。

### Architecture Considerations

05 應讓SYS-011成功產生的active-stage path透過標準BT交給SYS-015 `FollowPath`，並由selected controller與Progress Checker負責單一路徑追蹤。First Mile、On Route與Last Mile均共用此tracking能力，但stage selection、transition與跨stage continuity必須由SYS-018～020後續assessment及05 contracts明確承接；route strategy／fallback與final result分別由SYS-013／021及SYS-017負責。不得因SYS-015簡化而刪除三階段移動原則或留下無owner的stage handoff。

### MVP Change Candidate

`None`。

## SYS-016 Goal Completion

### Required Behavior / Constraint

系統僅應在 AMR 目前位姿符合解析後 Navigation Target 所設定之位置與朝向接受條件，且底盤已停止時，判定導航成功。位置、朝向與停止判定門檻應經整合及實機驗證。

### Candidate Assessment: Navigation2 StoppedGoalChecker

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 Controller Server、`FollowPath`、`nav2_controller::StoppedGoalChecker`及standard NavigateToPose BT |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2／`nav2_controller` Jazzy release 1.3.12-1；target image installed version尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 對final path endpoint檢查current pose的XY與yaw；使用odometry-derived twist檢查平移與旋轉速度低於停止門檻；四項條件全部通過才讓`FollowPath`成功，並由standard BT傳遞至NavigateToPose success |
| Known Constraints | 必須使用`StoppedGoalChecker`而非只檢查pose的`SimpleGoalChecker`；final path endpoint須保留resolved Navigation Target position/yaw；navigation-level stopped使用odom feedback，不等同M1 wheel-stop hardware confirmation；`stateful`與所有thresholds須配置及實機驗證 |
| Uncovered Gap | `None`；不需要自製goal-completion gate、velocity monitor或success message |
| Evidence | Navigation2 1.3.12 `StoppedGoalChecker`／`SimpleGoalChecker`、Controller Server、`FollowPath`／`NavigateToPose` action及standard BT官方API/source；詳見`research/sys-016-goal-completion.md` |
| Missing Evidence | Target installed versions與selected Goal Checker ID；final endpoint preservation；odom topic/source/rate/latency；XY/yaw、translational/rotational stop及minimum-velocity thresholds；`stateful` policy；boundary/noise/creep及final-stage-only success實機結果 |

`StoppedGoalChecker`原生把position、orientation、odometry translational velocity與rotational velocity組成同一goal-reached predicate，完整覆蓋SYS-016，因此Custom Behavior Gap為None。Controller Server先套用minimum-velocity thresholds再呼叫checker；門檻過大可能過早成功，過小則可能受noise影響而無法成功，必須由整合及實機evidence固定。

### Architecture Considerations

05 應在final-stage `FollowPath`明確選用`StoppedGoalChecker`，並維持`final target endpoint -> StoppedGoalChecker -> FollowPath success -> final BT success -> NavigateToPose success`關係。Intermediate First Mile或On Route stage endpoint success不得直接形成整體Navigation Success；三階段transition仍由SYS-018～020承接，外部結果由SYS-017負責。SYS-016的odom stopped predicate不得被當作SYS-030 hardware stop confirmation。

### MVP Change Candidate

`None`。

## SYS-017 Navigation Result

### Required Behavior / Constraint

系統應透過 Navigation2 原生導航結果回報導航成功、失敗或取消；導航失敗時應回報可取得的 Navigation2 原生失敗結果。

### Candidate Assessment: Navigation2 native action result

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy action result、Navigation2 1.3.12-1 `NavigateToPose`、BT Navigator，以及`ComputePathToPose`／`FollowPath`／`ComputeRoute`原生results |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2／`nav2_msgs` Jazzy release 1.3.12-1；target image installed versions尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | ROS 2 action wrapped result區分`SUCCEEDED`／`ABORTED`／`CANCELED`；`NavigateToPose`提供overall result payload；BT Navigator聚合child error codes；planner、controller與route actions提供各自native failure codes |
| Known Constraints | 1.3.12不保證每個child的detail string完整傳到final `NavigateToPose.error_msg`；terminal client須同時觀察wrapped action status與result payload；CancelGoal request accepted不等於goal已完成取消，仍須等待final `CANCELED` result |
| Uncovered Gap | `None`；不需要stage-aware result taxonomy、project failure enum、result aggregator或custom navigation action |
| Evidence | ROS 2 Jazzy action semantics；Navigation2 1.3.12 `NavigateToPose`、BT Action Server、standard BT、`ComputePathToPose`、`FollowPath`與`ComputeRoute`官方interfaces/source；詳見`research/sys-017-navigation-result.md` |
| Missing Evidence | Target installed versions；actual BT error-code ports；planning/tracking/route child result至final result的傳遞；success/failure/cancel及race scenarios；terminal實際顯示之status、code與可取得message |

ROS 2 action與Navigation2原生result完整覆蓋目前SYS-017，因此Custom Behavior Gap為None。First Mile、On Route與Last Mile仍是SYS-018～020的執行原則，`Free-space Fallback unavailable`仍由SYS-021要求；SYS-017只回報它們最終形成的Nav2原生overall outcome，不再重複建立project stage分類。

### Architecture Considerations

05 應保留`child Nav2 action result -> BT Navigator result -> NavigateToPose wrapped status/payload -> terminal`的標準結果鏈。Terminal必須區分request accepted、canceling與final canceled；不得只用`error_code == 0`推論所有terminal states。不要為了標示First Mile／On Route／Last Mile而新增custom result framework；三階段與fallback責任仍須在SYS-018～021的execution flow中實現及驗證。

### MVP Change Candidate

`None`。

## SYS-025 Navigation Cancellation

### Required Behavior / Constraint

系統應接受使用者對進行中導航任務提出之取消要求，終止該導航任務，並回報取消結果。

### Candidate Assessment: ROS 2 action cancel and Navigation2 BT Navigator cancellation

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy action cancel 協定、Navigation2 1.3.12-1 `NavigateToPose`、`BtActionServer` / BT Navigator，以及 child action cancellation（`FollowPath`、`ComputePathToPose`、`ComputeRoute`） |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2／`nav2_msgs` Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 接收進行中導航之 cancel goal request；BT root halt 並級聯取消 active child actions；Controller Server 終止路徑追蹤並下發零速度命令；回傳標準 terminal `CANCELED` action result |
| Known Constraints | Cancel request accepted 僅表示進入 `CANCELING` 狀態，terminal client 必須等待最終 `CANCELED` result；若取消請求與目標達成（Success）或失敗（Abort）並發，依 ROS 2 action 語意以 server 處理當下狀態決定最終 terminal state；零速度下發為 navigation-level 停止，實體減速停止受限於底盤加減速限制與運動學 |
| Uncovered Gap | `None`；不需要自訂 cancellation watchdog、額外取消管理服務或客製化導航取消框架 |
| Evidence | ROS 2 Jazzy action cancel protocol；Navigation2 1.3.12 `BtActionServer`、BT Action Node halt 機制、`ControllerServer` cancel 零速下發官方 interfaces/source；詳見 `research/sys-025-navigation-cancellation.md` |
| Missing Evidence | Target installed exact versions；在 planning、tracking、recovery 及三階段各 stage 下之取消整合驗證；取消與即將成功／失敗之競態情境驗證；零速度發布與實體停止之時序量測；Terminal 端取消反饋與最終結果呈現驗證 |

ROS 2 action 取消協定與 Navigation2 原生 BT 級聯取消機制完整覆蓋 SYS-025，因此 Custom Behavior Gap 為 None。取消時的零速度命令由 Navigation2 controller 發布，底盤超時保護由 SYS-027 承接，實體運動限制由 SYS-028 承接；SYS-025 不另行建立客製化取消狀態機。

### Architecture Considerations

05 應維持標準 `Client cancel_goal -> NavigateToPose/BtActionServer -> BT root halt -> child actions cancel -> zero cmd_vel -> final CANCELED result` 調度鏈。Terminal 必須區分 request accepted 與 final canceled 狀態；取消處理過程中的底盤停止命令應經由標準 velocity multiplexer 與 `diff_drive_controller` 下發，不繞過 base controller 安全與逾時保護。

### MVP Change Candidate

`None`。

## SYS-013 Route-preferred Navigation Strategy

### Required Behavior / Constraint

系統應根據目前位姿、Canonical Goal Pose 與有效 Route Graph 建立可安全執行的 route-assisted movement，並優先使用適用的 Route Graph 範圍。存在有效且可安全執行的 route-assisted solution 時，系統不得選擇完整 free-space movement。

### Candidate Assessment: Navigation2 Route Server and Behavior Tree composition

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_route`（Route Server / `ComputeRoute.action`） + `nav2_planner`（Planner Server） + `nav2_behavior_tree` BT 組裝 |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 / `nav2_route` Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 依據 Current Pose、Canonical Goal Pose 與 Route Graph 搜尋並建立 route-assisted movement；在圖論路網可用範圍內優先採用 Route Graph；透過專案 BT 流程組裝確保優先採用 route 方案，並禁止在有可用 route 時執行完整 free-space 導航 |
| Known Constraints | Route Graph 必須為合法且已載入之資源；route-assisted 方案之可行性需經 global/local costmap 檢查；在 v0.1 階段，BT 流程不得配置全局 free-space fallback，無可用 route 時應依 SYS-021 終止並回報 |
| Uncovered Gap | `None`；不需要自行開發圖論搜尋演算法、自訂 Route Server 或客製化規劃核心 |
| Evidence | Navigation2 1.3.12 `nav2_route`、`ComputeRoute.action`、Route Server 官方文件與 `nav2_behavior_tree` 調度機制；詳見 `research/sys-013-route-preferred-navigation-strategy.md` |
| Missing Evidence | Target image installed exact versions；實際場域地圖與 Route Graph 拓撲之搜尋正確性驗證；驗證在有 route 情況下確實產生 route-assisted 移動；驗證無 route 時不會靜默轉為純 free-space 移動；實機規劃延遲與路徑可行性測試 |

ROS 2 Jazzy Navigation2 之 `nav2_route` 與 Behavior Tree 調度機制完整覆蓋 SYS-013，因此 Custom Behavior Gap 為 None。三階段具體執行分別由 SYS-018（First Mile）、SYS-019（On Route）與 SYS-020（Last Mile）承接，無可用路線時的終止由 SYS-021（Fallback Boundary）承接；SYS-013 只確立「路線優先、禁止任意自由移動」之決策原則，不重複建立自訂規劃演算法。

### Architecture Considerations

05 應在導航決策層（BT Navigator）將 `nav2_route` 之 `ComputeRoute` 作為主要路徑規劃入口，並依序串接 First Mile、On Route、Last Mile 三階段執行鏈。嚴格禁止在專案 BT 中設置無條件回退至全域純自由空間規劃（`ComputePathToPose` 直接至目標）之 fallback 分支，以落實 SYS-013 與 SYS-021 的策略約束。

### MVP Change Candidate

`None`。

## SYS-018 First Mile

### Required Behavior / Constraint

目前位姿不在選定 route entry 時，系統應規劃並執行由目前位姿至該 entry 的安全連接；目前位姿已位於適用的 route entry 時，First Mile 應視為不需要執行，不得因此判定導航失敗。

### Candidate Assessment: Navigation2 Planner and Controller with BT branching

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_planner`（Planner Server / `ComputePathToPose`） + `nav2_controller`（Controller Server / `FollowPath`） + `nav2_behavior_tree`（BT 條件判斷與順序控制） |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 判定 Current Pose 與選定 Route Entry 之容差關係；不在 Entry 時，規劃起點至 Entry 之局部自由空間路徑並執行路徑追蹤；已在 Entry 時，判定為 Not-required 並成功放行至 On Route 階段，不判定為失敗；連接失敗時回報原生失敗供 SYS-021 處理 |
| Known Constraints | Route Entry 必須為 Route Graph 上的有效節點／位姿；連接路徑受限於 global costmap 之障礙物占用；Not-required 判定容差（XY/Yaw tolerance）需合理配置；First Mile 成功僅代表抵達 Entry，不代表整體導航完成 |
| Uncovered Gap | `None`；不需要自訂銜接演算法或專屬 First Mile 控制器，完全可由標準 Nav2 組件與 BT 條件分支達成 |
| Evidence | Navigation2 1.3.12 `nav2_planner`、`nav2_controller`、`ComputePathToPose.action`、`FollowPath.action` 與 `nav2_behavior_tree` 條件分支機制；詳見 `research/sys-018-first-mile.md` |
| Missing Evidence | Target image 之 exact installed versions；在 Route Entry 外不同距離與角度下之規劃與追蹤驗證；在 Route Entry 容差內直接跳過（Not-required）且成功進入 On Route 之驗證；Entry 被障礙物阻擋時之失敗回報驗證；實機銜接平順度與過渡時延量測 |

Navigation2 Planner Server、Controller Server 與 Behavior Tree 條件分支機制完整覆蓋 SYS-018，因此 Custom Behavior Gap 為 None。First Mile 僅負責抵達 Route Entry，抵達後的路網移動由 SYS-019（On Route）承接，若無法連接 Entry 則交由 SYS-021（Fallback Boundary）處理；SYS-018 不承擔整體導航結果結算責任。

### Architecture Considerations

05 應在 BT Navigator 中以標準條件節點（Condition Node）檢查是否需執行 First Mile。若需執行，呼叫 `ComputePathToPose` 與 `FollowPath` 抵達 Entry；First Mile 完成後將控制權交給 On Route 階段（SYS-019），不在此處觸發整體導航成功結算（整體成功由最後階段 SYS-016 / SYS-017 負責）。

### MVP Change Candidate

`None`。

## SYS-019 On Route Navigation

### Required Behavior / Constraint

系統應沿選定 Route Graph route 由 route entry 移動至 route exit，並遵守 Route Graph 所定義的 connectivity、direction 與 availability constraints。

### Candidate Assessment: Navigation2 Route Server and Controller path tracking

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_route`（Route Server / `ComputeRoute`） + `nav2_controller`（Controller Server / `FollowPath`） + Local Costmap 避障 |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 / `nav2_route` Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 自選定的 Route Entry 沿著路網節點與邊（Nodes & Edges）行駛至 Route Exit；依有向圖（Directed Graph）嚴格約束行駛方向（Direction）與連通性（Connectivity），保證不逆向行駛；在路段不可用或受阻時配合 Route Server 重選可用路線；抵達 Route Exit 時結束 On Route 階段並交接予 Last Mile |
| Known Constraints | Route Graph 檔案必須合法定義連通性與方向性；AMR 在路網上的循跡貼合度由 local controller 參數（如 lookahead distance, path tolerance）決定；抵達 Route Exit 僅代表主線路網行駛結束，不代表整體導航完成 |
| Uncovered Gap | `None`；不需要自訂圖論循跡引擎或專屬車道保持控制器，標準 `nav2_route` 與 Nav2 Controller 即可完整支援 |
| Evidence | Navigation2 1.3.12 `nav2_route`、`route_server.cpp`、`ComputeRoute.action`、`FollowPath.action` 與 `controller_server.cpp` 之循跡與避障機制；詳見 `research/sys-019-on-route-navigation.md` |
| Missing Evidence | Target image 之 exact installed versions；單向邊、雙向邊、分岔路口與交叉口之循跡與方向約束驗證；中途路網阻塞觸發重新選路或失敗回報驗證；Route Exit 抵達判斷與交接 Last Mile 之平順度測試 |

ROS 2 Jazzy Navigation2 之 `nav2_route` 與 `nav2_controller` 完整覆蓋 SYS-019，因此 Custom Behavior Gap 為 None。AMR 從 Route Entry 出發，沿路網移動至 Route Exit，抵達 Exit 後順暢交接給 SYS-020（Last Mile）；若路網中途阻塞且無法重新選路，則依 SYS-021（Fallback Boundary）觸發降級終止。

### Architecture Considerations

05 應在 BT Navigator 中將 Route Path 的追蹤交由 `nav2_controller` 執行，並維持 local costmap 動態避障防線。On Route 抵達 Exit 點後，應平順觸發 Last Mile 子樹，不在此處做最終到站結算。

### MVP Change Candidate

`None`。

## SYS-020 Last Mile

### Required Behavior / Constraint

選定 route exit 未直接到達 Canonical Goal Pose 時，系統應規劃並執行由該 exit 至 Canonical Goal Pose 的安全連接；Canonical Goal Pose 已位於適用的 route exit 時，Last Mile 應視為不需要執行，不得因此判定導航失敗。

### Candidate Assessment: Navigation2 Planner and Controller with BT branching and StoppedGoalChecker

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_planner`（Planner Server / `ComputePathToPose`） + `nav2_controller`（Controller Server / `FollowPath`） + `nav2_behavior_tree`（BT 條件判斷與順序控制） + `StoppedGoalChecker` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 判定 Canonical Goal Pose 與 Route Exit 之容差關係；若未在 Exit 則規劃 Exit 至目標之局部自由空間路徑並執行追蹤；若已在 Exit 則判定為 Not-required 略過執行並順暢進入到站判定（SYS-016）；確保路徑終點保留 Canonical Goal Pose 之位置與朝向；連接失敗時回報原生失敗供 SYS-021 處理 |
| Known Constraints | Canonical Goal Pose 必須為 global costmap 上的可達非占用點；Last Mile 路徑終點必須精確保留 Canonical Goal Pose 的位置與朝向；Not-required 判定容差需合理配置；Last Mile 追蹤完成後由 SYS-016 之 `StoppedGoalChecker` 進行最終停止與到站結算 |
| Uncovered Gap | `None`；不需要自訂末端銜接演算法或專屬 Last Mile 控制器，完全可由標準 Nav2 組件與 BT 條件分支達成 |
| Evidence | Navigation2 1.3.12 `nav2_planner`、`nav2_controller`、`stopped_goal_checker.cpp`、`ComputePathToPose.action`、`FollowPath.action` 與 `nav2_behavior_tree` 條件分支機制；詳見 `research/sys-020-last-mile.md` |
| Missing Evidence | Target image 之 exact installed versions；在 Route Exit 外不同距離與朝向之目標點規劃與追蹤驗證；目標點剛好在 Exit 容差內直接跳過（Not-required）且成功結算之驗證；目標點周圍被障礙物阻擋時之失敗回報驗證；終點姿態精度與到站平順度量測 |

Navigation2 Planner Server、Controller Server、StoppedGoalChecker 與 Behavior Tree 條件分支機制完整覆蓋 SYS-020，因此 Custom Behavior Gap 為 None。Last Mile 負責由 Route Exit 抵達目標點並保持姿態，追蹤完成後交由 SYS-016 進行最終到站與停止結算；若無法連接目標點則交由 SYS-021（Fallback Boundary）處理。

### Architecture Considerations

05 應在 BT Navigator 中將 Last Mile 作為三階段移動的最後一環，並確保末端路徑嚴格保留 Canonical Goal Pose 的座標與朝向。Last Mile 追蹤完成後，直接對接 SYS-016 `StoppedGoalChecker` 進行位姿容差與底盤停止結算，由 SYS-017 對外發布最終導航成功結果。

### MVP Change Candidate

`None`。

## SYS-021 Reserved Free-space Fallback Boundary

### Required Behavior / Constraint

系統應保留下列 Free-space Fallback eligibility，以供後續版本擴充：

- Current Pose 無法連接任何可用 route entry。
- Active、valid Route Graph 無法提供通往 Canonical Goal Pose 方向的可用 route。
- On Route movement 因目前環境阻塞而無法維持，且重新選擇 Route Graph route 仍失敗。
- 所有可用 route-assisted candidates 均無法由 route exit 透過 Last Mile 安全連接 Canonical Goal Pose。

v0.1 不得執行 Free-space Fallback。符合上述任一 eligibility 且已無可用 route-assisted solution 時，系統應終止導航、嘗試使底盤停止，並回報 Free-space Fallback unavailable。Navigation Resource、Navigation Target 或 localization 的缺失、無效或不相容仍屬其各自 failure boundary，不構成 fallback eligibility。

### Candidate Assessment: Navigation2 Behavior Tree fallback handling and Action failure propagation

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_behavior_tree`（BT 流程與失敗捕捉） + `nav2_route` / `nav2_planner` / `nav2_controller` 失敗傳遞機制 + Action terminal `ABORTED` 結果回報 |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | `Fully Covered` |
| Covered Scope | 捕捉 First Mile 失敗、Route 搜尋無路、On Route 受阻重選失敗、Last Mile 失敗等 4 類無可用路線情境；在 BT 決策層落實 v0.1 禁用全局 free-space fallback 之約束；終止導航行為樹、主動發布零速命令煞停、回傳標準 `ABORTED` 狀態與失敗資訊；保持前置目標校驗（SYS-033）、資源載入（SYS-007）與定位有效性（SYS-010）之排他性失敗邊界 |
| Known Constraints | v0.1 階段不執行任何未受約束的全域自由空間脫困移動；失敗回報需透過 Action Result payload 或專案終端介面呈現；前置資源/目標/定位錯誤必須在進入導航前或由各自節點獨立攔截，不得誤入此處 |
| Uncovered Gap | `None`；不需要客製化降級管理器或專門的 fallback 守護進程，標準 Nav2 BT 流程組裝即可完全滿足 |
| Evidence | Navigation2 1.3.12 `nav2_behavior_tree`、BT Action Server 終止機制、`pipeline_sequence.cpp` 與 Action error 傳遞機制；詳見 `research/sys-021-reserved-free-space-fallback-boundary.md` |
| Missing Evidence | Target image 之 exact installed versions；針對 4 種 eligibility 條件的故障注入測試（起點堵塞、路網無路、中途堵死無替代、出口堵死）；驗證在失敗時絕不產生全局自由空間軌跡；驗證底盤平順煞停時序；Terminal 失敗訊息呈現驗證 |

Navigation2 Behavior Tree 流程組裝與 Action 失敗傳遞機制完整覆蓋 SYS-021，因此 Custom Behavior Gap 為 None。4 種 eligibility 條件由各階段失敗直接捕捉，v0.1 禁用全局自由空間降級之約束透過 BT XML 結構移除 fallback 規劃分支達成，終止時由 Nav2 Controller 下發零速煞停並回報結果；前置目標、資源與定位問題由各自獨立邊界處理。

### Architecture Considerations

05 應在專案 Behavior Tree XML 中徹底移除任何未經路網約束的全局自由空間 fallback 分支。當三階段路網流程遭遇不可恢復之失敗時，BT 應立即觸發任務 abort 與零速發布，將錯誤碼傳遞至終端，確保 AMR 永遠在受控路網內運作或安全就地停下。

### MVP Change Candidate

`None`。
