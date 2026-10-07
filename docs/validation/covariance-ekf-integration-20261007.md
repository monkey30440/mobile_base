# Covariance / native EKF software integration — 2026-10-07

Operator adopted optional calibrated gyro covariance at the existing IMU adapter boundary. This delivers that scoped capability plus partial #38 native estimation wiring. It is not production calibration, an accepted physical model or complete #38 acceptance.

Commits tested: `11188f7` (native launch/workflow), `9f4b933` (adopted responsibility), `ff900a0` (IMU publisher configuration). Testing used production-check image SHA256 `307cf16d1581c1078d21e67c1d8c9aab21eeca61641e1c9a23b90c34d0b83e46`, isolated ROS domain 165, `--network none` and no mapped devices.

IMU publication and configuration RED/GREEN evidence is in `imu-angular-covariance-20261007.md`. The EKF workflow first failed with the launch process exiting because the entrypoint did not exist. Adding the native-only launch enables the controlled data chain. The bounded test waits for synthetic estimates to converge; it checks filtered linear speed 0.2 m/s and yaw rate 0.5 rad/s within fixture tolerances, nonzero translated/rotated pose, model/odom TF connectivity and odom-transform shutdown with EKF while RSP remains alive. Those inputs and tolerances are software fixture values, not calibration or product acceptance thresholds.

The IMU and EKF boundaries are tested separately: IMU ROS/PTY tests verify configured covariance in emitted messages; the native EKF workflow supplies synthetic standard IMU/odometry messages directly. No physical adapter-to-EKF accuracy claim is made. Native RSP advertises `/tf` even when publishing no moving joints; the test observes the specific odom edge and its cessation after EKF stops rather than equating topic publisher count with transform ownership.

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select mobile_base_imu mobile_base_bringup
source install/setup.bash
colcon test --packages-select mobile_base_imu mobile_base_bringup --event-handlers console_direct+
colcon test-result --test-result-base build/mobile_base_imu --verbose
colcon test-result --test-result-base build/mobile_base_bringup --verbose
```

Both affected packages built. Their fresh results are **13 IMU tests + 10 Bringup tests = 23 tests, 0 errors, 0 failures, 0 skipped**. The unrestricted workspace result count of 48 includes retained results from unchanged packages, so it is not reported as 48 newly executed tests. The host-local build/test log is `/tmp/v1-covariance-ekf-full.log` and may be lost after restart; tracked tests and this interpretation are durable.

Unknown gyro covariance still publishes ROS zeros when not supplied. Actual fusion must not select that measurement until validated positive SI variance is available. No deployment profile, real variance, gyro bias correction, acceleration fusion, duplicate RSP, automatic calibration or new estimator is introduced. Physical yaw signs/scales, wheel displacement, production tuning/timing, LiDAR scan transforms and full Bringup ownership remain pending. #35/#36/#38 remain open.

## Two-axis review

Operator selected comparison baseline `f591f4e`; independent Standards and Spec reviewers inspected `f591f4e...cfbd510`. Standards found no documented violation or concrete bug, with one nonblocking P3 maintainability judgement: bounded driver/observer spin loops are repeated in the new public IMU tests. A small shared helper is optional; no broader fixture refactor was introduced for this scoped delivery. Spec found no actionable deviation or runtime scope creep and confirmed the explicit partial-acceptance boundaries. Reviewers did not rerun tests or access hardware.
