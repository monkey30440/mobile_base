> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-028 Base Motion Limits — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-028 底盤運動限制**：系統應將 AMR 的直線與旋轉速度，以及相應的加速與減速，限制於設定之 operational limits；限制值應依操作需求選定，並於部署前完成整合及實機驗證。

研究問題是：ROS 2 Jazzy `diff_drive_controller` 4.42.1 是否原生覆蓋 AMR body-domain 的 linear/angular velocity、acceleration 與 deceleration limits。Wheel joint velocity 與 motor RPM 只屬下游換算與配置結果，不是目前 SYS-028 的 requirement fragments，也不據此建立 Custom Behavior Gap。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `diff_drive_controller` built-in linear/angular `SpeedLimiter` |
| Exact Version / Platform | ROS 2 Jazzy；Ubuntu 24.04 Noble；`ros2_controllers` 4.42.1 |
| Coverage Status | **Fully Covered**（成熟 controller capability 層級） |
| Covered Scope | 分別限制 `linear.x` 與 `angular.z` 的正/反向 velocity，以及正/反向 acceleration/deceleration；限制後才執行 differential-drive inverse kinematics |
| Known Constraints | 所需數值預設為 `.NAN`，代表未啟用；必須明確配置；limiter 依賴前兩次已限制命令與 controller update period；controller 必須 configured/active 且 update loop 正常執行 |
| Uncovered Gap | `None`（SYS-028 沒有已知 Custom Behavior Gap） |
| Missing Evidence | operational limit 數值尚須依操作需求選定；target image exact version、參數、update timing、整合行為及實體 AMR 速度/加減速尚待驗證 |
| MVP Change Candidate | `None` |

`Fully Covered` 表示成熟 controller 已提供目前 SYS-028 要求的 body motion limiting behavior，不表示限制值已選定或實體 AMR 已符合限制。後者仍是 configuration、integration 與 real-hardware evidence gap。

## 3. Requirement Fragments

| Requirement fragment | Mature coverage | Remaining configuration / evidence |
|---|---|---|
| AMR 直線速度限制 | `linear.x.min_velocity` / `max_velocity` | 依允許前進與後退速度明確設定 finite values |
| AMR 旋轉速度限制 | `angular.z.min_velocity` / `max_velocity` | 依允許順/逆時針速度明確設定 finite values |
| 直線加速與減速限制 | `linear.x.max_acceleration`、`max_deceleration`、`max_acceleration_reverse`、`max_deceleration_reverse` | 決定正向/反向是否對稱，並驗證實際 ramp |
| 旋轉加速與減速限制 | `angular.z` 下同一組 acceleration/deceleration parameters | 決定正/負旋轉是否對稱，並驗證實際 ramp |
| 依操作需求選定 | 參數允許專案配置 operational envelope | 專案須依場域、載重、操控與導航需求選值 |
| 部署前整合及實機驗證 | 官方 source/tests 證明 controller-level limiter behavior | 專案須量測 controller output 與實體 AMR body motion |

## 4. Primary-source Evidence

### 4.1 Exact 4.42.1 limiting path

- **Evidence Type:** Official tagged source
- **Source:** [`diff_drive_controller.cpp` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller.cpp)
- **Exact Version / Revision:** `ros-controls/ros2_controllers` tag `4.42.1`, commit `aacd842600a09d556b983ac3d53a0983e9ebcbb1`
- **Observed Scope:** `update_and_write_commands()` 先取得 body `linear` / `angular` references，再以獨立的 `limiter_linear_` 與 `limiter_angular_` 限制兩者。限制後的值被保存到 two-command history，接著才用 wheel separation/radius 執行 inverse kinematics 並寫出 wheel commands。若 `publish_limited_velocity=true`，`~/cmd_vel_out` 發布限制後的 body twist。
- **Limitations:** Source-level behavior不證明本專案已配置限制、update loop timing 符合預期或實體 AMR 已遵守 body motion envelope。
- **Access Date:** 2026-08-14

