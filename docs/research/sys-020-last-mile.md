# SYS-020 Last Mile — Reuse Research

## 1. Research Scope

本筆記研究目前定案的 SYS-020：

> 選定 route exit 未直接到達 Canonical Goal Pose 時，系統應規劃並執行由該 exit 至 Canonical Goal Pose 的安全連接；Canonical Goal Pose 已位於適用的 route exit 時，Last Mile 應視為不需要執行，不得因此判定導航失敗。

相鄰責任邊界保持分離：

- SYS-009／032／033：產生合法且經校驗之 Canonical Goal Pose；
- SYS-011：路徑規劃（`ComputePathToPose`）；
- SYS-013：路線優先之總體策略與三階段組織；
- SYS-015：路徑追蹤（`FollowPath`）；
- SYS-016：到站判定與停止確認（`StoppedGoalChecker`）；
- SYS-019：On Route 階段（沿 Route Graph 移動至 Route Exit）；
- SYS-021：無法自 Route Exit 連接目標點時之降級邊界處理。

本項聚焦於「最後一哩路（Last Mile）之判定、規劃與執行」：
1. 判斷 Canonical Goal Pose 是否已在選定的 Route Exit 容差範圍內；
2. 不在 Exit 時，透過 Planner Server 與 Controller Server 規劃並追蹤由 Exit 至最終目標點之安全連接路徑；
3. 已在 Exit 時，判定為「不需要執行（Not-required）」並直接進入 SYS-016 到站結算，不得判定為失敗；
4. 確保 Last Mile 路徑終點精確保持 Canonical Goal Pose 之位置與朝向（Yaw）。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_planner`（Planner Server / `ComputePathToPose`） + `nav2_controller`（Controller Server / `FollowPath`） + `nav2_behavior_tree`（BT 條件判斷與順序控制） + `StoppedGoalChecker` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 判定 Canonical Goal Pose 與 Route Exit 之容差關係；若未在 Exit 則規劃 Exit 至目標之局部自由空間路徑並執行追蹤；若已在 Exit 則判定為 Not-required 略過執行並順暢進入到站判定（SYS-016）；連接失敗時回報原生失敗供 SYS-021 處理 |
| Known Constraints | Canonical Goal Pose 必須為 global costmap 上的可達非占用點；Last Mile 路徑終點必須精確保留 Canonical Goal Pose 的位置與朝向；Not-required 判定容差需合理配置；Last Mile 追蹤完成後由 SYS-016 之 `StoppedGoalChecker` 進行最終停止與到站結算 |
| Uncovered Gap | **None**；不需要自訂末端銜接演算法或專屬 Last Mile 控制器，完全可由標準 Nav2 組件與 BT 條件分支達成 |
| Configuration / Composition Gap | Route Exit 接近容差（XY/Yaw tolerance）配置；BT XML 設計（包含「檢查是否已在目標/Exit」條件節點與「規劃＋追蹤」執行分支）；Last Mile 終點與 SYS-016 GoalChecker 之銜接配置；連接失敗時轉入 SYS-021 fallback 邊界之連線 |
| Missing Evidence | Target image 之 exact installed versions；在 Route Exit 外不同距離與朝向之目標點規劃與追蹤驗證；目標點剛好在 Exit 容差內直接跳過（Not-required）且成功結算之驗證；目標點周圍被障礙物阻擋時之失敗回報驗證；終點姿態精度與到站平順度量測 |
| MVP Change Candidate | `None` |

成熟方案已完整具備 Last Mile 所需之末端連接、條件略過、目標朝向保真與到站交接能力，完全滿足 SYS-020 需求。

## 3. Last Mile Execution and "Not-required" Semantics

Last Mile 的執行邏輯在 Behavior Tree 中的工作流如下：

```text
               [進入 Last Mile 階段 (AMR 位於 Route Exit)]
                                    │
                                    ▼
           <檢查 Canonical Goal Pose 是否已在 Route Exit 容差內?>
                                    │
                        ┌───────────┴───────────┐
                       YES                      NO
                        │                       │
                        ▼                       ▼
               [Not-required (跳過)]   [ComputePathToPose(Exit -> Goal)]
                        │                       │
                        │                       ▼
                        │               [FollowPath(Path)]
                        │                       │
                        └───────────┬───────────┘
                                    │
                                    ▼
             [進入到站判定與停止確認 (SYS-016 / StoppedGoalChecker)]
                                    │
                                    ▼
                       [Navigation Success (SYS-017)]
