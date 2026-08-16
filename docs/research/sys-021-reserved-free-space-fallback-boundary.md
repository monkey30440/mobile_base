# SYS-021 Reserved Free-space Fallback Boundary — Reuse Research

## 1. Research Scope

本筆記研究目前定案的 SYS-021：

> 系統應保留下列 Free-space Fallback eligibility，以供後續版本擴充：
> - Current Pose 無法連接任何可用 route entry。
> - Active、valid Route Graph 無法提供通往 Canonical Goal Pose 方向的可用 route。
> - On Route movement 因目前環境阻塞而無法維持，且重新選擇 Route Graph route 仍失敗。
> - 所有可用 route-assisted candidates 均無法由 route exit 透過 Last Mile 安全連接 Canonical Goal Pose。
> 
> v0.1 不得執行 Free-space Fallback。符合上述任一 eligibility 且已無可用 route-assisted solution 時，系統應終止導航、嘗試使底盤停止，並回報 Free-space Fallback unavailable。Navigation Resource、Navigation Target 或 localization 的缺失、無效或不相容仍屬其各自 failure boundary，不構成 fallback eligibility。

相鄰責任邊界保持分離：

- SYS-007／024：地圖與資源載入邊界；
- SYS-010：定位有效性邊界；
- SYS-013：路線優先總體策略；
- SYS-017／025：導航結果回報與取消處理；
- SYS-018：First Mile（起點至 Entry 連接）；
- SYS-019：On Route（路網主線移動）；
- SYS-020：Last Mile（Exit 至目標點連接）；
- SYS-032／033：站點解析與目標合法性驗證邊界。

本項聚焦於：
1. 辨識 4 種「無可用路網輔助方案」之降級資格（Fallback Eligibility）；
2. 落實 v0.1 禁用全局自由空間降級之規範，在觸發時有序終止導航、下發零速煞停並回報結果；
3. 明確排他性邊界，確保非路線因素之錯誤不被混淆為 fallback eligibility。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_behavior_tree`（BT 流程與失敗捕捉） + `nav2_route` / `nav2_planner` / `nav2_controller` 失敗傳遞機制 + Action terminal `ABORTED` 結果回報 |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 捕捉 First Mile 失敗、Route 搜尋無路、On Route 受阻重選失敗、Last Mile 失敗等 4 類情境；在 BT 決策層落實 v0.1 禁用全局 free-space fallback 之約束；終止導航行為樹、主動發布零速命令煞停、回傳標準 `ABORTED` 狀態與失敗資訊；保持前置驗證與定位失敗之排他性邊界 |
| Known Constraints | v0.1 階段不執行任何未受約束的全域自由空間脫困移動；失敗回報需透過 Action Result payload 或專案終端介面呈現；前置資源/目標/定位錯誤必須在進入導航前或由各自節點獨立攔截，不得誤入此處 |
| Uncovered Gap | **None**；不需要客製化降級管理器或專門的 fallback 守護進程，標準 Nav2 BT 流程組裝即可完全滿足 |
| Configuration / Composition Gap | 專案 BT XML 結構設計（去除預設 BT 中無條件回退至全局 `ComputePathToPose` 的分支，將路網失敗直接串接至終止與零速發布）；BT blackboard error code 設定與映射至 `Free-space Fallback unavailable` |
| Missing Evidence | Target image 之 exact installed versions；針對 4 種 eligibility 條件的故障注入測試（起點堵死、路網無路、中途堵死無替代、出口堵死）；驗證在失敗時絕不產生全局自由空間軌跡；驗證底盤平順煞停時序；Terminal 失敗訊息呈現驗證 |
| MVP Change Candidate | `None` |

成熟方案已原生具備多層級失敗捕捉、行為樹終止、零速發布與 Action 失敗回報機制，透過專案 BT 組裝即可 100% 滿足 SYS-021 規範。

## 3. Fallback Eligibility and Behavior Tree Flow

在 Navigation2 體系下，SYS-021 降級邊界的調度與終止流程如下：

```text
[導航執行流程]
     ├── (1) First Mile 連接失敗 (起點無可用 Entry) ───────────┐
     ├── (2) nav2_route 搜尋無可用路線 (路網無通路) ────────────┼──> [捕捉 Route-assisted Failure]
     ├── (3) On Route 受阻且重選替代路線失敗 (中途全封死) ─────┤                  │
     └── (4) Last Mile 連接失敗 (出口無法至目標) ──────────────┘                  │
                                                                                   ▼
                                                             <v0.1 策略約束：禁止 Free-space Fallback>
                                                                                   │
                                                                                   ▼
                                                                        [BT halt & 下發零速度]
                                                                                   │
                                                                                   ▼
                                                                [回報 STATUS_ABORTED / Unavailable]
