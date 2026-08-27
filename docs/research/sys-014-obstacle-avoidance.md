> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-014 Obstacle Avoidance — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-014 障礙物避讓**：導航期間，系統應使用有效之環境障礙物資訊，避免規劃或執行穿越已判定占用區域之運動；無法維持可安全執行之導航時，系統應嘗試使底盤停止並回報失敗。

本項評估Navigation2如何把環境觀測轉成global／local costmap occupancy，讓planner避開occupied cells、controller拒絕collision trajectory，並在無可用motion時輸出zero velocity attempt及native navigation failure。

相鄰責任不重複計入：

- SYS-011：取得current pose與stage goal並要求non-empty path；
- SYS-015：一般path tracking、progress與stage transition；
- SYS-017：跨navigation stages的最終結果分類；
- SYS-022：把已接受速度命令轉成底盤運動；
- SYS-027：速度命令中斷時的base timeout stop；
- SYS-030：底盤enable/disable、停止確認與driver安全啟停。

候選成熟composition固定為ROS 2 Jazzy Navigation2 1.3.12-1：`nav2_costmap_2d` Static／Obstacle／Inflation layers、collision-aware global planner與controller plugin、Planner／Controller Server、BT Navigator及`nav2_collision_monitor`。Collision Monitor作為核准的command-chain defense-in-depth元件，但不取代costmap、planner、controller、實體E-stop或safety-rated設備。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | Navigation2 Jazzy 1.3.12-1 layered global/local costmaps + collision-aware planner（例如Smac）+ collision-checking controller（例如MPPI或Regulated Pure Pursuit）+ Planner/Controller Server + standard BT failure propagation + `nav2_collision_monitor` defense-in-depth |
| Coverage Status | **Fully Covered** |
| Mature Coverage | sensor observations的marking／clearing與freshness；static/dynamic occupied costs及footprint inflation；global planning collision checks；local trajectory collision checks；stale costmap wait/timeout；no-valid-path/control failure；controller zero-velocity stop attempt；native action error code/message |
| Custom Behavior Gap | **None** |
| Configuration / Composition Gap | obstacle sources/QoS/frames/timeouts；global/local costmap layers、resolution、footprint及inflation；unknown-space policy；selected planner/controller的collision options；BT retry/recovery；Collision Monitor sources/zones/timeouts與cmd_vel chain；zero-command routing |
| Missing Evidence | exact installed versions；actual LaserScan source(s)及freshness；occupied-cell marking/clearing；planner/controller collision injection；Collision Monitor zones/source timeout/TF failure；native failure propagation；zero command至physical stop的實機證據 |
| MVP Change Candidate | `None` |

此Fully Covered只表示成熟Nav2 composition已提供全部required behavior，不表示目前configuration或實體AMR已驗證。特別是「嘗試使底盤停止」由Controller Server發布zero velocity滿足software attempt；底盤是否實際停止仍須SYS-022／027／030及實機evidence閉合。

## 3. Environment Obstacle Information

### 3.1 Global and local costmaps have different roles

`nav2_costmap_2d`以layered costmap組合環境資料：

- Static Layer：由Occupancy Grid提供已知static occupied/free/unknown cells；
- Obstacle Layer：從LaserScan或PointCloud2 observations標記lethal obstacles，並以raytracing清除free space；
- Inflation Layer：依robot footprint／inscribed radius把occupied costs向外擴張，供planner/controller保留碰撞距離。

Global costmap主要提供global planner規劃範圍內的occupied cost；local rolling costmap提供controller附近的較即時障礙資訊。兩者可以使用相同或不同observation sources，但必須各自配置並驗證，不能因global costmap看見障礙就假定local controller也看見，反之亦然。

SYS-014只要求使用有效環境障礙資訊，不指定必須融合LaserScan。Obstacle Layer原生支援多個`observation_sources`；可以直接接多個來源或接核准的單一selected／merged scan。選擇哪一種是configuration/evidence問題，不在本項重做LaserScan merge方案。

### 3.2 Native freshness and transform constraints

每個Obstacle Layer observation source具有topic、data type、marking／clearing、range、height及`expected_update_rate`等配置。Observation Buffer的`isCurrent()`依expected update rate判斷資料是否仍current；Obstacle Layer彙整marking與clearing buffers的current狀態，Layered Costmap再形成整體current狀態。

Planner Server在規劃前等待global costmap current，超過`costmap_update_timeout`即回報planner timeout。Controller Server也會等待local costmap current，超時後形成controller failure。TF unavailable的sensor message會被message filter延後或drop，因而影響layer current與原生logs。

所以「有效」不需另做project obstacle-valid boolean；可由成熟costmap observation freshness、TF及server current/timeout behavior組合覆蓋。但若`expected_update_rate`或timeout被停用／設得過寬，stale data仍可能被視為可用，必須靠configuration與failure-injection evidence閉合。

