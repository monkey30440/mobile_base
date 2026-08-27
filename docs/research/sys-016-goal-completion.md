> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-016 Goal Completion — Reuse Research

## 1. Research Scope

本筆記只研究目前定案的 SYS-016：

> 系統僅應在 AMR 目前位姿符合解析後 Navigation Target 所設定之位置與朝向接受條件，且底盤已停止時，判定導航成功。位置、朝向與停止判定門檻應經整合及實機驗證。

相鄰責任保持分離：

- SYS-015：追蹤 active-stage path，以及追蹤失敗時終止該 stage；
- SYS-017：彙整並對外回報整體 navigation result；
- SYS-028：限制移動與旋轉速度／加速度；
- SYS-029：以 M1 hardware feedback 建立實際輪速與運動 feedback；
- SYS-030：安全停止流程、實際輪組停止確認及 drive disable。

本項只判斷「何時可把導航視為成功」。候選成熟方案固定為 ROS 2 Jazzy Navigation2 1.3.12-1 的 Controller Server、`FollowPath`、`StoppedGoalChecker` 與標準 NavigateToPose behavior-tree composition。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | Navigation2 Controller Server + `FollowPath` + `nav2_controller::StoppedGoalChecker` + standard NavigateToPose BT |
| Exact Version / Platform | ROS 2 Jazzy；Navigation2 / `nav2_controller` 1.3.12，Jazzy binary release 1.3.12-1 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 以 current pose 對 path endpoint 檢查 XY 與 yaw；以 odometry-derived twist 檢查平移及旋轉已低於停止門檻；全部通過才讓 `FollowPath` 成功，並由標準 BT 傳遞至 NavigateToPose success |
| Known Constraints | final path endpoint 必須保持 resolved Navigation Target 的位置與方向語意；停止是 navigation-level odometry velocity 判定，不是 M1 wheel-stop hardware confirmation；所有門檻及 `stateful` 語意必須配置並實機驗證 |
| Uncovered Gap | **None** |
| Evidence | Jazzy 1.3.12 API、1.3.12 exact-tag source、action definition與標準 BT source |
| Missing Evidence | target installed versions；selected Goal Checker ID；final path endpoint preservation；odom topic/source；各門檻與 `stateful` 配置；邊界值、噪聲、停止及完整 success-chain 實機結果 |

成熟方案已原生提供 SYS-016 所需的複合成功條件，不需自行撰寫 goal-completion behavior。Configuration、standard composition 與 verification 尚未完成，不改變 coverage 結論。

## 3. Goal Checker Comparison

| Capability | `SimpleGoalChecker` | `StoppedGoalChecker` |
|---|---|---|
| XY acceptance | `xy_goal_tolerance` | 繼承相同判定 |
| Yaw acceptance | `yaw_goal_tolerance` | 繼承相同判定 |
| Translational stop | 無 | `hypot(linear.x, linear.y) <= trans_stopped_velocity` |
| Rotational stop | 無 | `abs(angular.z) <= rot_stopped_velocity` |
| SYS-016 suitability | 不完整 | 完整，前提是正確配置與驗證 |

`StoppedGoalChecker::isGoalReached()` 先呼叫 `SimpleGoalChecker`；位置或 yaw 任一不合格就回傳 false，兩者合格後才檢查平移及旋轉速度。因此它不是「到達後另外觀察停止」的鬆散組合，而是同一次 goal-reached predicate 同時要求 pose 與 stop conditions。

`SimpleGoalChecker` 的 `stateful=true` 會在第一次通過 XY tolerance 後停止重複檢查 XY，接著只等待 yaw；此時 `StoppedGoalChecker` 也繼承該語意。若 SYS-016 要求成功當下仍重新符合 XY tolerance，應設定 `stateful=false`。若允許到達 XY window 後原地完成朝向與停止，才可採用 `stateful=true`。這是必須固定並驗證的 acceptance policy，不是 custom gap。

## 4. Stop Semantics and Velocity Source

