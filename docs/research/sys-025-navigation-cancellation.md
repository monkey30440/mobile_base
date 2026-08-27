> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-025 Navigation Cancellation — Reuse Research

## 1. Research Scope

本筆記研究目前定案的 SYS-025：

> 系統應接受使用者對進行中導航任務提出之取消要求，終止該導航任務，並回報取消結果。

相鄰責任邊界保持分離：

- SYS-017：彙整並對外回報整體 Navigation Result（包含 `CANCELED`、`SUCCEEDED`、`ABORTED`）；
- SYS-011／014／015：各 child action（planning、avoidance、tracking）在接收到 halt/cancel 時的個別行為；
- SYS-022／027／028：底盤速度控制、命令逾時停止與運動限制；
- SYS-030：安全停機與實體硬體 stop confirmation / drive disable。

本項聚焦於：
1. 使用者／terminal 發出取消請求至 Nav2 action server 之接收與狀態轉移；
2. 進行中導航行為樹（BT）與 child action 之有序終止及停止命令下發；
3. 取消結果之確定性回報與競態條件（race condition）處理。

候選成熟方案為 ROS 2 Jazzy action cancel 協定、Navigation2 1.3.12-1 `NavigateToPose`、BT Navigator（`BtActionServer`）及 BT Action Node 級聯取消機制。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy action cancel protocol + Navigation2 1.3.12-1 `NavigateToPose` + `BtActionServer` / BT Navigator + child action cancellation (`FollowPath`, `ComputePathToPose`, `ComputeRoute`) |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2／`nav2_msgs` Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 接收進行中導航之 cancel goal request；BT root halt 並級聯取消 active child actions；Controller Server 終止路徑追蹤並下發零速度命令；回傳標準 terminal `CANCELED` action result |
| Known Constraints | Cancel request accepted 僅表示進入 `CANCELING` 狀態，terminal client 必須等待最終 `CANCELED` result；若取消請求與目標達成（Success）或失敗（Abort）並發，依 ROS 2 action 語意以 server 處理當下狀態決定最終 terminal state；零速度下發為 navigation-level 停止，實體減速停止受限於底盤加減速限制與運動學 |
| Uncovered Gap | **None**；不需要自訂 cancellation watchdog、額外取消管理服務或客製化導航取消框架 |
| Configuration / Composition Gap | Terminal / Client 端 cancel-goal 與 wait-for-result 呼叫模式；BT tree halt 與 child cancel timeout 配置；`cmd_vel` 零速發布與 downstream controller 整合 |
| Missing Evidence | Target image installed exact versions；在 planning、tracking、recovery 及三階段各 stage 下之取消整合驗證；取消與即將成功／失敗之競態情境驗證；零速度發布與實體停止之時序量測；Terminal 端取消反饋與最終結果呈現驗證 |
| MVP Change Candidate | `None` |

成熟方案已完整具備 SYS-025 所需之取消接收、執行終止與結果回報機制，不需新增 custom implementation。

## 3. Action Cancellation Protocol and Lifecycle

ROS 2 Jazzy Action Cancel 生命週期如下：

```text
[Client]                            [NavigateToPose / BtActionServer]
   |                                                |
   |--- async_cancel_goal(goal_handle) ------------>|
   |                                                | handle_cancel callback:
   |                                                | (check goal is_active)
   |<-- CancelResponse (ACCEPT / REJECT) -----------| (Goal transitions to CANCELING)
   |                                                |
   |                                                | execute loop:
   |                                                |   detect is_canceling()
   |                                                |   tree.rootNode()->halt()
   |                                                |   -> cascade halt to active child nodes
   |                                                |   -> cancel active FollowPath / ComputePath
   |                                                |   publish zero velocity / on_cancel()
   |                                                |   goal_handle->canceled(result)
   |<-- Result Callback (code: STATUS_CANCELED) ----| (Goal transitions to CANCELED)
```

