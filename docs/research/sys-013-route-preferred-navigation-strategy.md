> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-013 Route-preferred Navigation Strategy — Reuse Research

## 1. Research Scope

本筆記研究目前定案的 SYS-013：

> 系統應根據目前位姿、Canonical Goal Pose 與有效 Route Graph 建立可安全執行的 route-assisted movement，並優先使用適用的 Route Graph 範圍。存在有效且可安全執行的 route-assisted solution 時，系統不得選擇完整 free-space movement。

相鄰責任邊界保持分離：

- SYS-009／032／033：產生標準合法之 Canonical Goal Pose；
- SYS-010：提供目前地圖定位位姿（Current Pose）；
- SYS-011：單一 active stage 之路徑規劃（`ComputePathToPose`）；
- SYS-014：環境障礙物感知與動態避障；
- SYS-015：active stage 之路徑追蹤（`FollowPath`）；
- SYS-016：到站判定與停止確認；
- SYS-017／025：整體導航結果回報與取消；
- SYS-018：First Mile（起點至 Route Entry 連接）；
- SYS-019：On Route Navigation（沿 Route Graph 移動與約束遵守）；
- SYS-020：Last Mile（Route Exit 至目標點連接）；
- SYS-021：Free-space Fallback 邊界與 v0.1 禁用回報。

本項聚焦於「路線優先（Route-preferred）之移動策略建立」，即在規劃與導航決策層，優先搜尋並組合由 Route Graph 支援之路徑方案，並在存在可用 route-assisted 方案時，禁止退化至全域自由空間規劃（full free-space movement）。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_route`（Route Server / `ComputeRoute.action`） + `nav2_planner`（Planner Server） + `nav2_behavior_tree` BT 組裝 |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 / `nav2_route` Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 依據 Current Pose、Canonical Goal Pose 與 Route Graph 搜尋並建立 route-assisted movement；在圖論路網可用範圍內優先採用 Route Graph；透過 BT 流程組合確保優先使用 route 方案並禁止在有可用 route 時執行完整 free-space 導航 |
| Known Constraints | Route Graph 必須為合法且已載入之資源；route-assisted 方案之可行性需經 global/local costmap 檢查；在 v0.1 階段，BT 流程不得配置全局 free-space fallback，無可用 route 時應依 SYS-021 終止 |
| Uncovered Gap | **None**；不需要自行開發圖論搜尋演算法、自訂 Route Server 或客製化規劃核心 |
| Configuration / Composition Gap | Route Server 參數與 Edge Scorer 配置；BT XML 結構設計（串接 Route 搜尋、三階段判定與 fallback 邊界）；Route Entry / Exit 搜尋半徑與連接條件配置 |
| Missing Evidence | Target image 之 `nav2_route` 與 Nav2 exact installed versions；實際場域地圖與 Route Graph 拓撲之搜尋正確性驗證；驗證在有 route 情況下確實產生 route-assisted 移動；驗證無 route 時不會靜默轉為純 free-space 移動；實機規劃延遲與路徑可行性測試 |
| MVP Change Candidate | `None` |

成熟方案已完整提供圖論路由搜尋（`nav2_route`）與多階段路徑規劃能力，透過標準 Nav2 BT 組裝即可完全滿足 SYS-013 之策略原則。

## 3. Route-preferred Strategy Principles

在 Navigation2 體系下，Route-preferred 移動策略的建立流程如下：

```text
[Current Pose] + [Canonical Goal Pose] + [Active Route Graph]
                           │
                           ▼
          [nav2_route::RouteServer / ComputeRoute]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
   [Route-assisted Found]      [No Valid Route Available]
             │                           │
             ▼                           ▼
  [Execute 3-Stage Pipeline]   [Trigger SYS-021 Fallback Boundary]
  (First Mile -> On Route -> Last Mile)  (v0.1: Terminate & Report Unavailable)