```

1. **Not-required 判定**：
   - 透過 BT 條件節點比對 Route Exit 座標與 Canonical Goal Pose 座標；
   - 若兩者在設定容差範圍內（例如目標點本就設在路網節點上），該條件成立，Last Mile 立即視為完成（Not-required），不觸發額外路徑規劃與移動，直接推進至 SYS-016 進行到站確認。
2. **安全連接規劃與追蹤**：
   - 若目標點在路網外（離 Exit 有一定距離），呼叫 Planner Server 產生由 Route Exit 至 Canonical Goal Pose 的無碰撞路徑；
   - 透過 Controller Server 執行 `FollowPath` 帶領 AMR 駛向目標點；
   - 路徑終點保持 Canonical Goal Pose 之 exact position 與 orientation。
3. **失敗處理與邊界銜接**：
   - 若 Exit 至目標點之間被障礙物完全阻擋或目標不可達，Last Mile 回報規劃/追蹤失敗；
   - 決策層捕捉此失敗後，判定符合 SYS-021 之 eligibility（`所有可用 route-assisted candidates 均無法由 route exit 透過 Last Mile 安全連接 Canonical Goal Pose`），觸發安全煞停並回報 Free-space Fallback unavailable。

## 4. Responsibility and Requirement Boundary

| 需求項目 | 責任範圍 | 與 Last Mile (SYS-020) 的邊界 |
|---|---|---|
| **SYS-013** | **Strategy**：路線優先總體策略 | 協調整體三階段移動，引導進入 Last Mile |
| **SYS-016** | **Goal Completion**：到站判定與停止確認 | 接收 Last Mile 的終點追蹤結果，驗證 pose 與 stopped 條件 |
| **SYS-019** | **On Route**：路網主線移動 | 將 AMR 帶至 Exit 點後，交接予 SYS-020 |
| **SYS-020** | **Last Mile**：Route Exit 至目標點銜接 | 負責 Exit 到 Goal 的末端連接或判定 Not-required 略過 |
| **SYS-021** | **Fallback**：無可用路線之降級處理 | 當 Last Mile 無法連接目標點時接手失敗處理 |

## 5. Configuration and Evidence Requirements

### Configuration / composition

- 配置 Route Exit 與 Goal 接近容差（`exit_xy_tolerance`, `exit_yaw_tolerance`）；
- 配置 Planner Plugin 與 Controller Plugin 確保末端微調與朝向對齊精度；
- 設計 BT XML 中的 Last Mile 子樹（條件判定 -> 略過 / 規劃+追蹤 -> SYS-016 StoppedGoalChecker）；
- 確保 Last Mile 失敗時正確將 error code 傳遞予 SYS-021 處理。

### Integration and real-hardware evidence

- 記錄 target image 之 exact versions（ROS 2 Jazzy、Navigation2 1.3.12-1）；
- **離網目標測試**：目標點位於離 Exit 1m、3m、5m 及不同指定 Yaw 朝向下，驗證能順利規劃並追蹤至目標點，且最終姿態符合要求；
- **在網目標測試（Not-required）**：目標點剛好就在 Exit 點上，驗證系統不重複做 Last Mile 移動，直接進入 SYS-016 判定且導航不失敗；
- **阻塞測試**：在 Exit 至目標點之間設置障礙物使連接路徑不通，驗證系統回報規劃失敗並由 SYS-021 接手；
- **姿態精度量測**：量測抵達目標點後的 XY 誤差與 Yaw 朝向誤差，確保符合精度規範。

## 6. Primary-source Evidence

### 6.1 Planner and Controller Action Servers

- **Evidence Type:** official upstream source and interfaces
- **Sources:** [`ComputePathToPose.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputePathToPose.action)；[`FollowPath.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/FollowPath.action)；[`planner_server.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_planner/src/planner_server.cpp)；[`controller_server.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/src/controller_server.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** Planning from route exit to canonical goal pose, preserving goal orientation, and executing path tracking.
- **Access Date:** 2026-08-15

### 6.2 Stopped Goal Checker and BT Completion Chain

- **Evidence Type:** official upstream source
- **Sources:** [`stopped_goal_checker.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/plugins/stopped_goal_checker.cpp)；[`navigate_to_pose_w_replanning_and_recovery.xml` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** Goal arrival verification, translation and rotational stop verification, and BT action success completion.
- **Access Date:** 2026-08-15

## 7. Recommended 04 Record

```text
SYS-020 Last Mile
Candidate Mature Solution: Navigation2 Planner Server (ComputePathToPose) + Controller Server (FollowPath) + Behavior Tree condition branching + StoppedGoalChecker (Jazzy 1.3.12-1)
Coverage Status: Fully Covered
Covered Scope: evaluating whether Canonical Goal Pose is within Route Exit tolerance; planning and executing safe connection from Route Exit to Canonical Goal Pose; preserving goal orientation; skipping execution (Not-required) and transitioning to SYS-016 when Goal is already at Exit; returning failure for fallback handling when goal is unreachable
Custom Behavior Gap: None
Configuration / Composition Gap: Route Exit proximity tolerance configuration; BT XML subtree branching for exit-goal check, connection planning/tracking, and handoff to SYS-016 StoppedGoalChecker; failure routing to SYS-021
Evidence Gap: installed versions; planning/tracking from Route Exit to various off-route goal poses and orientations; not-required bypass verification when goal is at Exit; blocked-goal failure reporting; arrival position/yaw accuracy
MVP Change Candidate: None
```
