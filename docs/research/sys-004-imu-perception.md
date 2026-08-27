> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-004 IMU Perception Reuse Assessment Research

## Scope

- Requirement: `SYS-004` — 系統應提供 IMU 量測資料供定位使用。
- Primary candidate: local `tdk_ros2_imu` package.
- Assessment date: 2026-08-13.
- This note assesses reusable capability only. It does not prove downstream localization integration.

## Candidate Identity

| Field | Value |
|---|---|
| Package | `tdk_ros2_imu` |
| Package version | `0.1.0` |
| Inspected repository revision | `f05d8cbb43a812e39c0b038c56baee8ada699b2c` |
| Sensor | HandBoard IMU V1 using TDK IIM-42652 |
| ROS interface | `sensor_msgs/msg/Imu` on `/tdk/imu` |
| Transport | USB serial, default `/dev/ttyACM0`, 115200 baud, 59-byte binary packet |

The package identity and dependencies are declared in [`package.xml`](../../ref/tdk_ros2_imu/package.xml). The package version is independent from the inspected repository revision.

## Source-supported Capability

- The node publishes `sensor_msgs/msg/Imu` with sensor-data QoS and a configurable `frame_id`; it uses ROS clock time when publishing each decoded sample. See [`tdk_imu_node.py`](../../ref/tdk_ros2_imu/tdk_ros2_imu/tdk_imu_node.py).
- Linear acceleration is converted from g to m/s², angular velocity from degrees/s to rad/s, and fusion RPY from degrees to a quaternion. See [`conversions.py`](../../ref/tdk_ros2_imu/tdk_ros2_imu/conversions.py).
- The stream parser validates the two-byte header, fixed packet length and XOR checksum; corrupt packets are discarded, while serial open/read failures stop the node with a fatal error. See [`protocol.py`](../../ref/tdk_ros2_imu/tdk_ros2_imu/protocol.py) and [`tdk_imu_node.py`](../../ref/tdk_ros2_imu/tdk_ros2_imu/tdk_imu_node.py).
- The device guide says output begins after about two seconds of power-on calibration, defines the physical X/Y/Z axes, and warns that orientation is relative to the power-on pose and yaw drifts because the sensor has no magnetometer. See [`HandBoard_IMU_V1_Quick_Guide.md`](../../ref/tdk_ros2_imu/HandBoard_IMU_V1_Quick_Guide.md) and the package [`README.md`](../../ref/tdk_ros2_imu/README.md).

The ROS 2 Jazzy `sensor_msgs/msg/Imu` definition requires acceleration in m/s² and rotational velocity in rad/s. It also defines an all-zero covariance matrix as "covariance unknown" and `-1` in the first covariance element as "estimate unavailable." The inspected node leaves all three covariance matrices at their default zeros; therefore it publishes values with unknown covariance, not a calibrated uncertainty model. [ROS 2 Jazzy `Imu.msg`](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/Imu.msg)

## Evidence Boundary

The user has confirmed that this package was validated and can be applied directly. This is accepted as project evidence for package reuse, but the current conversation does not identify the test record, target image, hardware conditions, duration, or exact behaviors observed. Source inspection independently proves the implementation described above; it does not expand the user's validation claim into localization integration or field-performance proof.

## Constraints and Missing Evidence

- **Timestamp:** the message uses host ROS publish/decode time, not a device-provided acquisition timestamp. Timing error and jitter have not been characterized.
- **Axes and frame:** the driver preserves device axes. Physical mounting must align them with the configured frame or provide the correct TF; this has not been verified here.
- **Covariance:** all covariance matrices remain zero, which ROS interprets as unknown. Localization configuration must supply/handle measurement uncertainty deliberately.
- **Calibration:** the guide describes power-on calibration, but this assessment has no calibration-quality, bias, noise, temperature-drift or repeatability evidence.
- **Orientation validity:** fusion orientation is power-on-relative and yaw is not an absolute heading. Whether localization should consume orientation, angular velocity, acceleration, or a subset remains an architecture/configuration decision.
- **Validity and diagnostics:** checksum errors produce throttled warnings and serial failures are fatal, but there is no separate measurement-validity or diagnostic status interface.
- **Integration:** topic remapping, QoS compatibility, TF consistency, localization configuration, failure propagation and real-hardware localization contribution remain unverified.
- **Exact ROS platform:** `package.xml` does not pin ROS 2 Jazzy or exact dependency versions. Compatibility with the target Jazzy image remains part of implementation/integration evidence unless covered by the user's existing validation record.

## Assessment Recommendation

| Field | Recommendation |
|---|---|
| Coverage Status | `Fully Covered` at reusable-capability level |
| Covered Scope | Provides standard IMU acceleration, angular velocity and power-on-relative fusion orientation measurements that can be supplied to localization |
| Custom Behavior Gap | `None` for SYS-004 as written |
| Non-custom Gaps | Configuration, timing characterization, covariance policy, frame/axis verification, diagnostics policy and localization integration evidence |
| MVP Change Candidate | `None` |

The candidate satisfies the narrowly written SYS-004 capability without new custom behavior. The remaining items are constraints, configuration choices and verification obligations for Architecture/Subsystem/Implementation; they must not be treated as evidence that downstream localization already works.
