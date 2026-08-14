# SYS-011 Path Planning — Reuse Research

## 1. Research Scope

本筆記只研究目前定案的SYS-011：

> 系統應使用目前位姿與 active navigation stage 的目標，透過 Navigation2 產生有效且非空的路徑。無法產生路徑時，系統不得開始該 stage 的路徑追蹤，並應回報 Navigation2 原生規劃失敗結果。

SYS-011只要求單一active stage的path computation與planning-to-tracking gate。下列責任不再重複計入本項：

- route-preferred strategy：SYS-013；
- path tracking與stage transition：SYS-015；
- navigation result：SYS-017；
- First Mile／On Route／Last Mile與跨stage continuity：SYS-018～020；
- route-assisted alternatives與Free-space Fallback eligibility：SYS-021。

候選成熟方案為ROS 2 Jazzy Navigation2 1.3.12-1的`nav2_planner` Planner Server、`nav2_core::GlobalPlanner` plugin interface及標準Behavior Tree planning-to-tracking sequence。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | Navigation2 Jazzy 1.3.12-1 Planner Server + selected `nav2_core::GlobalPlanner` plugin + standard BT Sequence |
| Coverage Status | **Fully Covered** |
| Mature Coverage | current robot pose或explicit start至active-stage goal的path computation；global costmap與TF handling；empty-path rejection；`nav_msgs/Path` success result；native planning error code/message；planning失敗時不進入後續`FollowPath` |
| Custom Behavior Gap | **None** |
| Configuration / Composition Gap | planner plugin、planner ID、global costmap、footprint、frames／TF、planning timeout與standard BT planning-to-tracking sequence |
| Missing Evidence | exact installed versions；selected planner；實際stage inputs與paths；TF／costmap／failure injection；planning失敗時zero `FollowPath` start；實機latency與path suitability |
| MVP Change Candidate | `None` |

目前需求已對齊Navigation2原生抽象，不需要stage-aware orchestration、alternative manager、自訂planner或project failure taxonomy。

## 3. Native Coverage

### 3.1 Current pose and active-stage goal

`ComputePathToPose.action`包含goal、optional start、planner ID與`use_start`：

- `use_start=false`時，Planner Server從global costmap取得目前robot pose；
- `use_start=true`時，可由caller明確提供stage start；
- goal使用標準`geometry_msgs/msg/PoseStamped`，可直接承接active navigation stage的目標。

Planner Server把start與goal轉換至global frame，等待global costmap current，再呼叫selected `nav2_core::GlobalPlanner::createPlan()`。這完整覆蓋目前位姿至active-stage goal的規劃輸入。

### 3.2 Valid and non-empty path

Planner Server要求plugin回傳`nav_msgs/msg/Path`。若path為空，Server視為`NoValidPathCouldBeFound`而失敗；成功結果包含path及planning time。

SYS-011的「有效」限於：selected planner根據當時configured global costmap、robot footprint／kinematic constraints與plugin規則接受並產生non-empty path。它不是physical-safety certification；障礙物資料責任屬SYS-014，實際path可追蹤性屬SYS-015。

### 3.3 Native planning failure result

Navigation2 1.3.12的`ComputePathToPose`結果提供`error_code`與`error_msg`。Planner Server可回報的原生類別包含：

- invalid planner；
- TF error；
- start／goal outside map；
- start／goal occupied；
- timeout；
- no valid path；
- unknown planning exception。

因此SYS-011只需保留並向上轉送原生結果，不需建立額外failure taxonomy。

### 3.4 Planning failure does not start tracking

Navigation2標準NavigateToPose Behavior Tree以Sequence型控制流程先執行`ComputePathToPose`，成功後才讓`FollowPath`使用產生的path。當planning node回傳FAILURE時，Sequence不會開始後續tracking child。

專案必須選用保有此順序的標準BT composition，但不需要額外project-specific admission gate。是否重試、重新規劃或採用其他route strategy屬其他requirements或configuration，並非SYS-011 coverage gap。

## 4. Configuration and Composition

- 固定target image的Navigation2與planner plugin版本；
- 選定global planner plugin及planner ID；
- 配置global costmap、robot footprint、global frame與TF tolerance；
- 確認current robot pose可由costmap／TF取得；
- 配置planner timeout與必要planner parameters；
- 使用planning success先於`FollowPath`的標準BT sequence；
- 保留原生`ComputePathToPose` error code與message。

以上皆是成熟套件整合，不形成custom behavior gap。

## 5. Evidence Required Before Acceptance

- 記錄target image的`nav2_planner`、`nav2_msgs`及selected planner plugin版本；
- 以各active navigation stage的實際current pose與goal產生non-empty `nav_msgs/Path`；
- 驗證path frame、timestamp、start／goal端點及planning time；
- 注入invalid planner、TF failure、outside map、occupied start／goal、timeout與no-valid-path，保存原生code／message；
- 證明每個planning failure均未開始對應的`FollowPath` action；
- 量測實機planning latency，並確認selected planner產生的path適合AMR footprint與運動限制。

## 6. Primary-source Evidence

### 6.1 Planner Server and action contract

- **Evidence Type:** upstream exact-tag source and official configuration documentation
- **Sources:** [`planner_server.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_planner/src/planner_server.cpp)；[`ComputePathToPose.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputePathToPose.action)；[Planner Server configuration](https://docs.nav2.org/configuration/packages/configuring-planner-server.html)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** current／explicit start、goal、planner selection、costmap wait、TF transform、non-empty path validation、path result與structured planning errors。
- **Limitations:** target installation、configuration及real-hardware path suitability仍需project evidence。
- **Access Date:** 2026-08-14

### 6.2 Global planner plugin interface

- **Evidence Type:** upstream exact-tag interface source
- **Source:** [`global_planner.hpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_core/include/nav2_core/global_planner.hpp)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** selected plugin透過`createPlan(start, goal, cancel_checker)`回傳標準`nav_msgs/msg/Path`。
- **Limitations:** plugin selection與algorithm-specific parameters尚待05／06固定。
- **Access Date:** 2026-08-14

### 6.3 Standard planning-to-tracking sequence

- **Evidence Type:** upstream exact-tag BT source and official Behavior Tree documentation
- **Sources:** [`navigate_to_pose_w_replanning_and_recovery.xml` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml)；[Nav2 Behavior Trees](https://docs.nav2.org/behavior_trees/index.html)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** standardtree以control-flow composition先取得path，再將成功path提供給`FollowPath`；planning FAILURE不會開始後續Sequence child。
- **Limitations:** 專案實際BT XML與retry／replanning設定仍須保存及驗證。
- **Access Date:** 2026-08-14

## 7. Recommended 04 Record

```text
SYS-011 Path Planning
Candidate Mature Solution: Navigation2 Jazzy Planner Server + selected GlobalPlanner plugin + standard BT planning-to-tracking sequence
Coverage Status: Fully Covered
Covered Scope: current/explicit start to active-stage goal path computation; non-empty path; native error code/message; planning failure prevents FollowPath start
Custom Behavior Gap: None
Configuration / Composition Gap: planner/costmap/footprint/frames/TF/timeout and BT sequence
Evidence Gap: target versions; actual stage paths; native failure injection; zero FollowPath start on planning failure; real-hardware latency/path suitability
MVP Change Candidate: None
```
