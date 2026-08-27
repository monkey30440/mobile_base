> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-015 Path Tracking — Reuse Research

## 1. Research Scope

本筆記只研究目前定案的SYS-015：

> 系統應透過 Navigation2 `FollowPath` 控制 AMR 追蹤目前 active navigation stage 的有效路徑，並使用設定的 controller 與 progress checker 判定能否繼續追蹤。無法繼續追蹤時，系統應停止該 stage 的路徑追蹤、嘗試使底盤停止，並回報 Navigation2 原生追蹤失敗結果。追蹤接受條件應經整合及實機驗證。

SYS-015只要求單一active stage的path tracking。相鄰責任保持分離：

- SYS-011：產生active-stage有效且非空path；
- SYS-013：route-preferred strategy；
- SYS-014：occupied-space collision avoidance；
- SYS-016：最終Navigation Target到站判定；
- SYS-017：整體navigation result；
- SYS-018～020：First Mile、On Route、Last Mile及其stage transition／continuity；
- SYS-021：route-assisted alternatives與Free-space Fallback eligibility。

候選成熟方案為ROS 2 Jazzy Navigation2 1.3.12-1的Controller Server、`FollowPath` action、selected controller plugin、Progress Checker、Goal Checker及standard BT composition。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | Navigation2 Jazzy 1.3.12-1 Controller Server + `FollowPath` + selected controller + Progress Checker + Goal Checker + standard BT |
| Coverage Status | **Fully Covered** |
| Mature Coverage | non-empty path tracking；controller/path/TF/local-costmap monitoring；progress checking；distance/speed feedback；native failure codes；cancel/failure zero-velocity stop attempt |
| Custom Behavior Gap | **None** |
| Configuration / Composition Gap | controller/progress/goal plugins；control rate；local costmap；TF/odom；tracking/progress acceptance；failure tolerance；BT wiring；stop-command chain |
| Missing Evidence | exact versions；selected plugins；per-stage tracking；progress/failure injection；native errors；zero command；real-hardware tracking error、latency及stopping |
| MVP Change Candidate | `None` |

需求已對齊Navigation2原生`FollowPath` boundary，不需要stage-aware tracking orchestration、自製path follower或project failure taxonomy。

## 3. Native Tracking Loop

`nav2_msgs/action/FollowPath` goal包含path、controller ID、goal checker ID與progress checker ID。Controller Server拒絕empty path，並依controller frequency循環：

1. 等待local costmap current；
2. 取得current robot pose；
3. 執行Progress Checker；
4. 由selected controller計算velocity command；
5. 發布velocity command；
6. 執行Goal Checker；
7. 發布distance-to-goal與speed feedback。

MPPI與Regulated Pure Pursuit等成熟`nav2_core::Controller` implementations皆可追蹤path，但plugin選擇、tuning、CPU負載及對差速AMR與實際stage paths的適用性仍須實機驗證。

## 4. Continue and Failure Semantics

成熟監控包含：

- controller能否產生valid control；
- Progress Checker是否在允許時間內觀察到足夠movement；
- local costmap是否current；
- TF與robot pose是否可取得；
- path是否有效；
- Goal Checker是否到達該path endpoint。

`FollowPath`原生failure codes包含invalid controller、TF error、invalid path、failed progress、no valid control、controller timeout與unknown failure。Controller Server在cancel、failure及goal exit時可發布zero velocity，因此完整覆蓋software stop attempt與原生追蹤結果。

Progress Checker主要判斷一段時間內是否有足夠movement，不等同跨controller通用的lateral deviation metric。追蹤接受條件應由selected controller、progress parameters及實機tracking evidence固定，不需要為此自製通用deviation monitor。

Zero velocity不證明底盤實際停止；command routing、watchdog、driver response及wheel feedback由SYS-022、027、030與實機verification閉合。

## 5. Three-stage Navigation Boundary

First Mile、On Route與Last Mile都使用同一套SYS-015 tracking能力：

```text
First Mile path ─┐
On Route path  ──┼─> FollowPath
Last Mile path ──┘
```