## 4. Avoiding Occupied Regions

### 4.1 Planning-time avoidance

成熟Nav2 global planner plugins直接使用global costmap。以Smac Planner為例，其A* search含基於robot radius或footprint的Collision Checker；Hybrid／Lattice variants同時使用kinematically valid motion models。Occupied、inscribed及unknown cells如何處理由plugin與costmap parameters控制。

Planner Server會拒絕empty path，並以`START_OCCUPIED`、`GOAL_OCCUPIED`、`NO_VALID_PATH`、`TIMEOUT`或其他native error code/message終止`ComputePathToPose`。標準BT sequence只有planning成功才進入`FollowPath`，所以不能穿越costmap occupied region的planner若找不到替代path，tracking不會開始。

這部分與SYS-011的差異是：SYS-011只要求Navigation2產生non-empty path；SYS-014要求selected planner確實啟用costmap collision semantics。相同Planner Server可同時提供兩項能力，但verification focus不同。

### 4.2 Execution-time avoidance

Global path在產生後，動態障礙可能出現，因此只靠global planner不足。必須選用會針對local costmap進行trajectory collision checking的controller：

- MPPI對sampled trajectories使用costmap及footprint collision cost；當所有trajectories collide時設failure，無法產生valid control；
- Regulated Pure Pursuit在`use_collision_detection=true`時沿projected motion執行time-to-collision checking並調節／拒絕危險motion。

Controller Server在no valid control、invalid path、TF、costmap timeout、failed progress等exceptions時呼叫`onGoalExit(true)`，發布zero velocity後終止`FollowPath`並回傳error code/message。標準BT可在有限replanning/recovery後使NavigateToPose失敗。

因此「避免執行穿越occupied區域」與「無法維持時停止並回報」可由成熟local costmap + collision-checking controller + Controller Server覆蓋，不需custom collision algorithm或failure adapter。

「occupied」是costmap classification，不代表感測器能看見所有真實障礙。透明、過低／過高、超出range、遮蔽或資料延遲的物體可能未被marked；這是sensor/configuration及實機evidence限制，不能由source capability直接宣稱全部真實碰撞已避免。

## 5. Failure and Stop Boundary

SYS-014的software failure flow可使用標準Nav2 behavior：

```text
observation unavailable/stale
  → costmap not current / timeout
  → planner or controller action failure

occupied region blocks every valid path/trajectory
  → NO_VALID_PATH or NO_VALID_CONTROL / controller failure

failure cannot be recovered under configured BT limits
  → terminate navigation action with native code/message
  → Controller Server publishes zero velocity as stop attempt
```

邊界必須清楚：

- SYS-014只要求attempt stop，不要求在此確認wheel speed為零；
- zero velocity是否通過command mux/smoother、ROS transport與driver到達底盤，屬SYS-022 integration；
- command停止更新後的base watchdog屬SYS-027；
- 停止確認、disable與driver安全狀態屬SYS-030；
- 將native obstacle/navigation failure放進整體First／On Route／Last Mile結果屬SYS-017。

只要保留Nav2原生error code/message，SYS-014不需要另建project failure taxonomy。若BT先執行costmap clear/replan等有限recoveries，仍屬Nav2原生composition；但Spin／BackUp等會移動的recovery必須另外證明其collision checking及是否符合核准operation policy。

## 6. Collision Monitor Baseline

### Core Nav2 costmap/planner/controller composition

| Field | Assessment |
|---|---|
| Coverage Status | **Fully Covered** |
| Role | 常態navigation obstacle avoidance：costmaps → global planning → local trajectory collision checks → native failure/zero command |
| Custom Gap | None |
| Key Constraint | 必須選用並正確配置collision-aware planner/controller，且sensor freshness與footprint必須經實機證明 |

### Required defense-in-depth — `nav2_collision_monitor`

Collision Monitor繞過costmap與trajectory planners，直接監看sensor points或costmap source，依robot-relative polygon／circle／approach model對incoming velocity command執行stop、slowdown或limit。`source_timeout` watchdog可在尚未收到資料、資料逾時或無法transform時採blocking stop behavior。

| Field | Assessment |
|---|---|
| Baseline Status | **Included in the approved SYS-014 mature composition** |
| Added Coverage | 對突然靠近、來不及由costmap/planner/controller反應的障礙提供更靠近command output的快速stop/slow behavior |
| Custom Gap | None |
| Key Constraint | 需額外配置zones、source timeout、frames、cmd_vel chain及real-hardware braking evidence；其CPU implementation不是hard-real-time或certified functional-safety solution |

