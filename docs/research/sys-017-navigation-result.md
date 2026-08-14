# SYS-017 Navigation Result — Reuse Research

## 1. Research Scope

本筆記只研究目前定案的SYS-017：

> 系統應透過 Navigation2 原生導航結果回報導航成功、失敗或取消；導航失敗時應回報可取得的 Navigation2 原生失敗結果。

本項只評估overall navigation result，不重複各上游行為：

- SYS-011、014、015：planning、obstacle avoidance與tracking的原生結果；
- SYS-013、018～020：route-preferred strategy與三階段執行；
- SYS-016：成功判定；
- SYS-021：`Free-space Fallback unavailable` eligibility與行為；
- SYS-025：使用者取消。

候選成熟方案為ROS 2 Jazzy action semantics、Navigation2 1.3.12-1 `NavigateToPose`、BT Navigator，以及`ComputePathToPose`、`FollowPath`與`ComputeRoute`的原生results。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy action result + Navigation2 1.3.12-1 `NavigateToPose` + BT Navigator + child native action results |
| Coverage Status | **Fully Covered** |
| Mature Coverage | action-level succeeded／aborted／canceled terminal states；overall result delivery；BT child error-code aggregation；planner/controller/route native failure codes；standard cancellation result |
| Custom Behavior Gap | **None** |
| Configuration / Composition Gap | overall action boundary；BT error-code blackboard ports；child-to-final result propagation；terminal wrapped-status/payload handling；cancel completion handling |
| Missing Evidence | exact versions；actual BT；planning/tracking/route error propagation；success/failure/cancel and races；terminal-visible status/code/message |
| MVP Change Candidate | `None` |

目前需求已對齊ROS 2 action與Navigation2原生result boundary，不需要project stage taxonomy、custom result aggregator或custom navigation action。

## 3. Native Result Semantics

ROS 2 action提供goal、feedback、result與cancel。`NavigateToPose` client取得的wrapped result code可區分：

- `SUCCEEDED`：BT成功結束；
- `ABORTED`：BT失敗並終止goal；
- `CANCELED`：取消流程完成。

`NavigateToPose.action`另提供`error_code`與`error_msg` payload。Navigation2 1.3.12 BT Action Server會從blackboard收集非零child error codes，選擇優先值放入final result。

因此terminal client必須同時檢查wrapped action status與payload，不能只用`error_code == 0`判定success。CancelGoal response accepted也只表示goal開始進入canceling；必須等待final `CANCELED` result才可回報取消完成。

## 4. Native Failure Results

- `ComputePathToPose`提供invalid planner、TF、map/occupancy、timeout及no-valid-path等codes，並有error message；
- `FollowPath`提供invalid controller/path、TF、failed progress、no-valid-control及timeout等codes，並有error message；
- `ComputeRoute`提供invalid graph/nodes、timeout及no-route等codes，但1.3.12 result沒有error message string。

Navigation2原生codes已足以滿足「回報可取得的原生失敗結果」。1.3.12 standard BT主要聚合child error code；不可僅因final `NavigateToPose` interface有`error_msg`欄位，就假定每一個child detail string都會完整傳到terminal。實際內容須由integration evidence確認。

## 5. Three-stage and Fallback Boundary

SYS-017不再要求把相同Nav2 error另外標記為First Mile、On Route或Last Mile。三階段原則仍由SYS-018～020定義並執行；SYS-021仍負責符合eligibility時終止並回報`Free-space Fallback unavailable`。

這些行為最後都會形成Nav2 overall success、failure或cancel result，但SYS-017不建立第二套project-specific enum或result framework。如此可保留產品行為，同時避免因stage label產生額外custom orchestration。

人工管理Navigation Resources也不形成runtime `Navigation Resource Validation` result category；該過時名稱已從SYS-017移除。

## 6. Configuration and Evidence

### Configuration / composition

- 固定overall navigation action boundary與exact Nav2 version；
- 固定BT child error-code blackboard ports；
- 確認route、planning與tracking action failure會終止overall BT；
- terminal client同時呈現wrapped status與可取得的result payload；
- cancel操作等待final result，不把request accepted直接顯示為canceled。

### Evidence required

- success：SYS-016成立後得到`NavigateToPose` `SUCCEEDED`；
- planning：注入TF、occupied/out-of-map、timeout及no-path，保存child/final codes；
- tracking：注入invalid path、failed progress、no-valid-control及timeout，保存child/final codes；
- route：注入invalid graph/nodes、timeout及no-route，保存route與overall result；
- cancel：驗證執行中取消、已終止goal取消及cancel/completion race；
- terminal：保存使用者實際看到的status、error code及可取得message，不以server log代替result contract。

## 7. Primary-source Evidence

### 7.1 Overall action result

- **Evidence Type:** upstream exact-tag action definition and ROS 2 Jazzy documentation
- **Sources:** [`NavigateToPose.action` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/NavigateToPose.action)；[ROS 2 Jazzy actions overview](https://docs.ros.org/en/jazzy/How-To-Guides/Topics-Services-Actions.html)
- **Exact Version / Revision:** Navigation2 1.3.12；ROS 2 Jazzy
- **Observed Scope:** action terminal states、result payload與cancel capability。
- **Limitations:** terminal presentation and actual error-message propagation require project evidence。
- **Access Date:** 2026-08-14

### 7.2 BT Navigator result propagation

- **Evidence Type:** official Jazzy generated source and upstream exact-tag source
- **Sources:** [Jazzy `bt_action_server_impl.hpp`](https://api.nav2.org/nav2-jazzy/html/bt__action__server__impl_8hpp_source.html)；[`navigate_to_pose.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/src/navigators/navigate_to_pose.cpp)；[`navigate_to_pose_w_replanning_and_recovery.xml` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml)
- **Exact Version / Revision:** Navigation2 Jazzy / 1.3.12
- **Observed Scope:** BT completion maps to action success/failure/cancel and blackboard error-code aggregation。
- **Limitations:** selected project BT and final message content require integration evidence。
- **Access Date:** 2026-08-14

### 7.3 Child native results

- **Evidence Type:** upstream exact-tag action definitions
- **Sources:** [`ComputePathToPose.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputePathToPose.action)；[`FollowPath.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/FollowPath.action)；[`ComputeRoute.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputeRoute.action)
- **Exact Version / Revision:** Navigation2 / `nav2_msgs` 1.3.12
- **Observed Scope:** native planning、tracking與route failure codes。
- **Limitations:** child-to-final propagation and terminal-visible detail require project evidence。
- **Access Date:** 2026-08-14

## 8. Recommended 04 Record

```text
SYS-017 Navigation Result
Candidate Mature Solution: ROS 2 action result + Navigation2 NavigateToPose/BT Navigator + native child action results (Jazzy 1.3.12-1)
Coverage Status: Fully Covered
Covered Scope: succeeded/aborted/canceled terminal states; overall result; child error-code aggregation; native planning/tracking/route failures
Custom Behavior Gap: None
Configuration / Composition Gap: BT error ports; child-to-final propagation; terminal status/payload and cancel completion handling
Evidence Gap: versions; actual BT; failure propagation; success/failure/cancel races; terminal-visible result
MVP Change Candidate: None
```