SYS-015不決定目前是哪個stage，也不決定何時切換。SYS-018～020後續assessment與05 architecture必須明確承接stage transition及跨stage continuity；簡化SYS-015不得刪除三階段移動原則或讓handoff失去owner。

## 6. Configuration and Evidence

### Configuration / composition

- 固定controller、Progress Checker與Goal Checker plugins及exact versions；
- 配置controller frequency、local costmap、TF tolerance、odom topic及velocity thresholds；
- 配置progress radius／angle與time allowance；
- 固定controller failure tolerance、BT retry與zero-velocity publication；
- 維持`ComputePath → FollowPath`的標準composition；
- 讓SYS-018～020提供active-stage path與承接transition結果。

### Evidence required

- 記錄target installed versions與selected plugin IDs；
- 分別追蹤First Mile、On Route與Last Mile實際path，保存feedback與controller output；
- 驗證TF、local-costmap stale、invalid path、failed progress及no-valid-control原生結果；
- 驗證failure時`FollowPath`終止且zero velocity進入核准command chain；
- 量測straight、turn、reverse（若允許）、狹窄通道及stage endpoint附近的tracking error、command rate、latency與停止表現；
- 後續以SYS-018～020 evidence確認三階段handoff continuity未因SYS-015簡化而遺失。

## 7. Primary-source Evidence

### 7.1 Controller Server and FollowPath

- **Evidence Type:** upstream exact-tag source and action definition
- **Sources:** [`controller_server.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/src/controller_server.cpp)；[`FollowPath.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/FollowPath.action)；[Controller Server configuration](https://docs.nav2.org/configuration/packages/configuring-controller-server.html)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** standard tracking loop、plugin selection、feedback、native failures與zero-velocity publication。
- **Limitations:** target configuration與physical tracking/stopping仍需project evidence。
- **Access Date:** 2026-08-14

### 7.2 Progress and goal checkers

- **Evidence Type:** upstream exact-tag source and official documentation
- **Sources:** [`simple_progress_checker.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/plugins/simple_progress_checker.cpp)；[Progress Checker configuration](https://docs.nav2.org/configuration/packages/nav2_controller-plugins/simple_progress_checker.html)；[Goal Checker configuration](https://docs.nav2.org/configuration/packages/nav2_controller-plugins/simple_goal_checker.html)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** configurable movement/time progress判定與path endpoint pose acceptance。
- **Limitations:** Progress Checker不是通用lateral-deviation estimator；threshold需實機選定。
- **Access Date:** 2026-08-14

### 7.3 Mature controller plugins

- **Evidence Type:** upstream exact-tag source and official documentation
- **Sources:** [`nav2_mppi_controller` README at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_mppi_controller/README.md)；[Regulated Pure Pursuit configuration](https://docs.nav2.org/configuration/packages/configuring-regulated-pp.html)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** mature path-tracking controller implementations compatible with Controller Server.
- **Limitations:** final plugin selection and tuning require actual AMR evidence。
- **Access Date:** 2026-08-14

### 7.4 Standard BT composition

- **Evidence Type:** upstream exact-tag BT source
- **Source:** [`navigate_to_pose_w_replanning_and_recovery.xml` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** standard planning-to-FollowPath composition and controller failure propagation。
- **Limitations:** stage transition remains a SYS-018～020/architecture responsibility。
- **Access Date:** 2026-08-14

## 8. Recommended 04 Record

```text
SYS-015 Path Tracking
Candidate Mature Solution: Navigation2 Controller Server + FollowPath + selected controller + Progress/Goal Checker + standard BT (Jazzy 1.3.12-1)
Coverage Status: Fully Covered
Covered Scope: active-stage path tracking; controller/progress monitoring; feedback; native failure; zero-velocity stop attempt
Custom Behavior Gap: None
Configuration / Composition Gap: plugins; local costmap/TF/odom/rates; tracking acceptance; failure tolerance; BT and stop-command wiring
Evidence Gap: target versions; per-stage tracking; progress/failure injection; native results; zero command; real-hardware tracking/latency/stopping; SYS-018-020 handoff continuity
MVP Change Candidate: None
```