Controller Server 的 goal check 並非使用送出的 `cmd_vel`。它透過 `nav_2d_utils::OdomSubscriber` 取得 raw odometry twist，先以 `min_x_velocity_threshold`、`min_y_velocity_threshold`、`min_theta_velocity_threshold` 將小量測值歸零，再交給 selected Goal Checker。`StoppedGoalChecker` 隨後以平面線速度大小及 z 軸角速度與自身停止門檻比較。

因此 SYS-016 的「底盤已停止」在此成熟方案中的精確語意是：

```text
configured odom velocity
  -> Controller Server minimum-velocity thresholding
  -> StoppedGoalChecker translational/rotational thresholds
  -> navigation-level stopped predicate
```

這比「controller 已送出零命令」更強，因為它使用回授 odometry；但它仍不等同 SYS-030 的 M1 wheel feedback、實際輪組停止確認及 drive disable。SYS-016 不應重複承擔 hardware-safe-stop contract。若未來產品要求只有 M1 hardware-confirmed wheel stop 才能宣告導航成功，必須回到 03 修改 requirement；不能把它暗中加入本次 reuse gap。

下列參數彼此有關，不能分開調整：

- `min_x_velocity_threshold`、`min_y_velocity_threshold`、`min_theta_velocity_threshold` 會先改變送入 checker 的小速度量測；
- `trans_stopped_velocity` 與 `rot_stopped_velocity` 決定何時視為停止；
- `xy_goal_tolerance`、`yaw_goal_tolerance` 與 `stateful` 決定 pose acceptance。

如果 minimum-velocity thresholds 過大，仍在緩慢移動的 AMR 可能先被視為零速；如果 stopped thresholds 過小，odometry noise 可能使成功永遠無法成立。這些不是成熟能力缺口，而是 SYS-016 明文要求的整合及實機驗證項目。

## 5. Completion Propagation

Navigation2 1.3.12 的 success chain 為：

```text
current pose + final path endpoint + odom twist
  -> StoppedGoalChecker returns true
  -> Controller Server exits control loop and publishes zero velocity
  -> FollowPath action succeeds
  -> standard NavigateToPose BT can return SUCCESS
  -> NavigateToPose action succeeds
```

Controller Server 比較的是目前 FollowPath path 的最後一個 pose。因此 composition 必須保證最後 active stage 的 endpoint 保留 resolved Navigation Target 的 position 與 orientation；中間 stage 的 `FollowPath` success 只能表示該 stage 完成，不能直接被解讀成整體導航成功。Stage selection／transition 仍屬 SYS-018～020，整體結果彙整仍屬 SYS-017；它們不是 SYS-016 的 custom behavior gap。

標準 NavigateToPose BT 以 `ComputePathToPose` 與 `FollowPath` 組成導航流程，只有 BT 最終回傳成功時，NavigateToPose 才成功。若後續三階段策略使用不同 BT composition，必須以 integration evidence 證明最後成功仍經過本項 predicate。

## 6. Configuration and Evidence Gaps

### Configuration / composition

- 將 final-stage `FollowPath.goal_checker_id` 固定到 `nav2_controller::StoppedGoalChecker`，不得沿用只檢查 pose 的預設 `SimpleGoalChecker`；
- 固定 `xy_goal_tolerance`、`yaw_goal_tolerance`、`trans_stopped_velocity`、`rot_stopped_velocity` 及 `stateful`；
- 固定 Controller Server 的 odom topic與三個 minimum-velocity thresholds；
- 確認 final path endpoint 保留 canonical target position/yaw；
- 維持 `FollowPath success -> final BT success -> NavigateToPose success`，且 intermediate-stage success 不會提前結束整體導航。

### Integration and real-hardware evidence

- 記錄 target image 中 Nav2 / `nav2_controller` exact installed versions及實際載入的 goal checker plugin ID；
- 對 XY、yaw、translation speed及rotation speed各門檻做 inside、boundary及outside 測試；
- 對 `stateful=true/false` 的最終 XY 行為做核准選項測試；
- 記錄 Goal Checker 實際使用的 odom topic、更新率、延遲、frame及速度來源；
- 量測 odometry noise、低速 creep、滑動、旋轉及停止 settling time，確認不會過早成功或永遠不成功；
- 證明最後 path endpoint與 resolved target一致，且只有 final stage completion 會形成 NavigateToPose success；
- 另由 SYS-029／SYS-030 evidence 證明 motor feedback 與 hardware-safe-stop 行為，不把 navigation-level odom stop 當成該證據。

