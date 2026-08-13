# Subsystem Design

# 1. Purpose, Scope and Authority

本文件定義 `mobile_base` v0.1 各 subsystem 的詳細設計，將 `05_architecture.md` 已核准的 system decomposition、responsibility allocation、cross-subsystem relationships、operational flows 與 system-wide contracts，落實為可實作、可整合及可驗證的 subsystem design。

## 1.1 Normative Input

本文件僅以 `05_architecture.md` 作為 normative design input。

現有 source code、舊版設計、實機測試結果、implementation baseline 與 exact-version 官方文件可作為 feasibility、現況及技術能力的 evidence，但不得反向改寫 `05_architecture.md` 已定義的：

- subsystem decomposition；
- responsibility allocation 與 primary ownership；
- cross-subsystem relationships；
- operational flows；
- system-wide architectural contracts。

若 evidence 顯示既有 architecture 缺漏、矛盾或不可實現，必須停止受影響的 subsystem 定案，回到最早受影響的 01–05 文件修正並取得核准；不得在本文件中靜默新增 user behavior、capability、requirement 或 architecture responsibility。

## 1.2 Scope

本文件負責定義每個 subsystem 的：

- purpose、boundary、inputs、outputs 與 dependencies；
- internal component decomposition 與各 component responsibility；
- package、node、plugin、process 或 composition responsibility；
- authoritative ROS interface、message type、frame、QoS 與 lifecycle contract；
- parameter、configuration 與 runtime resource ownership；
- failure detection、diagnostics、invalid／degraded behavior 與 safe-stop contribution；
- implementation handoff 與 verification responsibility；
- 為支援 runtime 所必要的 container deployment contract。

本文件可以依據 exact-version 官方能力與 project evidence 選擇成熟 solution，並優先使用 configuration 與 composition。只有在已證明成熟方案無法滿足核准責任時，才可定義最小必要 custom design，且必須記錄缺口與驗證方式。

## 1.3 Excluded Responsibilities

本文件不得：

- 新增或改寫 `01_use_cases.md`、`02_capabilities.md` 或 `03_requirements.md` 的內容；
- 新增、移除或重新分割 `05_architecture.md` 已核准的 subsystem；
- 重新指派 responsibility owner、command authority、TF ownership 或 safety responsibility；
- 改變 cross-subsystem relationship、operational flow 或 system-wide contract；
- 僅因現有 package、node、process 或第三方套件的結構而重新定義 subsystem boundary；
- 將未核准的 future feature 或方便 implementation 的行為寫成 v0.1 baseline；
- 虛構尚未由 integration 或 real-hardware evidence 確立的 operational parameter value。

## 1.4 Downstream Boundary

本文件是 implementation design、source code、launch、configuration、`Dockerfile`、Compose deployment 與 verification design 的上游依據。

本文件定義上述實作必須滿足的責任與 contracts，但不展開：

- function、class、method 或 source-file implementation；
- driver frame encoding、register-level procedure 或 algorithm code；
- 完整 `Dockerfile`、Compose service、image build 或 deployment script；
- test command、step-by-step bring-up procedure 或實機操作紀錄。

下游 implementation 可以在不改變本文件 contracts 的前提下選擇具體實作；若無法滿足，必須提出 design change 並回到本文件或更上游處理，不得由 source code 或 deployment configuration 靜默取代設計。

## 1.5 Upstream-Issue Handling

06 重構或驗證期間若發現上游問題，應依下列順序處理：

1. 停止受影響 subsystem 的定案，並在 refactoring checklist 標記 `[!]`；
2. user-visible behavior 問題回到 01；
3. system capability 問題回到 02；
4. 可驗證義務、限制或 acceptance 問題回到 03；
5. subsystem allocation、cross-subsystem relationship、operational flow 或 system-wide contract 問題回到 04；
6. 上游修改核准後，再恢復受影響的 05 設計。

以下各 subsystem 的識別、模板與詳細內容，依 `docs/06_subsystem_checklist.md` 逐項討論與核准。

# 2. Uniform Subsystem Section Template

`05_architecture.md` 定義的每個 subsystem 都必須使用本章模板。各節可以依 subsystem 特性使用表格、文字或小型 diagram 表達，但不得省略必要責任；不適用的項目應明確寫出原因，不得以空白代替設計判斷。

一致的模板用於確認相鄰 subsystem 的 producer／consumer、ownership、failure handling 與 verification 能互相閉合，不表示所有 subsystem 必須具有相同的 internal component 數量或 implementation 形式。

## 2.1 Purpose

以簡短文字說明 subsystem 存在的理由，以及它為系統提供的核心價值。Purpose 不重複 implementation 技術，也不擴張 04 已核准的責任。

## 2.2 Architectural Responsibilities

列出從 `05_architecture.md` 承接的 responsibility、requirement allocation 與 relevant system-wide contracts。每項責任必須能追溯至 05，不得由現有 package 或舊版 06 反向產生。

## 2.3 Boundary

明確定義 subsystem 負責與不負責的內容，特別標出容易與相鄰 subsystem 重疊的責任。Boundary 必須維持 04 的 decomposition 與 primary ownership。

## 2.4 Inputs and Dependencies

列出 subsystem 開始及持續運作所需的 data、command、state、resource、external device 與 upstream readiness／validity。每個 dependency 必須指出提供者及使用條件。

## 2.5 Outputs and Authoritative Interfaces