Core Nav2本身已可覆蓋normative behavior；本專案仍核准加入Collision Monitor，讓靠近command output的sensor zones可更快執行stop／slow／limit，形成額外defense-in-depth。它不取代costmap planning/controller collision avoidance，也不取代實體E-stop或safety-rated scanner/controller。

此外，Collision Monitor單獨把velocity降為零不一定終止NavigateToPose或回報navigation failure；若採用，仍需保留Core Nav2 failure/progress behavior。是否加入它應由05依風險、速度、環境與command chain決定，04不預先核准architecture selection。

## 7. Is SYS-014 Over-aggregated?

SYS-014橫跨sensor observations、costmap、planner、controller、navigation result與base stop，從component ownership看確實是cross-cutting requirement；但它描述的是一條完整且一致的「看見障礙→不規劃／不執行碰撞motion→無法繼續時停止並失敗」行為鏈，並非不合理聚合。

現行wording不需要回到03簡化。可在05分配責任及contracts：perception提供observations、costmaps擁有occupied representation、planner/controller負責collision avoidance、Nav2 action負責failure、motion/base負責stop attempt傳遞與physical evidence。這是architecture responsibility allocation，不是requirement weakening。

成熟Nav2原生composition採collision-aware plugins、標準interfaces/configuration及核准的Collision Monitor；不需刪除stop或failure fragment。把physical-stop確認誤放進SYS-014才會造成不必要custom gap，因此本筆記明確把它留在SYS-030等底盤requirements。

## 8. Configuration and Evidence Gaps

### Configuration / composition still required

- 固定global/local costmap的LaserScan／PointCloud observation sources、topics、QoS、frames及marking／clearing；
- 固定`expected_update_rate`、observation persistence、transform tolerance、obstacle/raytrace ranges與height filters；
- 固定costmap resolution、update/publish frequency、rolling window、robot footprint及Inflation Layer parameters；
- 固定unknown-space policy與cost combination；
- 選定並記錄collision-aware global planner及controller plugin；
- 對MPPI配置footprint-aware Cost/Obstacles critic或對RPP保持collision detection enabled，並固定prediction horizon；
- 固定Planner／Controller Server costmap update timeout、controller failure tolerance、BT retry/recovery limits；
- 確認controller zero velocity經核准command chain到達base；
- 固定Collision Monitor的sources、zones、action types、source timeout、min points、input/output cmd_vel topics及其在command chain的位置。

### Evidence required before acceptance

- 記錄target image上`nav2_costmap_2d`、planner、controller、BT Navigator及Collision Monitor的實際1.3.12-1 binary版本；
- 以實際navigation sensor source(s)驗證QoS、frame、timestamp、rate、coverage及observation freshness；
- 對global/local costmap分別注入static與dynamic obstacles，確認marking、clearing、inflation及current/stale transitions；
- 驗證robot footprint及inflation不允許robot body穿越lethal/inscribed occupied area；
- 在規劃前放置障礙，證明planner繞行或回傳native no-path/occupied failure，且不啟動FollowPath；
- 在執行中突然加入障礙，證明controller的candidate trajectories不穿越occupied cells，無解時回傳native failure；
- 中斷或延遲obstacle source、破壞TF並測試costmap timeout及failure behavior；
- 保存NavigateToPose／ComputePath／FollowPath error code/message，證明無法維持navigation時最終回報失敗；
- 驗證failure時zero velocity被發布並通過command chain；以wheel feedback證明實際停止，但將physical-stop closure歸入SYS-022／027／030 evidence；
- 在不同速度、障礙距離／角度、遮蔽、反射特性及CPU load下量測detection-to-command及braking distance；
- 測試Collision Monitor各zone、source timeout、TF failure、simultaneous zones及其非hard-real-time限制。

## 9. Primary-source Evidence

### 9.1 Layered costmaps and obstacle freshness

