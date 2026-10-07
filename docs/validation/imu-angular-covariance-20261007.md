# Optional IMU gyro covariance — software evidence, 2026-10-07

Based on integrationf591f4e, isolated branch `fix/imu-angular-covariance`. Scope is existing IMU adapter/node, public ROS/PTY tests and documentation only. No hardware access, real calibration values, estimator, republisher or acceleration changes.

`angular_velocity_variances` uses the runtime-supported ROS DOUBLE_ARRAY, default `[0.0,0.0,0.0]` (unknown). Exactly three finite positive values configure diagonal covariance in published `base_imu_link` x/y/z SI axes, `(rad/s)^2`; all zeros retain unknown. Already-converted axes/units are intentional: supplied variances are not remapped or scaled again. Diagnostics distinguish supplied/unknown/invalid configuration while never claiming calibration. Orientation remains unavailable and acceleration covariance unknown.

Publication RED observed zeros instead of the independently expected synthetic diagonal. The GREEN public test uses nonidentity axes and verifies diagonal0/4/8, zero off-diagonals, unchanged orientation/acceleration semantics and supplied-covariance diagnostics. A packet fixture gyro-offset error was corrected to the documented slots5..7; it was unrelated to covariance behavior.

Validation RED observed modified PTY line attributes for mixedzero, negative, NaN, infinity and wrong-length vectors. GREEN rejects all five before serial open, reports the public configuration diagnostic and leaves PTY attributes unchanged with no samples. Existing default-unknown, packet validity, timeout/disconnection and baud0 cases remain passing.

Production-check image `mobile-base-v1-production-check:jazzy` was used without device mapping. Commands: build `mobile_base_imu`, source install, `colcon test --packages-select mobile_base_imu --event-handlers console_direct+`, `colcon test-result --verbose`. Result:13 pytest cases (5 packet +8 public ROS),0 errors/failures/skips. Root owns separate native EKF workflow verification and final combined regression.

Synthetic test variances are not deployment values. Actual covariance calibration, bias, physical scales/axes, acquisition timing and fusion acceptance remain unvalidated; this software option does not accept them.
