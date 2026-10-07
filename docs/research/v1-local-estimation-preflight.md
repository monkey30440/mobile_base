# V1 local estimation preflight: IMU uncertainty

Research date: 2026-10-07. Scope: #38 prerequisites, specifically angular-velocity covariance. No device access, runtime changes, or calibration performed.

## Confirmed evidence

- An isolated `docker run --rm --network none --entrypoint dpkg-query mobile-base-v1-production-check:jazzy -W ros-jazzy-robot-localization` reported `3.8.3-1noble.20260902.170723`. No devices or workspace were mapped. Research below pins upstream tag **3.8.3**.
- ROS `sensor_msgs/Imu` specifies SI acceleration and angular velocity units. All-zero covariance means uncertainty is unknown; first element `-1` means that measurement is unavailable. These are different contracts. [Jazzy message definition](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/Imu.msg)
- Current `mobile_base_imu` emits unavailable orientation and unknown angular-velocity/acceleration covariance. See `src/mobile_base_imu/mobile_base_imu/node.py` and its README. User confirms mounting axes follow URDF; this does not establish measurement noise.
- Native `imuCallback` excludes angular velocity only for the unavailable sentinel. Otherwise it copies the supplied covariance into a twist measurement. An all-zero matrix therefore reaches fusion when angular velocity is selected. [3.8.3 callback](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/src/ros_filter.cpp#L561-L584)
- EKF correction raises selected variance below `1e-9` to that numerical floor. It does not derive a sensor uncertainty estimate. Zero input can thus produce extremely confident weighting despite ROS unknown semantics. The callback also emits a diagnostic for selected zero variance. [3.8.3 EKF correction](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/src/ekf.cpp#L126-L138), [covariance diagnostic](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/src/ros_filter.cpp#L2378-L2425)

## Native options and confirmed gap

Inspection of native IMU parameter declarations and documented parameters found no per-sensor replacement covariance parameter. Sensor selection, differential/relative modes, rejection thresholds and queue settings do not supply uncertainty. Process noise and initial estimate covariance describe different filter quantities; neither replaces incoming measurement covariance. [IMU declarations](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/src/ros_filter.cpp#L1421-L1637), [filter covariance parameters](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/src/ros_filter.cpp#L1745-L1752), [native documentation](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/doc/state_estimation_nodes.rst), [example configuration](https://github.com/cra-ros-pkg/robot_localization/blob/3.8.3/params/ekf.yaml)

For the selected native estimator, calibrated covariance must arrive in the input message. Disabling IMU fusion avoids unsupported weighting but does not meet the confirmed wheel-plus-IMU fusion responsibility. A generic external republisher would add another runtime owner without resolving calibration.

**Minimal custom responsibility, adopted by the operator on 2026-10-07:** extend the already necessary project-owned hardware IMU publisher with configuration for calibrated angular-velocity covariance in its published frame and SI units. Publish the configured covariance with the same sample; preserve unknown semantics when calibration is absent. Define validation and deployment requirements at that existing boundary. No separate covariance node, new estimator, bias estimator, or automatic calibration service is justified by this gap.

This note does not authorize choosing numerical covariance values. Native EKF process-noise tuning is also separate from estimating sensor measurement variance.

## Remaining evidence and integration boundaries

- **REQUIRES CALIBRATION:** gyro measurement covariance in `(rad/s)^2`, bias/noise versus deployment conditions, and estimator tuning/acceptance evidence. A stationary capture alone cannot establish dynamic scale accuracy, axis signs or time alignment.
- **REQUIRES HARDWARE VALIDATION:** gyro direction and scale during actual chassis rotation, timing assumptions, and fused wheel/IMU behavior. Raised wheel rotation does not rotate the chassis.
- **CONFIRMED scoped interface:** optional three positive angular-velocity variances in the published IMU frame and SI units; when omitted, all-zero unknown covariance is retained. Invalid supplied values fail before opening the device. Deployment fusion must not select an unknown-covariance measurement. No numerical deployment values are confirmed here.
- **CONFIRMED software-only path:** model/TF and native estimator wiring can be exercised using explicitly synthetic, nondeployment test measurements with declared fixture covariance. Passing that test must not be presented as hardware calibration or #35/#36 acceptance.

Native-first result: keep `robot_localization` as estimator and sole odometry TF publisher. The identified gap concerns upstream input quality at the existing IMU adapter, not estimator ownership.
