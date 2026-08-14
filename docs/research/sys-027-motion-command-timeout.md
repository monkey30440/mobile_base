# SYS-027 Motion-command Timeout — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的下列定案需求，不修改或擴張需求：

> **SYS-027 運動命令逾時**：底盤執行運動期間，若系統未在設定之逾時時間內收到有效的新速度命令，應使底盤停止；逾時值與停止行為應經整合及實機驗證。

研究問題是：ROS 2 Jazzy `diff_drive_controller` 是否原生提供 stamped velocity command、command-age timeout 與停止用 wheel command；並區分成熟 controller capability、configuration/integration evidence、physical-stop evidence 與 custom behavior gap。

SYS-026、SYS-028、SYS-030、SYS-031 不在本筆記範圍。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` + `diff_drive_controller` |
| Exact Version / Platform | ROS 2 Jazzy；Ubuntu 24.04 Noble；Jazzy rosdistro release metadata：`ros2_controllers` 4.42.1-1 |
| Coverage Status | **Fully Covered**（成熟 controller capability 層級） |
| Covered Scope | 非 chained 模式下接收 `geometry_msgs/msg/TwistStamped`；依訊息 timestamp 計算 command age；超過非零 `cmd_vel_timeout` 後把 body linear/angular reference 設為 0，經已設定的 velocity/acceleration/jerk limits 後寫入左右輪 velocity command interfaces |
| Known Constraints | controller 必須 configured 且 active；`cmd_vel_timeout=0.0` 會停用 timeout；Jazzy 4.42.1 沒有 `use_stamped_vel` 選項，topic input 固定為 `TwistStamped`；chained mode 不使用此 subscriber-age timeout path |
| Uncovered Gap | `None`（SYS-027 沒有已知 Custom Behavior Gap） |
| Missing Evidence | target image exact version、timeout/configuration、clock/timestamp contract、controller update execution、hardware command delivery、deceleration profile、最壞停止時間與距離、實體底盤確實停止尚待整合及實機驗證 |
| MVP Change Candidate | `None` |

`Fully Covered` 表示成熟控制器已具有 SYS-027 所需的 command-timeout 與停止命令能力，不表示實體 AMR 已被證明停止。Controller 寫出零輪速目標或受限減速命令，仍需 hardware interface、motor drive、制動能力、地面條件及實機量測共同證明 physical stop。

## 3. Requirement Fragments

| Requirement fragment | Mature coverage | Remaining project dependency / evidence |
|---|---|---|
| 未在設定逾時內收到有效的新速度命令 | `cmd_vel_timeout` 定義 stale threshold；非 chained subscriber path 以 controller update time 減 `TwistStamped.header.stamp` 判斷 age | 選定非零 timeout；統一 clock/timestamp；驗證 producer rate、transport delay 與 controller update rate |
| 應使底盤停止 | timeout 將 linear/angular reference 設為 0；inverse kinematics 將最終 body command 轉成左右輪 velocity commands | 啟用 acceleration/jerk limits 時可能按限制減速；需驗證 hardware 實際接收、馬達反應及最終輪速/車速為零 |
| 逾時值與停止行為應經整合及實機驗證 | 官方原始碼與測試證明 controller-level behavior | 本專案仍須量測 timeout detection、command output、wheel feedback、停止時間及停止距離 |

## 4. Primary-source Evidence

### 4.1 Jazzy interface and automatic timeout capability

- **Evidence Type:** Official exact-distribution documentation
- **Source:** [Jazzy `diff_drive_controller` user documentation](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)
- **Exact Version / Revision:** ROS 2 Jazzy documentation；release family `ros2_controllers` 4.42.1-1 per Jazzy rosdistro metadata
- **Observed or Documented Scope:** 官方文件列出 automatic stop after command time-out；非 chained subscriber `~/cmd_vel` 的型別是 `geometry_msgs/msg/TwistStamped`；controller 的輸出是 wheel joint `HW_IF_VELOCITY` command interfaces；`cmd_vel_timeout` 預設為 0.5 秒。
- **Limitations:** 文件中的 automatic stop 是 controller command behavior，不是特定實體底盤停止距離或安全性能的證據。
- **Access Date:** 2026-08-14

### 4.2 Exact 4.42.1 timeout and wheel-command implementation

- **Evidence Type:** Official tagged source code
- **Source:** [`diff_drive_controller.cpp` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller.cpp)
- **Exact Version / Revision:** `ros-controls/ros2_controllers` tag `4.42.1`
- **Observed or Documented Scope:** `update_reference_from_subscribers()` computes `age_of_last_command = time - command_msg_.header.stamp`. When a nonzero timeout is exceeded, it writes 0.0 to linear and angular reference interfaces. `update_and_write_commands()` then applies configured speed limits, performs differential-drive inverse kinematics, and writes left/right wheel velocity command interfaces. The subscriber is created only for `TwistStamped`; it accepts commands only while the subscriber is active, replaces an all-zero timestamp with node current time, and rejects an already-old stamped message. `on_deactivate()` directly calls `halt()`, which writes 0.0 to wheel command interfaces.
- **Limitations:** Because speed limits are applied after the timeout reference becomes zero, configured acceleration/deceleration/jerk limits can make the wheel command approach zero over multiple update cycles rather than become zero in one cycle. Source-level writes do not prove hardware delivery or physical braking.
- **Access Date:** 2026-08-14

### 4.3 Exact 4.42.1 parameter semantics

- **Evidence Type:** Official tagged parameter definition
- **Source:** [`diff_drive_controller_parameter.yaml` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller_parameter.yaml)
- **Exact Version / Revision:** `ros-controls/ros2_controllers` tag `4.42.1`
- **Observed or Documented Scope:** `cmd_vel_timeout` is a double in seconds, defaults to 0.5, and 0.0 disables timeout. The exact parameter set contains no `use_stamped_vel`; this Jazzy version uses the stamped input contract directly.
- **Limitations:** The default value is not a project decision. SYS-027 requires the deployed value and resulting behavior to be verified.
- **Access Date:** 2026-08-14

### 4.4 Exact 4.42.1 tests

- **Evidence Type:** Official tagged test source
- **Source:** [`test_diff_drive_controller.cpp` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/test/test_diff_drive_controller.cpp)
- **Exact Version / Revision:** `ros-controls/ros2_controllers` tag `4.42.1`
- **Observed or Documented Scope:** The unchained-mode test waits beyond the default 0.5-second timeout and asserts both wheel command interfaces are 0.0. Another regression test verifies that `cmd_vel_timeout=0.0` preserves an old command. Lifecycle tests verify deactivation writes both wheel command interfaces to 0.0. Chained-mode tests set exported linear/angular reference interfaces directly rather than exercise the topic subscriber timeout.
- **Limitations:** These are controller unit tests with command interfaces, not integration or real-hardware stopping tests.
- **Access Date:** 2026-08-14

### 4.5 Stamped input is a Jazzy contract

- **Evidence Type:** Official exact-distribution migration guide
- **Source:** [ROS 2 Controllers Humble-to-Jazzy migration guide](https://control.ros.org/jazzy/doc/ros2_controllers/doc/migration.html#diff-drive-controller)
- **Exact Version / Revision:** ROS 2 Jazzy documentation
- **Observed or Documented Scope:** Jazzy requires the twist message on `~/cmd_vel` to be stamped.
- **Limitations:** Upstream publishers that only emit `geometry_msgs/msg/Twist` require an approved adapter or different producer configuration; that integration is not custom timeout behavior.
- **Access Date:** 2026-08-14

## 5. Important Behavioral Boundaries

### `TwistStamped` and command age

For exact Jazzy 4.42.1, `use_stamped_vel` is not a switch that can select stamped versus unstamped input. The controller's topic subscriber is `TwistStamped`. A nonzero timestamp participates in age validation; an all-zero timestamp is replaced with the controller node's current time. Therefore the deployed system should publish meaningful, clock-consistent timestamps instead of relying on the zero-timestamp compatibility behavior.

### Controller active and lifecycle

The subscription exists after configuration, but its callback rejects new commands while the subscriber is inactive. Activation requires the configured wheel interfaces to be available. Deactivation writes wheel velocity commands of 0.0 directly. Consequently, timeout verification must show the controller remains active and its update loop continues running during the command-loss scenario; an inactive or stalled control loop is not evidence that the timeout logic ran.

### Chained mode

The command-age timeout is implemented in `update_reference_from_subscribers()`. In chained mode, a preceding controller writes exported linear/angular reference interfaces directly, and the official chained-mode test does not exercise `cmd_vel` timestamp age. Therefore this assessment treats the native `cmd_vel_timeout` coverage as applying to **non-chained topic input**. If architecture later selects chained mode, the preceding controller or chain composition must provide and verify an equivalent freshness/timeout contract; this reuse record must then be revisited.

### Zero target versus physical stop

On timeout the controller first requests zero body velocity. It then applies configured velocity, acceleration and jerk limits before calculating wheel commands. Thus there are two valid controller-level stop profiles:

- without an active deceleration/jerk constraint, the computed wheel velocity target becomes zero immediately in that update;
- with such constraints, the controller can emit a bounded ramp toward zero over subsequent updates.

Neither profile by itself proves the AMR physically stopped. Physical proof requires wheel feedback or independent motion observation, plus measured timeout detection, stop time and stop distance under the approved payload, speed, floor, hardware and drive conditions.

## 6. Gap Classification

### Mature Capability

The non-chained Jazzy `diff_drive_controller` covers the required behavior without a custom watchdog node: it receives stamped commands, detects stale command age, replaces the motion reference with zero and sends the resulting wheel velocity commands through standard ros2_control interfaces.

### Configuration Gap

- Pin the installed `ros2_controllers` version on the target image.
- Use non-chained `TwistStamped` input for this native timeout path.
- Select a nonzero `cmd_vel_timeout`; 0.0 is prohibited for satisfying SYS-027 because it disables timeout.
- Establish compatible clocks and meaningful producer timestamps.
- Decide whether timeout stop is immediate zero-target behavior or a configured limited-deceleration profile, including acceleration/jerk parameters.
- Keep the controller update loop and hardware interface operational during upstream command loss.

### Integration and Evidence Gap

- Verify fresh commands are accepted and stale commands are rejected or timed out at the intended boundary.
- Measure the time from the last valid command timestamp to zero/reference-ramp output.
- Observe the wheel command interfaces and downstream hardware writes.
- On the physical AMR, verify wheel feedback and body motion reach zero; record worst-case stop time and distance under representative operating conditions.
- Exercise timestamp skew, command interruption and recovery with the chosen control/update rates.

### Custom Behavior Gap

`None` for the approved non-chained composition. A custom timeout component is not justified by SYS-027.

If a later architecture decision introduces chained mode, this conclusion is conditional: freshness ownership must be allocated upstream, and the assessment may no longer remain `Fully Covered` without another mature timeout mechanism.

## 7. Handoff to 04 Assessment

Recommended 04 conclusion:

- **Coverage Status:** `Fully Covered` at mature-solution capability level, conditional on non-chained `TwistStamped` input and nonzero `cmd_vel_timeout`.
- **Candidate composition:** the same ROS 2 Jazzy `ros2_control` + `diff_drive_controller` selected for SYS-022.
- **Controller behavior:** stale command age sets body velocity reference to zero; configured limiters may shape the transition; resulting wheel velocity commands go to ros2_control command interfaces.
- **Custom gap:** `None`.
- **Non-custom gaps:** exact installed-version pinning, timeout/timestamp/clock/limiter configuration, active update-loop integration, hardware delivery evidence and physical-stop evidence.
- **Architecture consideration:** if chained mode is selected later, explicitly reallocate command-freshness ownership and revisit this coverage decision.
- **MVP simplification:** none justified.

## 8. Search Boundary

The search covered the exact SYS-027 wording, the already-selected SYS-022 controller composition, ROS 2 Jazzy official `diff_drive_controller` documentation and migration guide, and the official `ros2_controllers` 4.42.1 tagged implementation, parameter definition and tests. Since that mature controller directly provides the required non-chained timeout behavior, no custom watchdog or second controller candidate was introduced.