### 4.2 Exact velocity and acceleration/deceleration parameters

- **Evidence Type:** Official tagged generated-parameter definition
- **Source:** [`diff_drive_controller_parameter.yaml` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller_parameter.yaml)
- **Exact Version / Revision:** `ros2_controllers` 4.42.1
- **Observed Scope:** `linear.x` 與 `angular.z` 各自提供：
  - `min_velocity`（應為 <= 0）與 `max_velocity`（應為 >= 0）；
  - `max_acceleration`（正方向加速，>= 0）；
  - `max_deceleration`（正方向減速，<= 0）；
  - `max_acceleration_reverse`（負方向加速，<= 0）；
  - `max_deceleration_reverse`（負方向減速，>= 0）。
- **Enable semantics:** 這些數值預設為 `.NAN`。`SpeedLimiter` 明確定義對應 max value 為 `NAN` 時停用該限制；未指定的 opposite-direction value 會由另一方向值推導成對稱限制。舊 `has_velocity_limits` / `has_acceleration_limits` 參數已 deprecated；若設為 `false`，4.42.1 會把相應數值改成 `NAN`。
- **Limitations:** 預設存在參數不等於限制已啟用。部署配置不得依賴預設 `.NAN`。
- **Access Date:** 2026-08-14

### 4.3 Exact limiter algorithm and history dependency