1. **Cancel Request Acceptance**：
   - Action client 發送 `async_cancel_goal()`；
   - Action server 透過 `handle_cancel` callback 檢查目標是否為 active；若是則回傳 `CancelResponse::ACCEPT`，目標狀態轉為 `CANCELING`。
   - 若目標已經進入 terminal state（已 Succeeded 或 Aborted），則回傳 `CancelResponse::REJECT`。
2. **Execution Halt and Child Cancellation**：
   - `BtActionServer` 在主迴圈偵測到 `goal_handle->is_canceling()`；
   - 呼叫 Behavior Tree 的 `rootNode()->halt()` / `haltTree()`；
   - Active 的 BT Action Node（例如 `FollowPathAction`、`ComputePathToPoseAction`）在其 `halt()` 實作中主動向底層 child action server 發送取消請求。
3. **Terminal Result Delivery**：
   - 在完成清理與停止後，`BtActionServer` 呼叫 `goal_handle->canceled(result)`；
   - Goal 狀態轉入 `STATUS_CANCELED`，並將 `error_code` 與 `error_msg` payload 隨 action result 送回 client。
   - Client 的 result callback 收到 `rclcpp_action::ResultCode::CANCELED`。

## 4. Stop Command and Authority Boundary

在取消導航時，系統對底盤運動停止的處理層次如下：

1. **Navigation-level Stop (Nav2)**：
   - 當 `FollowPath` 接收到 cancel 或被 halt 時，`ControllerServer` 退出控制迴圈，並主動在 `cmd_vel` 發布零速度命令（`linear = 0, angular = 0`）。
   - `BtActionServer` 亦具備在終止時確保零速度輸出的機制。
2. **Base Controller Timeout and Motion Limits (ros2_control)**：
   - 若導航節點在取消過程中停止發布速度命令，`diff_drive_controller` 之 `cmd_vel_timeout`（SYS-027）將確保底盤超時煞停。
   - 減速過程遵守 `diff_drive_controller` 之減速度限制（SYS-028）。
3. **Safety Stop Separation (SYS-030)**：
   - 導航取消屬於正常任務終止（Graceful task termination），透過發布零速度讓底盤平順減速停止。
   - 這與 SYS-030 的安全急停（Emergency / Safe Stop with hardware confirmation & drive disable）有明確責任分離，不應混淆。

## 5. Race Conditions and Boundary Scenarios

在實際運作中需處理以下競態與邊界情況：

| 情境 | 機制與行為 | 預期結果 |
|---|---|---|
| **任務執行中取消** | Goal 處於 `EXECUTING`，收到 cancel 後進入 `CANCELING`，BT halt，下發零速 | 最終 Action status 為 `CANCELED` |
| **即將成功時取消 (Cancel/Success Race)** | AMR 已達目標且 `StoppedGoalChecker` 成立，BT 正在完成 `SUCCESS` 結算時收到 cancel | 若 server 已完成 success 結算，cancel 被 reject，最終回傳 `SUCCEEDED`；若在結算前收到，則依 cancel 流程回傳 `CANCELED` |
| **即將失敗時取消 (Cancel/Abort Race)** | 規劃失敗或碰撞偵測觸發 BT `FAILURE` 時收到 cancel | 若 BT 已結算為 failure，最終回傳 `ABORTED`；若尚未結算則轉為 `CANCELED` |
| **已終止任務重複取消** | 對已為 `SUCCEEDED`、`ABORTED` 或 `CANCELED` 的 Goal 發送取消 | Action Server 回傳 `CancelResponse::REJECT`，不影響原已終止之結果 |
| **未有進行中任務時取消** | 無 active goal handle | Client 端或介面層拒絕請求，不觸發無效 server 呼叫 |

## 6. Configuration and Evidence Requirements

### Configuration / composition