列出 subsystem 對外提供的 data、command、state、result、diagnostics 與 readiness／validity，並指定 authoritative producer。ROS interface 應記錄 interface type、semantic、frame、time、QoS 與有效性條件中適用的部分。

## 2.6 Internal Design

定義 subsystem 內部必要的 component decomposition、各 component 的單一責任及彼此協作方式。優先採用成熟 solution 與 configuration／composition；custom component 必須有已證明的 capability gap 與最小責任範圍。

## 2.7 Configuration and Resource Ownership

定義 parameter、configuration file、runtime resource、device identity 與 persistent artifact 的 owner、consumer、載入時機、validation 及變更邊界。實際數值若尚未由 evidence 確立，應保留為待驗證 configuration，不得在設計中虛構。

## 2.8 Lifecycle and Operational Behavior

定義 configure、activate、ready、operate、deactivate 與 shutdown 中適用的狀態、進入條件、離開條件及 dependency ordering。本節只描述 subsystem-level behavior，不展開 function-level control flow。

## 2.9 Failure, Diagnostics and Safety

定義 failure detection、fault／invalid／degraded semantics、diagnostic output、fault propagation、recovery boundary 與 safe-stop contribution。不得把 process 或 topic 存在視為功能有效，也不得宣告未經 evidence 支持的 safety property。

## 2.10 Implementation Handoff

記錄預計使用的 package、node、plugin、process、launch composition 或成熟方案，以及 implementation 必須遵守的 contracts。Function、class、source-file、完整 deployment artifact 與逐步 procedure 留給下游 implementation design。

## 2.11 Verification

列出證明 subsystem responsibility 的必要 evidence，並依需要區分 source inspection、build、interface、runtime、integration、real-hardware 與 safety verification。Verification 必須驗證資料 semantics、ownership、validity 與 failure behavior，不只驗證 process 啟動或 topic 存在。

## 2.12 Open and Deferred Decisions

集中列出尚未定案、等待官方查證、等待整合測試、等待實機驗證或明確延後至 v0.1 之後的事項。未決事項不得隱含成 approved baseline，也不得阻止與其無關且已具充分 evidence 的責任完成設計。

# 3. Design Status and Evidence Status

05 必須分開記錄「設計是否已定案」與「設計已被何種 evidence 證明」。兩者是互相獨立的判斷，不得以設計核准取代官方查證、整合測試或實機驗證。

狀態應套用至會影響 responsibility、interface、ownership、mature-solution selection、failure behavior 或 verification obligation 的 design decision。純說明文字不需要逐句附加狀態。

## 3.1 Design Status

每項重要 design decision 必須使用下列一種狀態：

| Status | Meaning | Baseline Use |
|---|---|---|
| `Approved` | 已完成討論並核准，且符合 04 responsibility 與 contracts。 | 可以作為 downstream implementation 依據。 |
| `Candidate` | 目前的候選方案，仍需決策、比較或補足設計依據。 | 不得作為已定案 baseline。 |
| `Deferred` | 已明確決定不納入目前 baseline，並記錄延後範圍或重新啟動條件。 | 不得由 v0.1 implementation 偷渡實作。 |

`Approved` 只代表設計決策已核准，不代表 implementation 已完成，也不代表 runtime、integration 或 real hardware 已驗證。

若 `Candidate` 會阻止 subsystem 履行 04 核心 responsibility，該 subsystem 不得宣告完成；不影響 v0.1 核心責任的未決事項可以明確標記 `Deferred`。

## 3.2 Evidence Status

每項重要 design decision 必須依尚缺 evidence 使用下列一個或多個狀態；不同 evidence 缺口可以同時存在：

| Status | Meaning | Completion Evidence |
|---|---|---|
| `Needs Official Verification` | 尚未以 ROS 2 Jazzy、exact package version、hardware vendor 或其他 authoritative source 確認能力與限制。 | 官方文件、API、版本資訊或 vendor baseline 的可追溯引用。 |
| `Needs Integration Test` | 個別設計可能成立，但尚未證明跨 component 或跨 subsystem contracts 能閉合。 | 可重現的整合測試結果與 interface／flow evidence。 |
| `Needs Real-hardware Validation` | 尚未在目標 AMR、感測器、驅動器、運算平台或實際環境證明。 | 可追溯的實機測試結果及適用條件。 |
| `Verified` | 已取得目前聲明所需層級的 evidence。 | 明確記錄 evidence type、來源、版本／環境與驗證範圍。 |

`Verified` 必須說明驗證範圍。例如官方能力已查證，不代表 integration 或 real-hardware behavior 也已驗證。若仍缺其他層級 evidence，必須保留相應的 `Needs ...` 狀態。

Process 存在、node active、topic 存在或單次 message 可讀，只能證明對應的觀察事實；除非 evidence 同時涵蓋 semantics、validity、ownership 與預期行為，否則不得據此將完整 subsystem responsibility 標記為 `Verified`。

## 3.3 Required Decision Record

每項重要 design decision 至少應記錄：

```text
Decision: <決定內容>
Design Status: Approved | Candidate | Deferred
Evidence Status: <一個或多個 evidence status>
Evidence: <文件、測試、實機結果或尚無>
Scope / Conditions: <適用版本、環境與限制>
```

若 evidence 尚無，必須明確寫出 `尚無`，不得省略欄位而讓讀者誤認為已驗證。Evidence 後續更新只改變 evidence status；若 evidence 推翻原 design decision，則必須重新開啟設計討論，必要時依 1.5 節回到上游文件處理。