- **Evidence Type:** Official tagged wrapper and first-party dependency API
- **Sources:** [`speed_limiter.hpp` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/include/diff_drive_controller/speed_limiter.hpp)；[`control_toolbox::RateLimiter` Jazzy API](https://docs.ros.org/en/jazzy/p/control_toolbox/generated/classcontrol__toolbox_1_1RateLimiter.html)
- **Exact Version / Revision:** `ros2_controllers` 4.42.1 / ROS 2 Jazzy `control_toolbox`
- **Observed Scope:** `SpeedLimiter::limit(v, v0, v1, dt)` delegates to `control_toolbox::RateLimiter` and limits velocity, first derivative（acceleration/deceleration）and optional second derivative（jerk）using the previous two limited commands and elapsed update period.
- **History/timing semantics:** `diff_drive_controller` initializes the two-command history with zero commands during reset, then updates the history every successful command-limiting cycle. Acceleration/deceleration behavior therefore depends on a positive, representative controller update `period`; update-loop stalls or abnormal timing must be covered by integration evidence.
- **Limitations:** This is command shaping, not direct physical acceleration sensing or a certified safety function.
- **Access Date:** 2026-08-14

### 4.4 Exact 4.42.1 tests

- **Evidence Type:** Official tagged test source
- **Source:** [`test_diff_drive_controller.cpp` at tag 4.42.1](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/test/test_diff_drive_controller.cpp)
- **Exact Version / Revision:** `ros2_controllers` 4.42.1
- **Observed Scope:** `test_speed_limiter` configures distinct forward acceleration, forward deceleration, reverse acceleration and reverse deceleration values, then repeatedly advances the controller with a known `dt` and verifies the wheel commands follow the expected ramp to positive velocity, zero, negative velocity and zero. `test_open_loop_odometry_with_clamped_input` verifies configured maximum linear and angular velocities clamp oversized body commands.
- **Limitations:** Tests exercise controller command output, not this AMR's installed configuration or physical movement.
- **Access Date:** 2026-08-14

## 5. Parameter Semantics That Must Be Preserved

### Direction and asymmetry

The parameter names distinguish movement direction from whether speed magnitude is increasing or decreasing:

| Motion case | Parameter sign |
|---|---|
| Positive direction speeds up | `max_acceleration >= 0` |
| Positive direction slows toward zero | `max_deceleration <= 0` |
| Negative direction speeds up | `max_acceleration_reverse <= 0` |
| Negative direction slows toward zero | `max_deceleration_reverse >= 0` |

If reverse-specific values are omitted, the limiter can use symmetric counterparts. If operating behavior requires different forward/reverse or clockwise/counter-clockwise ramps, all direction-specific values should be configured explicitly and tested.

### Jerk is optional, not a SYS-028 requirement

The controller also supports `min_jerk` / `max_jerk`, but current SYS-028 only requires velocity, acceleration and deceleration limits. Jerk limiting may be configured later for smoother motion if operational evidence justifies it; it is not required for `Fully Covered`, and leaving jerk as `.NAN` does not create a requirement gap.

### Controller lifecycle and update loop

The limiter is executed inside the active controller update path. Configuration constructs the limiters from parameters; reset seeds their command history with zeros; activation requires the wheel interfaces; each update uses its supplied `period`. Therefore validation must not merely inspect YAML—it must show the controller is active, updates continue at the configured rate, the limited body command is produced, and downstream hardware follows it.

## 6. Downstream Wheel and Motor Values

`diff_drive_controller` converts the already-limited body command into wheel joint commands. `M1Hardware` later converts wheel rad/s into motor RPM according to gear ratio and signs. Those downstream values must remain compatible with hardware capability, but the current SYS-028 does not independently require wheel-domain or motor-domain clamps.

Consequently:

- wheel geometry, gearing and motor limits are downstream configuration/integration constraints;
- they must be checked when choosing feasible body operational limits;
- they do not create a SYS-028 Custom Behavior Gap;
- this assessment does not remove any clamp already required by a separate hardware design or requirement.

## 7. Gap Classification

### Mature Capability

`diff_drive_controller` 4.42.1 natively covers linear/angular velocity and corresponding acceleration/deceleration limiting. No custom body-motion limiter is needed.

### Configuration Gap

- Pin the installed `ros2_controllers` version on the target image.
- Configure finite `linear.x` and `angular.z` min/max velocity values.
- Configure finite forward/positive and reverse/negative acceleration/deceleration values, explicitly asymmetric where required.
- Optionally enable `publish_limited_velocity` to aid verification.
- Keep controller update rate/period within the validated deployment envelope.

### Composition Gap

`None` beyond the already-selected SYS-022 `diff_drive_controller` composition. A separate velocity smoother or custom limiter is not required by SYS-028.

### Custom Behavior Gap

`None`.

### Evidence Gap

- Verify parameter values actually loaded and limits are not `.NAN`.
- Exercise positive/negative linear and angular steps, acceleration, deceleration and direction reversal.
- Compare input command, `~/cmd_vel_out`, wheel command interfaces and controller update timing.
- On the physical AMR, measure achieved body linear/angular velocity and acceleration/deceleration under representative payload, floor, supply and communication conditions.
- Confirm chosen operational values remain feasible after wheel geometry and motor conversion.

## 8. Handoff to 04 Assessment

Recommended 04 conclusion:

- **Coverage Status:** `Fully Covered` at mature-solution capability level.
- **Candidate:** ROS 2 Jazzy `diff_drive_controller` / `ros2_controllers` 4.42.1.
- **Applicable conditions:** finite body velocity and acceleration/deceleration parameters; correct direction/sign semantics; active controller and valid update period.
- **Custom gap:** `None`.
- **Non-custom gaps:** operational value selection, exact installed-version/configuration evidence, update-loop integration and real-hardware body-motion evidence.
- **Optional feature:** jerk limiting is available but not required by current SYS-028.
- **MVP simplification:** none justified.

## 9. Search Boundary

The search covered the current exact SYS-028 wording and the exact official `ros2_controllers` 4.42.1 `diff_drive_controller` implementation, parameter definition, SpeedLimiter wrapper and tests, plus the first-party Jazzy `control_toolbox::RateLimiter` API. Wheel/motor-domain limiting, SYS-030/SYS-031 behavior and safety certification were not used as requirement fragments or as reasons to introduce custom behavior.