- Terminal / Client 端必須採非同步 cancel 模式：發送 `async_cancel_goal` 後，以 `async_get_result` 監聽最終結果，不得將 `cancel_goal` 的 response 直接當成終止完成；
- BT Navigator 與 child action servers 保持標準 cancel handling 配置；
- 確認 Controller Server 與 BT Navigator 在 cancel/halt 時具備零速度發布行為；
- 速度命令鏈路（`cmd_vel_nav` -> multiplexer -> `diff_drive_controller`）確保零速命令無阻礙傳遞。

### Integration and real-hardware evidence

- 記錄 target image 之 exact versions（ROS 2 Jazzy、Navigation2 1.3.12-1）；
- **階段取消驗證**：在 Path Planning 階段、First Mile 階段、On Route 階段、Last Mile 階段及 Recovery 階段分別觸發取消，驗證 BT 有序 halt 與 child action 終止；
- **競態測試**：模擬目標達成瞬間、規劃失敗瞬間之並發 cancel 請求，驗證狀態機無 deadlock 且回傳合規之 terminal status；
- **停止與時序量測**：量測發送 cancel 到 Controller Server 發布零速、以及 odometry 速度降至零之時間與距離；
- **Terminal 呈現驗證**：驗證終端使用者介面能正確顯示「取消請求已送出」與「導航已取消（`CANCELED`）」之狀態與結果。

## 7. Primary-source Evidence

### 7.1 ROS 2 Action Cancel Protocol

- **Evidence Type:** official ROS 2 Jazzy documentation & rclcpp_action API
- **Sources:** [ROS 2 Actions Design & Overview](https://docs.ros.org/en/jazzy/How-To-Guides/Topics-Services-Actions.html)；[rclcpp_action::ServerGoalHandle API](https://docs.ros.org/en/ros2_packages/jazzy/api/rclcpp_action/generated/classrclcpp__action_1_1ServerGoalHandle.html)
- **Exact Version / Revision:** ROS 2 Jazzy / `rclcpp_action`
- **Observed Scope:** Action cancel state machine (`is_canceling`, `canceled()`, `CancelResponse::ACCEPT/REJECT`, `STATUS_CANCELED`)。
- **Access Date:** 2026-08-14

### 7.2 Navigation2 BT Action Server Cancellation & Halting

- **Evidence Type:** official Jazzy generated source and upstream exact-tag source
- **Sources:** [Jazzy `bt_action_server_impl.hpp`](https://api.nav2.org/nav2-jazzy/html/bt__action__server__impl_8hpp_source.html)；[`bt_action_server.hpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_server.hpp)；[`bt_action_node.hpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_node.hpp)
- **Exact Version / Revision:** Navigation2 / `nav2_behavior_tree` 1.3.12, commit `6be3614`
- **Observed Scope:** `BtActionServer` on cancel callback, tree root halt, `BtActionNode::halt()` sending child cancel requests, and setting goal to `canceled()`.
- **Access Date:** 2026-08-14

### 7.3 Controller Server Stop on Cancel

- **Evidence Type:** upstream exact-tag source
- **Sources:** [`controller_server.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/src/controller_server.cpp)
- **Exact Version / Revision:** Navigation2 / `nav2_controller` 1.3.12
- **Observed Scope:** `FollowPath` cancel callback, execution loop break, publishing zero velocity command on exit/cancel.
- **Access Date:** 2026-08-14

## 8. Recommended 04 Record

```text
SYS-025 Navigation Cancellation
Candidate Mature Solution: ROS 2 action cancel protocol + Navigation2 NavigateToPose / BtActionServer + child action cancellation (Jazzy 1.3.12-1)
Coverage Status: Fully Covered
Covered Scope: cancel goal request acceptance; BT root halting and child action cancellation; zero-velocity command publishing; returning standard terminal CANCELED result
Custom Behavior Gap: None
Configuration / Composition Gap: client cancel-and-wait-result handling; BT tree halt and child cancel timeout; cmd_vel zeroing across velocity pipeline
Evidence Gap: installed versions; cancellation during planning/tracking/recoveries; cancel/success/abort race scenarios; zero-cmd delivery and physical stop timing; terminal-visible feedback and result
MVP Change Candidate: None
```