- **Evidence Type:** upstream exact-tag source and official Nav2 documentation
- **Sources:** [`nav2_costmap_2d` README at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_costmap_2d/README.md)；[`obstacle_layer.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_costmap_2d/plugins/obstacle_layer.cpp)；[`observation_buffer.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_costmap_2d/src/observation_buffer.cpp)；[Obstacle Layer configuration](https://docs.nav2.org/configuration/packages/costmap-plugins/obstacle.html)；[Inflation Layer configuration](https://docs.nav2.org/configuration/packages/costmap-plugins/inflation.html)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** layered costmap組合static、sensor-marked及inflated costs；Obstacle Layer執行marking／raytrace clearing並彙整buffer current state；Observation Buffer依update timing判斷freshness。
- **Limitations:** target sensor coverage、QoS、TF及parameter correctness需integration/real-hardware evidence。
- **Access Date:** 2026-08-14

### 9.2 Planning-time collision avoidance

- **Evidence Type:** upstream exact-tag source and official plugin documentation
- **Sources:** [`planner_server.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_planner/src/planner_server.cpp)；[`nav2_smac_planner` README at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_smac_planner/README.md)；[`collision_checker.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_smac_planner/src/collision_checker.cpp)；[`ComputePathToPose.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputePathToPose.action)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** Smac使用costmap與radius／footprint collision checking；Planner Server等待current costmap、拒絕invalid/empty path並回傳native errors。
- **Limitations:** selected planner、footprint、unknown-space及cost thresholds尚需project configuration/evidence。
- **Access Date:** 2026-08-14

### 9.3 Execution-time collision avoidance and stop attempt

- **Evidence Type:** upstream exact-tag source and official controller documentation
- **Sources:** [`controller_server.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/src/controller_server.cpp)；[`nav2_mppi_controller` README at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_mppi_controller/README.md)；[`obstacles_critic.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_mppi_controller/src/critics/obstacles_critic.cpp)；[Regulated Pure Pursuit configuration](https://docs.nav2.org/configuration/packages/configuring-regulated-pp.html)；[`FollowPath.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/FollowPath.action)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** mature controllers提供costmap-based trajectory collision checks；Controller Server等待current costmap，在no-valid-control及其他failure時發布zero velocity並回傳action error。
- **Limitations:** source不能證明target tuning、command delivery或physical braking。
- **Access Date:** 2026-08-14

### 9.4 BT failure propagation

- **Evidence Type:** upstream exact-tag source
- **Sources:** [`navigate_to_pose_w_replanning_and_recovery.xml` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml)；[`NavigateToPose.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/NavigateToPose.action)；[Detailed Behavior Tree walkthrough](https://docs.nav2.org/behavior_trees/overview/detailed_behavior_tree_walkthrough.html)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** standard BT依序執行planning再進入control，提供bounded contextual／system recoveries，並透過action result回報最終navigation failure。
- **Limitations:** selected BT recovery movements and retry limits require operation-policy review and integration evidence。
- **Access Date:** 2026-08-14

### 9.5 Collision Monitor

- **Evidence Type:** upstream exact-tag source and official Nav2 documentation
- **Sources:** [`collision_monitor_node.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_collision_monitor/src/collision_monitor_node.cpp)；[Collision Monitor configuration](https://docs.nav2.org/configuration/packages/collision_monitor/configuring-collision-monitor-node.html)；[Using Collision Monitor tutorial](https://docs.nav2.org/tutorials/docs/using_collision_monitor.html)；[Jazzy source-timeout behavior lineage](https://docs.nav2.org/migration/Iron.html#collision-monitor-added-watchdog-mechanism-based-on-source-timeout-parameter-with-default-blocking-behavior)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** command-chain stop/slow/limit zones及source-timeout watchdog；官方明確定位為繞過costmap/planners的additional safety layer。
- **Limitations:** CPU-level implementation不是hard-real-time/safety-certified；單獨velocity blocking不形成navigation action failure。
- **Access Date:** 2026-08-14

### 9.6 Jazzy release metadata

- **Evidence Type:** ROS build-farm status and upstream release metadata
- **Sources:** [ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)；[Navigation2 release 1.3.12](https://github.com/ros-navigation/navigation2/releases/tag/1.3.12)
- **Exact Version / Revision:** Navigation2 Jazzy 1.3.12-1
- **Observed Scope:** 確認本研究採用的Navigation2 Jazzy release anchor。
- **Limitations:** repository/build metadata不證明target安裝、configuration或實機效果。
- **Access Date:** 2026-08-14

## 10. Recommended 04 Record

```text
SYS-014 Obstacle Avoidance
Candidate Mature Solution: Nav2 layered global/local costmaps + collision-aware planner/controller + Planner/Controller Server + standard BT failure propagation + nav2_collision_monitor defense-in-depth (Navigation2 Jazzy 1.3.12-1)
Coverage Status: Fully Covered
Covered Scope: valid/fresh obstacle observations into occupied costs; planning and execution collision avoidance; stale/no-path/no-control failures; zero-velocity stop attempt; native error reporting
Custom Behavior Gap: None
Configuration / Composition Gap: sensor sources/QoS/frames/freshness; costmap/footprint/inflation; planner/controller collision options; BT recovery limits; Collision Monitor sources/zones/timeouts and cmd_vel chain
Evidence Gap: exact target versions; actual obstacle-source semantics; costmap marking/clearing/freshness; collision injection; native failure propagation; zero command and physical-stop evidence; real-hardware detection/braking margins
MVP Change Candidate: None
```

SYS-014可由成熟Nav2 composition完整覆蓋，不需自製obstacle avoidance或簡化requirement。04納入Collision Monitor作為defense-in-depth，同時必須保留configuration與實機evidence限制，且不得將其誤稱為certified safety mechanism或physical-stop證明。