```

1. **Route-assisted 方案構成**：
   - 透過 `nav2_route` 之 `ComputeRoute`，以起點與終點位姿對 Route Graph 進行拓撲搜尋；
   - 方案包含：起點至 entry node/edge（First Mile）、沿圖論 edge 移動（On Route）、以及 exit node/edge 至終點（Last Mile）；
   - 各階段路徑可由 Route Server 產生或由 Planner Server 配合生成。
2. **優先性保證（Preference Policy）**：
   - 導航決策大腦（BT Navigator）將 `ComputeRoute` 作為主要規劃入口；
   - 只要存在有效且安全可行的 route 方案，系統即採用該方案執行三階段移動。
3. **禁止完整 Free-space 移動（Prohibition of Unassisted Movement）**：
   - 標準 Nav2 預設 BT 是直接對全域 costmap 做 `ComputePathToPose`（純自由空間規劃）；
   - 本專案在 v0.1 依 SYS-013 與 SYS-021 規範，在 BT 組裝中**不配置**全局 free-space fallback 流程；
   - 當 route 方案存在時，不進行全局自由空間規劃；若 route 方案不可行或不存在，則直接轉入 SYS-021 終止，嚴格防止 AMR 在非預期路網外任意穿行。

## 4. Subsystem and Requirement Boundary

| 需求 | 角色與責任 | 本項（SYS-013）關係 |
|---|---|---|
| **SYS-013** | **Strategy & Policy Owner**：定義路線優先策略、禁止非必要自由移動 | 本項核心評估標的 |
| **SYS-018** | **First Mile Stage**：起點至 Route Entry 連接執行 | SYS-013 策略下之第一階段具體執行 |
| **SYS-019** | **On Route Stage**：沿 Route Graph 拓撲與約束移動 | SYS-013 策略下之第二階段具體執行 |
| **SYS-020** | **Last Mile Stage**：Route Exit 至 Canonical Goal 連接執行 | SYS-013 策略下之第三階段具體執行 |
| **SYS-021** | **Fallback Boundary**：無可用路線時之終止與回報 | SYS-013 策略無法成立時之邊界處理 |

SYS-013 作為「策略頂層」，負責約束與引導後續三階段（SYS-018～020）及降級邊界（SYS-021），不重複實作各階段內部細部邏輯。

## 5. Configuration and Evidence Requirements

### Configuration / composition

- 配置 `nav2_route::RouteServer` 生命週期節點及其圖論解析器（支援專案 Route Graph 格式）；
- 配置 Edge Scorer 插件以支援適當的距離與成本權重計算；
- 設計專案專用之 Behavior Tree XML，確保：
  1. 優先觸發 `ComputeRoute` 進行圖論路網搜尋；
  2. 依序執行 First Mile、On Route、Last Mile 組合；
  3. 剔除預設 BT 中無條件回退至全局 `ComputePathToPose` 的 fallback 分支；
- 配置 Route Entry / Exit 搜尋之最大容許連接距離與安全門檻。

### Integration and real-hardware evidence

- 記錄 target image 之 exact versions（ROS 2 Jazzy、`nav2_route` 1.3.12-1、`nav2_planner` 1.3.12-1）；
- **路線優先驗證**：在存在有效 Route Graph 的測試場域中下發導航目標，驗證產生的移動軌跡遵循 Route Graph 拓撲，而非在空曠處任意切西瓜（full free-space）；
- **無路線邊界驗證**：在孤立目標或無連通路網情境下，驗證系統正確拒絕純 free-space 導航，並轉入 SYS-021 終止；
- **障礙阻擋重選驗證**：驗證當某一路段被阻擋時，Route Server 嘗試搜尋替代路線之行為；
- **規劃時延量測**：量測 `ComputeRoute` 與各 stage planning 之運算時間，確保符合即時導航需求。

## 6. Primary-source Evidence

### 6.1 `nav2_route` Route Server and Action Interface

- **Evidence Type:** official upstream source and ROS 2 Jazzy documentation
- **Sources:** [`nav2_route` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/tree/1.3.12/nav2_route)；[`ComputeRoute.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputeRoute.action)；[Nav2 Route Server Documentation](https://docs.nav2.org/)
- **Exact Version / Revision:** Navigation2 / `nav2_route` 1.3.12 / Jazzy release 1.3.12-1
- **Observed Scope:** Graph-based route planning, `ComputeRoute` action server, GeoJSON/OSM route graph parsing, and routing plugins.
- **Access Date:** 2026-08-15

### 6.2 Nav2 Behavior Tree Orchestration

- **Evidence Type:** official upstream source
- **Sources:** [`nav2_behavior_tree` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/tree/1.3.12/nav2_behavior_tree)；[`navigate_to_pose.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/src/navigators/navigate_to_pose.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** BT control nodes, Action nodes, and navigator pipeline sequence enabling route-preferred strategy enforcement.
- **Access Date:** 2026-08-15

## 7. Recommended 04 Record

```text
SYS-013 Route-preferred Navigation Strategy
Candidate Mature Solution: ROS 2 Jazzy Navigation2 1.3.12-1 nav2_route (Route Server / ComputeRoute) + nav2_planner (Planner Server) + nav2_behavior_tree composition
Coverage Status: Fully Covered
Covered Scope: route-assisted movement generation using Current Pose, Canonical Goal Pose, and valid Route Graph; prioritizing route graph topology; preventing unassisted full free-space movement when route solution exists
Custom Behavior Gap: None
Configuration / Composition Gap: RouteServer configuration and edge scoring plugins; project BT XML composition enforcing route-preferred sequencing and omitting pure free-space fallback; entry/exit connection distance thresholds
Evidence Gap: installed versions; route graph loading and topological path search; route preference verification vs. full free-space; rejection of unassisted movement when route is missing; planning latency
MVP Change Candidate: None
```
