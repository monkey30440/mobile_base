# Reuse Assessment

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
| Motion and Drive | SYS-022、SYS-026、SYS-027、SYS-028、SYS-029、SYS-030、SYS-031 |
| Mapping | SYS-001、SYS-002、SYS-006、SYS-007、SYS-024 |
| Target, Resource, and Localization | SYS-008、SYS-009、SYS-010、SYS-012 |
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
