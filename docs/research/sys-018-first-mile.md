# SYS-018 First Mile — Reuse Research

## 1. Research Scope

本筆記研究目前定案的 SYS-018：

> 目前位姿不在選定 route entry 時，系統應規劃並執行由目前位姿至該 entry 的安全連接；目前位姿已位於適用的 route entry 時，First Mile 應視為不需要執行，不得因此判定導航失敗。

相鄰責任邊界保持分離：

- SYS-010：提供目前地圖定位位姿（Current Pose）；
- SYS-011：單一 active stage 路徑規劃（`ComputePathToPose`）；
- SYS-013：Route-preferred 移動策略與整體三階段組織；
- SYS-015：active stage 路徑追蹤（`FollowPath`）；
- SYS-019：On Route 階段（沿 Route Graph 移動）；
- SYS-020：Last Mile 階段（Route Exit 至目標點連接）；
- SYS-021：無法連接可用 route entry 時之降級邊界處理。

本項聚焦於「第一哩路（First Mile）之判定、規劃與執行」：
1. 判斷 AMR 當前位姿是否已在選定的 Route Entry 容差範圍內；
2. 不在 Entry 時，透過 Planner Server 與 Controller Server 規劃並追蹤安全連接路徑；
3. 已在 Entry 時，判定為「不需要執行（Not-required）」並順暢推進至 On Route 階段，不得判定為失敗。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_planner`（Planner Server / `ComputePathToPose`） + `nav2_controller`（Controller Server / `FollowPath`） + `nav2_behavior_tree`（BT 條件判斷與順序控制） |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 判定 Current Pose 與 Route Entry 之距離與朝向關係；若未在 Entry 則規劃起點至 Entry 之局部自由空間路徑並執行追蹤；若已在 Entry 則判定為 Not-required 並成功放行至 On Route 階段；連接失敗時回報原生失敗供 SYS-021 處理 |
| Known Constraints | Route Entry 必須為 Route Graph 上的有效節點／位姿；連接路徑受限於 global costmap 之障礙物占用；Not-required 判定容差必須合理配置（避免過嚴導致不必要微調，或過寬導致未進入路網範圍）；First Mile 成功僅代表抵達 Entry，不代表整體導航完成 |
| Uncovered Gap | **None**；不需要自訂銜接演算法或專屬 First Mile 控制器，完全可由標準 Nav2 組件與 BT 條件分支達成 |
| Configuration / Composition Gap | Route Entry 抵達判定門檻（XY/Yaw tolerance）配置；BT XML 設計（包含「檢查是否已在 Entry」條件節點與「規劃＋追蹤」執行分支）；連接失敗時轉入 SYS-021 fallback 邊界之連線 |
| Missing Evidence | Target image 之 exact installed versions；在 Route Entry 外不同距離與角度下之規劃與追蹤驗證；在 Route Entry 容差內直接跳過（Not-required）且成功進入 On Route 之驗證；Entry 被障礙物阻擋時之失敗回報驗證；實機銜接平順度與過渡時延量測 |
| MVP Change Candidate | `None` |

成熟方案已完整具備 First Mile 所需之起訖連接、條件跳過與階段轉換能力，透過標準 Nav2 BT 組裝即可滿足需求。

## 3. First Mile Execution and "Not-required" Semantics

First Mile 的執行邏輯在 Behavior Tree 中的工作流如下：

```text
               [進入 First Mile 階段]
                         │
                         ▼
        <檢查 Current Pose 是否已在 Route Entry?>
                         │
             ┌───────────┴───────────┐
            YES                      NO
             │                       │
             ▼                       ▼
    [Not-required (跳過)]    [ComputePathToPose(Pose -> Entry)]
             │                       │
             │                       ▼
             │               [FollowPath(Path)]
             │                       │
             └───────────┬───────────┘
                         │
                         ▼
               [推進至 On Route 階段 (SYS-019)]
