> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-022 Base Motion Control — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的下列定案需求，不修改或擴張需求：

> **SYS-022 底盤運動控制**：系統應接收底盤速度命令，並依差速輪運動學控制底盤完成移動。

研究問題是：ROS 2 Jazzy 的 `ros2_control` + `diff_drive_controller` 是否已提供接收 vehicle velocity command、執行 differential-drive kinematics、輸出左右輪命令所需的成熟能力；同時區分 controller capability、hardware interface dependency、configuration/evidence gap 與 custom behavior gap。

Wheel odometry 與 TF publication 只作為候選套件的附帶能力記錄，不在此筆記重新分配 SYS-005 ownership。M1 drive hardware baseline 只作為使 wheel command 落到實體底盤的 downstream dependency，不作為 SYS-022 controller capability 的替代證據。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `ros2_control` + `diff_drive_controller` |
| Exact Version / Platform | ROS 2 Jazzy；Ubuntu 24.04 Noble；2026-08-13 Jazzy rosdistro metadata：`ros2_control` 4.47.0-1、`ros2_controllers`（含 `diff_drive_controller`）4.42.1-1 |
| Coverage Status | **Fully Covered**（成熟 controller capability 層級） |
| Covered Scope | 接收 stamped body velocity command；使用 `linear.x`、`angular.z` 與 wheel geometry 轉換為左右輪 velocity commands；經 ros2_control wheel velocity command interfaces 驅動差速底盤 |
| Known Constraints | 原生 topic input 是 `geometry_msgs/msg/TwistStamped`；需要正確 wheel joint names、wheel radius/separation 與有效 hardware velocity command interfaces；實體移動取決於 downstream hardware interface、drive readiness 與正確 feedback/configuration |
| Uncovered Gap | `None`（SYS-022 沒有已知 Custom Behavior Gap） |
| Missing Evidence | target image installed versions、controller configuration/activation、topic/remap/QoS、wheel interface export、geometry/sign/unit、M1 integration 與 real-hardware movement 尚未驗證 |
| MVP Change Candidate | `None` |

`Fully Covered` 只表示成熟方案已提供 SYS-022 的 controller behavior。它不表示本專案已完成 `diff_drive_controller` configuration、M1 ros2_control hardware interface，也不表示實體 AMR 已完成移動驗證。

## 3. Requirement Fragments

| Requirement fragment | Mature coverage | Remaining project dependency / evidence |
|---|---|---|
| 接收底盤速度命令 | `~/cmd_vel` 接收 `geometry_msgs/msg/TwistStamped`，使用 `linear.x` 與 `angular.z` | 上游訊息型別、topic/remap、QoS、timestamp 與 controller active-state integration |
| 依差速輪運動學控制 | `wheel_separation`、`wheel_radius` 與左右輪配置支援 body twist 到 wheel velocity 的 inverse kinematics | 實際 wheel geometry、joint mapping、方向、倍率及校正值 |
| 控制底盤完成移動 | controller 寫入左右 wheel joint 的 velocity command interfaces；`ros2_control` control loop 將 controller command 交給 hardware component | M1 hardware plugin 必須正確 export/consume interfaces，並由 integration 與 real-hardware evidence 證明底盤按命令移動 |

## 4. Primary-source Evidence

### 4.1 Exact Jazzy releases and target platform

