# SYS-029 Base State Feedback — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-029 底盤狀態回授**：系統應提供由馬達驅動器有效回授所取得之左右輪位置與速度狀態，供里程估測、控制與診斷使用；無有效回授時，系統不得以命令值取代量測狀態，並應將狀態視為不可用或故障。

研究範圍限於 ROS 2 Jazzy `ros2_control` 4.47.0、`ros2_controllers` 4.42.1 與已核准的 M1Driver/M1Hardware design baseline。SYS-026 目前只規定 hardware interface 回傳 `ERROR` 後停止相關 controller 並使錯誤狀態可被觀察；本評估不重新加入舊版 SYS-026 的 fault latch、JG0、實體停止確認或 recovery policy。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` `SystemInterface` state interfaces + `diff_drive_controller` closed-loop feedback + `joint_state_broadcaster` |
| Exact Version / Platform | ROS 2 Jazzy；Ubuntu 24.04 Noble；`ros2_control` 4.47.0；`ros2_controllers` 4.42.1 |
| Coverage Status | **Partially Covered** |
| Covered Scope | framework 可承載左右輪 `position`／`velocity` state interfaces；`diff_drive_controller` closed-loop 模式會使用 wheel position 或 velocity feedback；broadcaster 可將 state interfaces 發布供觀察；hardware cycle 可用 `ERROR` 表達失敗 |
| Known Constraints | `open_loop=true` 不使用外部 state interfaces，而以 command 計算 odometry，因此不得用來滿足 SYS-029；framework 不理解 M1 protocol、driver identity、feedback freshness 或 raw-unit semantics |
| Uncovered Gap | 已必要的 M1Driver/M1Hardware device-specific behavior：取得並驗證兩顆馬達回授、左右輪映射、RPM/position 換算、連續位置追蹤、fresh/valid state 判斷，以及無有效回授時不得更新成命令值並回報硬體週期失敗 |
| Missing Evidence | target image exact installed versions；M1Hardware state export、closed-loop controller composition、freshness/failure path、broadcaster output、里程估測/控制消費及 target-AMR 實機資料一致性 |
| MVP Change Candidate | `None` |

成熟 framework 已提供標準資料通道、closed-loop consumer 與 error seam，但無法自動產生或判斷 M1-specific measured state。由於 SYS-029 明確要求「馬達驅動器有效回授」與「不得以命令值取代」，因此不能只憑 state interface 或 topic 存在判定 `Fully Covered`。

## 3. Requirement Fragments

| Requirement fragment | Mature framework coverage | Minimum remaining behavior / evidence |
|---|---|---|
| 提供左右輪位置與速度 | 標準 joint `position`／`velocity` state interfaces；可由 broadcaster 發布 | M1Driver 取得兩顆馬達 state；M1Hardware 映射左右輪並轉為 ROS joint units |
| 回授必須來自馬達驅動器且有效 | `SystemInterface::read()` 要求以 physical hardware readings 更新 exported state；失敗可回 `ERROR` | M1-specific response validation、driver ID mapping、latest-state availability/freshness 與 semantic health 判斷 |
| 供里程估測與控制使用 | `diff_drive_controller` closed-loop 使用 position feedback，或在 `position_feedback=false` 時使用 velocity feedback | 選定 feedback mode、正確 claim interfaces，驗證 controller 實際消費 measured state |
| 供診斷使用 | `joint_state_broadcaster` 可發布 movement state；`dynamic_joint_states` 可發布所有 available interfaces | Topic 值本身不證明 fresh/valid；若需 fault 原因或 age 欄位，必須由後續 requirement/architecture 明確定義，不能在本評估中新增 |
| 無有效回授時不得以命令取代 | closed-loop 模式可避免 controller 的 open-loop command substitution | M1Hardware 不得把 command copy 到 state，不得把 invalid exchange 當新 sample，並須走既定 hardware `ERROR` path |
| 狀態視為不可用或故障 | hardware `read()`／`write()` 可回 `ERROR`；Controller Manager 對使用該 hardware interfaces 的 controller 執行 error handling | M1Hardware 決定何者構成 no-valid/latest-state failure；驗證 failure 被傳遞且舊值不再被當作有效 measurement |

## 4. Primary-source Evidence

### 4.1 ros2_control state and error contract

- **Evidence Type:** Official exact-tagged API source and documentation
- **Sources:** [`HardwareComponentInterface` at `ros2_control` 4.47.0](https://github.com/ros-controls/ros2_control/blob/4.47.0/hardware_interface/include/hardware_interface/hardware_component_interface.hpp#L162-L195)；[`read()` contract](https://github.com/ros-controls/ros2_control/blob/4.47.0/hardware_interface/include/hardware_interface/hardware_component_interface.hpp#L264-L288)；[read/write error handling](https://github.com/ros-controls/ros2_control/blob/4.47.0/hardware_interface/doc/handling_errors_during_read_write.rst#L3-L9)
- **Exact Version / Revision:** `ros-controls/ros2_control` tag `4.47.0`, commit `df23a4b7`
- **Observed Scope:** hardware component exports state interfaces backed by its state storage；`read()` must update those interfaces from physical hardware readings and returns `OK` on success or `ERROR` otherwise. A read/write `ERROR` enters the hardware error-handling path.
- **Limitations:** The generic API does not define M1 packet validity, sample freshness, driver mapping, raw position rollover, RPM conversion or alarm semantics. The conclusion that these decisions remain in M1Driver/M1Hardware is an inference from the generic contract plus the approved local device baseline.
- **Access Date:** 2026-08-14

### 4.2 Controller Manager reaction to hardware failure

- **Evidence Type:** Official exact-tagged documentation
- **Source:** [`Controller Manager` hardware error behavior at `ros2_control` 4.47.0](https://github.com/ros-controls/ros2_control/blob/4.47.0/controller_manager/doc/userdoc.rst#L555-L559)
- **Exact Version / Revision:** `ros2_control` 4.47.0
- **Observed Scope:** when hardware `read()` or `write()` returns `ERROR`, Controller Manager stops controllers that use the hardware's command and state interfaces.
- **Limitations:** This provides the framework failure seam used by the already-simplified SYS-026. It does not by itself identify which cached M1 sample is valid/fresh, nor does it define a new detailed diagnostic or recovery requirement for SYS-029.
- **Access Date:** 2026-08-14

### 4.3 Exact diff_drive_controller feedback semantics

- **Evidence Type:** Official exact-tagged documentation, source and parameter definition
- **Sources:** [`diff_drive_controller` 4.42.1 interface documentation](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/doc/userdoc.rst#L40-L49)；[state-interface selection source](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller.cpp#L88-L104)；[feedback/open-loop update path](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller.cpp#L184-L230)；[parameter defaults](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller_parameter.yaml#L79-L87)
- **Exact Version / Revision:** `ros-controls/ros2_controllers` tag `4.42.1`, commit `aacd8426`
- **Observed Scope:** default `open_loop=false` and `position_feedback=true` claims wheel position state interfaces. With `position_feedback=false`, closed-loop operation claims velocity state interfaces. With `open_loop=true`, the controller claims no external wheel state interfaces and updates odometry from commanded body velocity.
- **SYS-029 consequence:** Either closed-loop feedback type can be a mature consumer of measured state, but `open_loop=true` is incompatible with the requirement's no-command-substitution clause. If both position and velocity must remain generally available to control/odometry/diagnostics, M1Hardware still exports both even if one controller mode claims only one type.
- **Access Date:** 2026-08-14

### 4.4 State publication for observation

- **Evidence Type:** Official exact-tagged documentation and parameter definition
- **Sources:** [`joint_state_broadcaster` 4.42.1 user documentation](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/joint_state_broadcaster/doc/userdoc.rst#L15-L49)；[`publish_dynamic_joint_states` parameter](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/joint_state_broadcaster/src/joint_state_broadcaster_parameters.yaml#L67-L71)
- **Exact Version / Revision:** `ros2_controllers` 4.42.1
- **Observed Scope:** `/joint_states` publishes standard position/velocity/effort movement interfaces；`/dynamic_joint_states` can publish every available state interface for each joint and is enabled by default in this exact version.
- **Limitations:** A received topic/value proves the state-export-to-topic path and the value observed at that instant. Neither topic inherently proves that the device transaction succeeded in every control cycle, that a value is fresh, or that M1 semantic validation passed. A separate custom freshness topic is not inferred as a SYS-029 requirement.
- **Access Date:** 2026-08-14

## 5. Approved Local Baseline Evidence

### 5.1 M1Driver measurement source

`docs/design_baseline/m1_driver.md` freezes the following relevant behavior:

- `MotorState` contains `driver_id`, integer `actual_rpm`, signed-int32 `position_steps`, `status` and `alarm`;
- one FC17 `exchange()` writes both motor RPM commands and simultaneously returns both motor states;
- response validation checks function, exception, length and selected-driver payload/order before parsing;
- FC17 JG/RPM plus simultaneous state feedback has real-hardware `PASS` evidence;
- M1Driver preserves motor-domain values and driver identity; it does not infer robot left/right meaning, unwrap position or convert wheel units.

This proves that the selected M1 protocol can supply the required raw measurements. It does not prove the full ROS joint-state path or runtime freshness/failure behavior.

### 5.2 M1Hardware state semantics

`docs/design_baseline/m1_hardware.md` assigns already-required device adaptation to M1Hardware:

- export left/right wheel `position [rad]` and `velocity [rad/s]` state interfaces;
- map driver IDs to left/right and apply gear ratio/motor sign conversion;
- convert `actual_rpm` to wheel velocity;
- use one `PositionTracker` per motor to turn signed-int32 raw position into continuous relative wheel position across rollover;
- under the A2 loop, `write()` performs FC17 exchange and caches the returned state, while the following `read()` validates and consumes `latest_motor_state_` without another transaction;
- a successful exchange replaces the cache；communication/protocol failure propagates upward；`read()` must not fabricate state when no valid state exists.

These behaviors are not a new subsystem invented by SYS-029 research. They are the minimum device-specific portion already inherent in the approved M1Hardware boundary.

## 6. Validity and Unavailability Semantics

### What the framework can express

- Valid measured values are exported through standard joint state interfaces.
- A failed hardware cycle is expressed with `hardware_interface::return_type::ERROR` and reaches Controller Manager error handling.
- Standard broadcasters can expose the last values held by the state interfaces.

### What the M1 boundary must decide

- whether an FC17/FC03 transaction is structurally valid and belongs to the expected drivers;
- whether a cached sample exists and is fresh enough for the current A2 control-loop contract;
- whether status/alarm makes a structurally valid sample unacceptable under the separately approved device-health policy;
- whether conversion inputs and outputs are finite/representable;
- when to replace the last valid cache and when to return `ERROR` without publishing command-derived state.

### No invented reporting contract

SYS-029 requires invalid feedback to be treated as unavailable or faulty, but does not prescribe a new ROS topic, custom state interface, error code taxonomy, retention period or recovery API. The minimum assessment conclusion is therefore:

1. do not replace measurement with command values;
2. do not accept an invalid transaction as a new valid sample;
3. propagate the condition through the standard hardware `ERROR` path;
4. do not let a previously cached numeric value be interpreted as continuing valid measurement after the failure.

The exact diagnostic representation beyond existing hardware/controller error observability belongs to later architecture only if another approved requirement demands it.

## 7. Gap Classification

### Mature Capability

- standard `position` and `velocity` state interfaces;
- controller-side selection and use of closed-loop wheel position or velocity feedback;
- standard state broadcasting;
- hardware-cycle `ERROR` and Controller Manager reaction.

### Configuration Gap

- pin target-image versions to `ros2_control` 4.47.0 and `ros2_controllers` 4.42.1 or reassess the installed versions;
- configure `open_loop=false`;
- select `position_feedback=true` for position-based wheel odometry or `false` for velocity feedback, while retaining both exported state interfaces for other consumers;
- configure joint names/interfaces consistently among URDF ros2_control description, M1Hardware, controller and broadcaster.

### Composition Gap

- compose M1Hardware state interfaces with the selected closed-loop `diff_drive_controller` mode and a standard broadcaster where ROS-topic observability is needed;
- ensure the A2 cached-state timing is included in control-loop/freshness validation.

### Custom Behavior Gap

Within the already-required M1Driver/M1Hardware device boundary:

- M1 response validation and dual-driver state acquisition;
- driver-to-wheel mapping and motor-to-wheel unit/sign conversion;
- continuous position tracking across raw-counter rollover;
- availability/freshness/health decision for `latest_motor_state_`;
- no command-to-state substitution and propagation of invalid/no-feedback as hardware `ERROR`.

No separate custom feedback node, estimator or diagnostic framework is justified by SYS-029.

### Evidence Gap

- unit tests for signed RPM/position decode, driver order, sign/gear conversion, position initialization/rollover and invalid/no-cache behavior;
- fake-driver tests showing only successful valid exchange replaces the cache and invalid feedback returns `ERROR` without command substitution;
- runtime evidence that both wheel position/velocity interfaces contain converted measured feedback and the selected controller is closed-loop;
- runtime observation of `/joint_states` or `/dynamic_joint_states`, explicitly separated from freshness proof;
- target-AMR comparison of reported wheel direction, velocity and position progression against physical motion;
- fault injection for timeout, malformed response, missing driver block and invalid cached state, showing the data is treated unavailable/faulty.

## 8. Handoff to 04 Assessment

Recommended 04 conclusion:

- **Coverage Status:** `Partially Covered`.
- **Candidate:** ROS 2 Jazzy `ros2_control` 4.47.0 + `diff_drive_controller` and `joint_state_broadcaster` 4.42.1.
- **Mature covered scope:** standard wheel state transport, closed-loop feedback consumption, state publication and hardware error propagation seam.
- **Minimum Custom Behavior Gap:** M1-specific measurement acquisition/validation, driver mapping, unit/sign conversion, continuous-position tracking and cached-state validity/freshness enforcement inside the already-required M1Driver/M1Hardware boundary.
- **Prohibited configuration:** `open_loop=true`, because commanded values replace external feedback for controller odometry.
- **Evidence gaps:** exact installed versions, A2 cache timing/freshness, conversion correctness, closed-loop consumption, failure propagation and target-hardware validation.
- **MVP Change Candidate:** `None`.

## 9. Search Boundary

The search covered the current SYS-029 wording, exact official tagged sources for `ros2_control` 4.47.0 and `ros2_controllers` 4.42.1, and only the approved M1Driver/M1Hardware baseline sections needed to determine the device boundary. SYS-026 was used only to avoid contradicting its current simplified error-handling rule. This research did not assess odometry fusion, physical stopping, recovery policy, custom diagnostic schemas or any requirement after SYS-029.