```

1. **Not-required 判定**：
   - 透過 BT 條件節點（如 `DistanceTraveled` / 自訂距離比較或 BT Decorator / GoalChecker），比較目前位姿與選定 Route Entry 的空間距離；
   - 若距離與角度在設定容差範圍內，該條件評估為成功，First Mile 立即視為完成（Not-required），不觸發額外的原地微調或底盤移動，直接進入 On Route 階段。
2. **安全連接規劃與追蹤**：
   - 若位姿超出容差，則呼叫 Planner Server 產生由 Current Pose 至 Route Entry 的無碰撞路徑；
   - 透過 Controller Server 執行 `FollowPath` 移動 AMR 至 Entry；
   - 抵達 Entry 後，First Mile 結束並交接予 On Route。
3. **失敗處理與邊界銜接**：
   - 若規劃失敗（如起點被障礙物包圍或無路徑可達 Entry）或追蹤超時／受阻，First Mile 回報失敗；
   - 決策層捕捉此失敗後，判定符合 SYS-021 之 eligibility（`Current Pose 無法連接任何可用 route entry`），觸發安全煞停並回報 Free-space Fallback unavailable。

## 4. Responsibility and Requirement Boundary

| 需求項目 | 責任範圍 | 與 First Mile (SYS-018) 的邊界 |
|---|---|---|
| **SYS-013** | **Strategy**：路線優先總體策略 | 決定整體需採用 route-assisted 方案，並調度 First Mile |
| **SYS-018** | **First Mile**：起點至 Route Entry 銜接 | 專注於將 AMR 安全移動至 Entry，或判定已在 Entry 予以跳過 |
| **SYS-019** | **On Route**：路網上循跡 | 接收抵達 Entry 的 AMR，開始沿 Route Graph 移動 |
| **SYS-021** | **Fallback**：無可用路線之降級處理 | 當 First Mile 無法連接任何可用 Entry 時承接失敗處理 |

## 5. Configuration and Evidence Requirements

### Configuration / composition

- 配置 Route Entry 接近容差（`entry_xy_tolerance`, `entry_yaw_tolerance`）；
- 配置 First Mile 專用或共用之 Planner Plugin（如 NavFn / Smac Planner）與 Controller Plugin；
- 設計 BT XML 中的 First Mile 子樹（條件判定 -> 略過 / 規劃+追蹤 -> 推進下一階段）；
- 確保 First Mile 失敗時正確將 error code 傳遞予 SYS-021 處理。

### Integration and real-hardware evidence

- 記錄 target image 之 exact versions（ROS 2 Jazzy、Navigation2 1.3.12-1）；
- **離網起步測試**：AMR 位於離 Entry 1m、3m、5m 及不同偏角位置，驗證能順利規劃並追蹤至 Entry；
- **在網起步測試（Not-required）**：AMR 已經停在 Entry 點上或容差內，下發導航，驗證系統不重複做 First Mile 移動，直接進入 On Route 階段且導航不失敗；
- **阻塞測試**：在 Entry 前設置障礙物使連接路徑不通，驗證系統回報規劃失敗並由 SYS-021 接手；
- **銜接時序測試**：量測 First Mile 抵達 Entry 後切換至 On Route 的過渡延遲與速度連續性。

## 6. Primary-source Evidence

### 6.1 Planner and Controller Action Servers

- **Evidence Type:** official upstream source and interfaces
- **Sources:** [`ComputePathToPose.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputePathToPose.action)；[`FollowPath.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/FollowPath.action)；[`planner_server.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_planner/src/planner_server.cpp)；[`controller_server.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/src/controller_server.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** Standard planning from arbitrary start to specified goal pose, and standard path tracking execution.
- **Access Date:** 2026-08-15

### 6.2 Behavior Tree Branching and Condition Nodes

- **Evidence Type:** official upstream source
- **Sources:** [`nav2_behavior_tree` plugins](https://github.com/ros-navigation/navigation2/tree/1.3.12/nav2_behavior_tree/plugins)；[`goal_reached_condition.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_behavior_tree/plugins/condition/goal_reached_condition.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** Condition evaluation, subtree skipping, and sequential stage transition.
- **Access Date:** 2026-08-15

## 7. Recommended 04 Record

```text
SYS-018 First Mile
Candidate Mature Solution: Navigation2 Planner Server (ComputePathToPose) + Controller Server (FollowPath) + Behavior Tree condition branching (Jazzy 1.3.12-1)
Coverage Status: Fully Covered
Covered Scope: evaluating whether Current Pose is within Route Entry tolerance; planning and executing safe connection from Current Pose to Route Entry when needed; skipping execution (Not-required) and seamlessly transitioning to On Route stage when already at Entry; returning failure upon unreachable entry for fallback handling
Custom Behavior Gap: None
Configuration / Composition Gap: Route Entry proximity tolerance configuration; BT XML subtree branching for entry-check, connection planning/tracking, and stage handoff; failure routing to SYS-021
Evidence Gap: installed versions; planning/tracking from various off-route poses; not-required bypass verification when starting at entry; blocked-entry failure reporting; transition latency to On Route stage
MVP Change Candidate: None
```