- **Evidence Type:** Official release metadata
- **Source:** [ROS 2 Jazzy rosdistro distribution metadata](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml#L9809-L9898)
- **Exact Version / Revision:** `ros2_control` 4.47.0-1；`ros2_controllers` 4.42.1-1；metadata current on 2026-08-13
- **Target Platform:** ROS 2 Jazzy；Ubuntu Noble is a Jazzy release platform
- **Observed or Documented Scope:** `diff_drive_controller` is a released package in the Jazzy `ros2_controllers` repository; `ros2_control` and `ros2_controllers` are separately versioned release repositories.
- **Limitations:** Floating rosdistro metadata identifies the current Jazzy release, not the version installed in this project's target image. Deployment must separately pin and record installed binary versions.
- **Access Date:** 2026-08-13

### 4.2 Velocity-command input and differential-drive output

- **Evidence Type:** Official exact-distribution documentation
- **Source:** [Jazzy `diff_drive_controller` user documentation](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)
- **Exact Version / Revision:** ROS 2 Jazzy documentation; release family `ros2_controllers` 4.42.1-1 per current rosdistro metadata
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** The controller accepts robot-body velocity commands and translates them into differential-drive wheel commands. Its non-chained subscriber is `~/cmd_vel` with `geometry_msgs/msg/TwistStamped`; only `linear.x` and `angular.z` are used. `wheel_separation` and `wheel_radius` define the body-to-wheel transformation, and the outputs are wheel-joint `HW_IF_VELOCITY` command interfaces.
- **Limitations:** The controller does not determine project wheel geometry, joint names, motor sign, gearing, encoder semantics, device protocol, or hardware readiness. A bare `geometry_msgs/msg/Twist` is not documented as this Jazzy controller's direct subscriber type.
- **Access Date:** 2026-08-13

### 4.3 Differential-drive kinematics

- **Evidence Type:** Official exact-distribution documentation
- **Source:** [Jazzy wheeled mobile robot kinematics](https://control.ros.org/jazzy/doc/ros2_controllers/doc/mobile_robot_kinematics.html)
- **Exact Version / Revision:** ROS 2 Jazzy `ros2_controllers` documentation
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** For wheel separation `w`, the documented inverse kinematics are `v_left = v_bx - omega_bz*w/2` and `v_right = v_bx + omega_bz*w/2`; wheel radius then maps linear wheel speed to wheel rotation.
- **Limitations:** Formula availability does not prove that the configured geometry, units, wheel direction, transmission ratio or actual AMR motion is correct.
- **Access Date:** 2026-08-13

### 4.4 ros2_control hardware boundary

- **Evidence Type:** Official exact-distribution documentation
- **Source:** [ROS 2 Jazzy ros2_control getting started](https://control.ros.org/jazzy/doc/getting_started/getting_started.html)；[Jazzy `diff_drive_controller` interface description](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html#description-of-controller-s-interfaces)
- **Exact Version / Revision:** ROS 2 Jazzy documentation; `ros2_control` 4.47.0-1 and `ros2_controllers` 4.42.1-1 per current rosdistro metadata
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** During the control loop, controllers read hardware state and write hardware command interfaces. `diff_drive_controller` requires velocity command interfaces for the configured wheel joints. For feedback it uses wheel position state interfaces by default, or wheel velocity state interfaces when `position_feedback=false`; with `open_loop=true` it does not claim external state interfaces for odometry.
- **Limitations:** This defines the standard boundary but does not implement or verify the project-specific M1 protocol/hardware plugin. Position state or velocity state is feedback; the controller still commands wheel **velocity**, not wheel position.
- **Access Date:** 2026-08-13

### 4.5 Odometry and TF are adjacent capabilities, not SYS-022 ownership evidence

- **Evidence Type:** Official exact-distribution documentation
- **Source:** [Jazzy `diff_drive_controller` ROS 2 interfaces and parameters](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html#ros-2-interfaces)
- **Exact Version / Revision:** ROS 2 Jazzy documentation; release family `ros2_controllers` 4.42.1-1 per current rosdistro metadata
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** The controller can compute `~/odom` from hardware feedback and can publish `/tf` when `enable_odom_tf=true`; it can instead use commanded velocity for odometry when `open_loop=true`.
- **Limitations:** These features do not change SYS-022 coverage. In this project, system-level odometry and authoritative `odom -> base_footprint` ownership remain SYS-005 concerns. Configuration must avoid duplicate TF publishers, and measured wheel feedback must not be replaced by command-derived evidence when closed-loop state is required.
- **Access Date:** 2026-08-13

## 5. Local Read-only Evidence

The current local reference `ref/base_motor_controller` is at commit `f05d8cbb43a812e39c0b038c56baee8ada699b2c`.

Read-only inspection found:

- the legacy Python `DiffDriveController.body_to_wheel_rpm()` implements the same standard differential-drive relationship using wheel base and wheel radius;
- it additionally converts wheel RPM to motor RPM and applies project-specific gearing, signs, motor RPM clamping and minimum-effective-RPM behavior;
- the implementation plan records migration toward `diff_drive_controller` for differential kinematics and a separate ros2_control hardware interface for the M1 device boundary.

This local code is a protocol/behavior reference, not evidence that Jazzy `diff_drive_controller` is configured or running. Its motor-side gearing, signs, clamping and minimum-effective-RPM semantics must be allocated to configuration, the hardware boundary, SYS-028 assessment or later design as appropriate; they are not evidence of a SYS-022 custom kinematics gap.

No installed target-image `ros2_control`/`diff_drive_controller` package query, controller runtime interface inspection, integration test or real-hardware motion result was available in this research step.

## 6. Gap Classification

### Controller Capability

The mature controller covers all three SYS-022 fragments: stamped body velocity input, differential-drive inverse kinematics, and wheel velocity command output. No custom motion-control algorithm is required for SYS-022.

### Hardware Interface Dependency

`diff_drive_controller` stops at standard ros2_control wheel interfaces. Actual AMR movement requires a downstream hardware component that:

- exports the configured left/right wheel velocity command interfaces;
- exports valid position or velocity state interfaces when closed-loop feedback is configured;
- converts standard wheel units and directions to the M1 protocol without changing the controller contract;
- writes commands and reads feedback successfully while the drive is operational.

The approved M1 hardware baseline is relevant evidence for that dependency, but it is not controller coverage and is not re-assessed here.

### Configuration Gap

- Pin the installed `ros2_control` and `diff_drive_controller` package versions on the target image.
- Configure left/right wheel joint names, wheel radius, wheel separation and any justified correction multipliers.
- Standardize the command chain on `TwistStamped`, or explicitly own a `Twist -> TwistStamped` adapter if a retained producer cannot publish the stamped type.
- Configure topic/remap, namespace, QoS, controller manager update rate, feedback mode and controller lifecycle activation.
- Keep `enable_odom_tf=false` if another component is the authoritative `odom -> base_footprint` publisher.

### Evidence Gap

- Build/installation: exact target-image packages and plugin discovery.
- Runtime interface: controller active; correct command/state interfaces claimed; intended `TwistStamped` messages received.
- Integration: finite body commands produce expected signed wheel commands; zero command produces zero wheel velocity; joint/unit/frame contracts are consistent.
- Real hardware: forward, reverse and rotation commands move the physical AMR in the expected direction and scale under the approved operating conditions.
- SYS-027 timeout, SYS-028 limits, SYS-026/SYS-030 fault/readiness and SYS-031 shutdown behavior require their own requirement-level assessments; package features noted here do not close them through SYS-022.

### Custom Behavior Gap

`None` for SYS-022. Project-specific M1 device communication is a required hardware interface dependency, not a reason to replace the mature differential-drive controller.

## 7. Handoff to 04 Assessment

Recommended 04 conclusion:

- **Coverage Status:** `Fully Covered` at mature-solution capability level.
- **Candidate composition:** ROS 2 Jazzy `ros2_control` 4.47.0-1 + `diff_drive_controller` / `ros2_controllers` 4.42.1-1.
- **Applicable conditions:** `TwistStamped` command contract; correct wheel geometry/joint configuration; functioning wheel velocity hardware command interfaces; downstream M1 hardware integration.
- **Custom gap:** `None` for SYS-022.
- **Non-custom gaps:** exact installed-version pinning, project configuration, hardware-interface dependency, integration evidence and real-hardware evidence.
- **Architecture consideration:** 05 may decide composition and ownership, but should preserve the standard controller/hardware boundary and must not assign system-odometry TF ownership through this SYS-022 assessment.
- **MVP simplification:** none justified.

## 8. Search Boundary

The candidate search covered the official ROS 2 Jazzy `ros2_control` controller family, the official differential-drive controller/kinematics documentation, current Jazzy release metadata, and the project-designated local motor-controller reference. Because `diff_drive_controller` directly and completely covers the required controller behavior through standard ros2_control interfaces, no second generic controller candidate or custom algorithm was introduced.