```

1. **4 類 Eligibility 的辨識與捕捉**：
   - **Condition 1**：First Mile 子樹呼叫 `ComputePathToPose` 至所有候選 Entry 均回傳失敗；
   - **Condition 2**：Route Server 之 `ComputeRoute` 回傳 `NO_ROUTE`（路網拓撲不連通）；
   - **Condition 3**：`FollowPath` 在 On Route 遇到障礙回傳追蹤失敗，BT 嘗試重觸發 `ComputeRoute` 尋找替代路網仍回傳失敗；
   - **Condition 4**：Last Mile 子樹呼叫 `ComputePathToPose` 由 Exit 至目標點回傳失敗。
2. **v0.1 禁用 Free-space Fallback 的實作保證**：
   - 標準 Nav2 BT 預設會在路徑失敗時呼叫 `ComputePathToPose` 直接對全地圖做 A* 規劃；
   - 本專案在 Behavior Tree XML 中**移除**該全局自由空間 fallback 分支；
   - 一旦 route-assisted 方案失敗，BT 直接進入失敗結算節點，確保系統在任何情況下都不會在場域內隨意穿行。
3. **終止與停止保證**：
   - BT 終止時觸發 Action Server 的清理流程，Controller Server 發布零速（`linear=0, angular=0`）；
   - Action Server 標記任務為 `STATUS_ABORTED`，並將對應的 error code 封裝於 result payload 送回。

## 4. Exclusion Boundary (排他性邊界)

SYS-021 明文規定下列前置或底層故障**不構成** Fallback Eligibility：

| 故障類別 | 所屬邊界 / 需求 | 處理方式 |
|---|---|---|
| **Station ID 不存在 / 語法錯誤** | SYS-032 / SYS-008 | 終端解析階段直接拒絕，不啟動導航 |
| **目標座標包含 NaN / 超出邊界** | SYS-033 / SYS-009 | 前置校驗階段攔截並拒絕，不啟動導航 |
| **地圖/路網檔案損毀或缺失** | SYS-007 / SYS-024 | 初始化載入階段報錯，阻止進入 Navigation Mode |
| **AMCL 地圖定位遺失或未初始化** | SYS-010 | 定位層回報無效，導航不具備啟動前提 |

這些非路線問題有其獨立的 failure contract，不會進入 SYS-021 的路網決策流程。

## 5. Configuration and Evidence Requirements

### Configuration / composition

- 專案 Behavior Tree XML 設計：
  - 將三階段路網移動封裝於主要序列；
  - 徹底剔除任何包含全局 `ComputePathToPose` 的 Free-space Fallback 分支；
  - 在失敗時導向停止命令與 error code 設定節點；
- 配置 Route Server 重選路線之重試次數與超時參數；
- Terminal 端解析 Action Result payload，正確呈現 `Free-space Fallback unavailable` 提示。

### Integration and real-hardware evidence

- 記錄 target image 之 exact versions（ROS 2 Jazzy、Navigation2 1.3.12-1）；
- **4 大情境故障注入測試**：
  1. *起點堵塞*：在 AMR 周圍設置障礙物使無法連接 Entry，驗證觸發 SYS-021 終止；
  2. *路網斷開*：給予跨越孤立路網的目標，驗證 Route Server 報錯並觸發 SYS-021；
  3. *主線中途堵死*：在行駛中封閉所有可用走道，驗證重選失敗後觸發 SYS-021；
  4. *終點堵塞*：在目標周圍設置障礙物使 Exit 無法到達目標，驗證觸發 SYS-021；
- **行為驗證**：驗證在上述所有失敗情境下，AMR 均立即煞停，**完全沒有**出現全局自由空間切西瓜軌跡；
- **排他性邊界驗證**：驗證輸入非法目標或缺少地圖時，直接由前置模組攔截，不進入 SYS-021。

## 6. Primary-source Evidence

### 6.1 Behavior Tree Fallback and Control Nodes

- **Evidence Type:** official upstream source and documentation
- **Sources:** [`nav2_behavior_tree` package](https://github.com/ros-navigation/navigation2/tree/1.3.12/nav2_behavior_tree)；[Nav2 Behavior Tree concepts](https://docs.nav2.org/behavior_trees/index.html)；[`pipeline_sequence.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_behavior_tree/plugins/control/pipeline_sequence.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy release 1.3.12-1
- **Observed Scope:** BT control flow, fallback handling, recovery node dispatch, and graceful termination.
- **Access Date:** 2026-08-15

### 6.2 Action Failure and Stop Semantics

- **Evidence Type:** upstream exact-tag source
- **Sources:** [`bt_action_server_impl.hpp` at 1.3.12](https://api.nav2.org/nav2-jazzy/html/bt__action__server__impl_8hpp_source.html)；[`controller_server.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/src/controller_server.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** BT failure triggers action abort, publishes zero velocity, and returns error payload.
- **Access Date:** 2026-08-15

## 7. Recommended 04 Record

```text
SYS-021 Reserved Free-space Fallback Boundary
Candidate Mature Solution: Navigation2 Behavior Tree composition + nav2_route / nav2_planner / nav2_controller failure propagation + Action ABORTED result (Jazzy 1.3.12-1)
Coverage Status: Fully Covered
Covered Scope: identifying 4 fallback eligibility conditions across First Mile, Route Planning, On Route tracking, and Last Mile; enforcing v0.1 prohibition of unassisted free-space fallback in BT composition; terminating navigation, publishing zero velocity to stop base, and returning standard ABORTED result; maintaining clear exclusion boundary for pre-navigation failures
Custom Behavior Gap: None
Configuration / Composition Gap: BT XML design omitting global free-space fallback subtrees and wiring route failures directly to stop and ABORTED result; mapping BT error codes to Free-space Fallback unavailable in terminal presentation
Evidence Gap: installed versions; fault injection tests for all 4 eligibility conditions; verification of immediate stopping without unassisted free-space movement; exclusion boundary verification for invalid targets and missing maps; terminal presentation of unavailable status
MVP Change Candidate: None
```
