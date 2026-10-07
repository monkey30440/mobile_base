# Perception component launch/config — 2026-10-07

Operator approved separate IMU/LiDAR launch/config within Perception. Spec32 and tickets36/37 were updated before runtime edits. This follows component verification phase ordering, without product Bringup or physical-device actions.

`imu.launch.py` requires an explicit native ROS parameter YAML. `dual_picoscan.launch.py` optionally loads a flat `lidar_config` YAML; CLI arguments take precedence and the existing all-CLI workflow remains supported. Missing selected files fail launch, unknown LiDAR setting keys are rejected, and required network facts remain explicit. No implicit hardware profile selection occurs. Both config files are installed alongside their launch entries. IMU decoder, diagnostics, mounting ownership and native SICK responsibilities remain unchanged.

`config/imu.yaml` contains recorded commissioning transport/guide conversions and Operator axis choice, unknown gyro covariance and the existing0.3s commissioning timeout; firmware identity, independent unit/axis verification and calibration remain incomplete. `config/lidar.yaml` records the confirmed sensor IPs and observed host/port configuration, native LAST/mode1. Profiles disclose applicability and existing shutdown/timing limitations. These are explicit examples, not calibrated production acceptance.

## Verification

ARM64 image SHA256307cf16d1581c1078d21e67c1d8c9aab21eeca61641e1c9a23b90c34d0b83e46. Isolated network-none container, no physical device mappings, read-only source; fresh build/install prefix `/tmp/entry`. Description dependency and Perception build succeeded; both installed config files were present. Python syntax/XML and diff checks passed.

At the agreed installed-launch/public ROS seam, IMU sample-conversion test failed before the entry existed, then passed after implementation. LiDAR YAML/CLI-override test failed before support existed, then passed with real native driver publishers, SensorDataQoS and public parameter readback. These are pseudo-terminal/passive-loopback fixtures, not actual sensors.

First full20-case run had one native parameter-service readiness assertion failure on the original all-CLI case. No driver/log root cause was established and no runtime fix was inferred. The seven public-entry cases passed on follow-up; final full Perception suite passed **20 tests,0 errors,0 failures,0 skipped**. Preserve the initial intermittent readiness result rather than claiming it diagnosed or hardware-relevant. New cases cover missing selected files and actual IMU conversion as well as config/CLI compatibility.

[Raw TDD XML, first failure, follow-up/final results, build/test logs and source hashes](artifacts/perception-component-entries-20261007.tar.gz).

Two-axis review with retained user-approved basis f591f4e, scoped against70bd2a4: Standards0 actionable findings; Spec0 actionable findings. No actual IMU/LiDAR startup, motor commands, hardware/calibration acceptance or issue closure occurred.