## 7. Primary-source Evidence

### 7.1 Stopped and simple goal checks

- **Evidence Type:** ROS 2 Jazzy generated API and upstream exact-tag source
- **Sources:** [Jazzy 1.3.12 `StoppedGoalChecker` API](https://docs.ros.org/en/ros2_packages/jazzy/api/nav2_controller/generated/classnav2__controller_1_1StoppedGoalChecker.html)；[`stopped_goal_checker.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/plugins/stopped_goal_checker.cpp)；[`simple_goal_checker.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/plugins/simple_goal_checker.cpp)
- **Exact Version / Revision:** Navigation2 / `nav2_controller` 1.3.12
- **Observed Scope:** StoppedGoalChecker繼承pose/yaw acceptance，並額外以linear/angular velocity thresholds判斷停止；SimpleGoalChecker的XY、yaw與stateful implementation。
- **Limitations:** source capability不證明project configuration、odom semantics或實機門檻正確。
- **Access Date:** 2026-08-14

### 7.2 Controller Server velocity and completion behavior

- **Evidence Type:** upstream exact-tag source and official configuration documentation
- **Sources:** [`controller_server.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/src/controller_server.cpp)；[Controller Server configuration](https://docs.nav2.org/configuration/packages/configuring-controller-server.html)
- **Exact Version / Revision:** Navigation2 / `nav2_controller` 1.3.12
- **Observed Scope:** OdomSubscriber、minimum-velocity thresholding、path endpoint transformation、selected Goal Checker invocation、zero-velocity publication與FollowPath success。
- **Limitations:** actual odom source、thresholds、latency及physical stop須由project evidence確認。
- **Access Date:** 2026-08-14

### 7.3 FollowPath and NavigateToPose success chain

- **Evidence Type:** upstream exact-tag action definitions and BT source
- **Sources:** [`FollowPath.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/FollowPath.action)；[`NavigateToPose.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/NavigateToPose.action)；[`navigate_to_pose_w_replanning_and_recovery.xml` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml)；[`navigate_to_pose.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/src/navigators/navigate_to_pose.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** FollowPath selectable Goal Checker；standard NavigateToPose planning/tracking composition與action success boundary。
- **Limitations:** project三階段composition尚需integration evidence，SYS-017對外result aggregation不屬本項。
- **Access Date:** 2026-08-14

### 7.4 Exact release identity

- **Evidence Type:** official upstream release metadata
- **Source:** [Navigation2 release 1.3.12](https://github.com/ros-navigation/navigation2/releases/tag/1.3.12)
- **Exact Version / Revision:** tag 1.3.12, commit `6be3614`, Jazzy release dated 2026-04-29；target binary revision 1.3.12-1
- **Observed Scope:** exact upstream tag used for source inspection.
- **Limitations:** installed target binary version仍須另行記錄。
- **Access Date:** 2026-08-14

## 8. Recommended 04 Record

```text
SYS-016 Goal Completion
Candidate Mature Solution: Navigation2 Controller Server + FollowPath + StoppedGoalChecker + standard NavigateToPose BT (Jazzy 1.3.12-1)
Coverage Status: Fully Covered
Covered Scope: final target XY/yaw acceptance; odometry-derived translational/rotational stopped predicate; FollowPath-to-NavigateToPose success propagation
Custom Behavior Gap: None
Configuration / Composition Gap: StoppedGoalChecker selection; pose/velocity thresholds; stateful policy; odom topic/minimum thresholds; final endpoint preservation; final-stage BT success wiring
Evidence Gap: installed versions/plugin; threshold boundaries; odom source/noise/latency; low-speed and stop behavior; endpoint preservation; final-stage-only success; real-hardware verification
MVP Change Candidate: None
```
