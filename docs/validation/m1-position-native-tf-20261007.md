# Native M1 position and nominal drive-seat TF — 2026-10-07

Specification [32](https://github.com/monkey30440/mobile_base/issues/32), decisions
[22](https://github.com/monkey30440/mobile_base/issues/22#issuecomment-6032477947),
tickets35/38. Operator adopted nominal drive-seat posture before model changes.
This follow-up supersedes the earlier missing-position and disconnected-drive-seat
findings; historical raw results remain unchanged.

## Result and scope

Software M1 checks:31 ROS public-workflow cases and4 C++ protocol cases pass
(colcon reports37 including2 CTest wrappers). Description checks pass
(1 pytest plus its CTest wrapper). Red/Green checks covered missing finite wheel
position, configuration mismatch reporting, and nominal fixed-seat geometry.
The initial all-package test invocation also encountered stale description/LiDAR
build caches; that invocation did not pass globally. Current description was
subsequently rebuilt and its scoped suite passed. No all-package claim is made.

Actual inhibited Read Data0–6 confirms the combined16-word response and both
per-drive checks. Runtime now exposes real wheel position with explicit mode0
10000steps/motor revolution and2500single-phase encoder pulses. Before activation,
actual02-14 and01-06 are read and compared; parameters are not written. Native
velocity-feedback odometry remains unchanged. Bad position residual or implausible
jump invalidates feedback and latches a fault until deliberate reconfiguration;
there is no automatic restart on a later valid packet. Software checks include
pulse carry, signed Index rollover, invalid data, and explicit recovery.

Phase1 actual stationary integration was PARTIAL: finite measured wheel angles
and local wheel TF were available, but unmeasured prismatic drive-seat joints
broke base-to-wheel paths. After Operator adoption and spec reconciliation, only
those two deployment joints became fixed at the source URDF zero-displacement
origins. Original source URDF, real continuous wheel joints and other passive
joints remain unchanged. No fabricated JointState or custom TF publisher is added.

Phase2 actual15s stationary integration PASS within this scope:300 wheel odometry,
2587 IMU and300 filtered messages; finite wheel TF, both base_footprint-to-drive-wheel
paths and base/sensor estimation paths available. Native robot_state_publisher
owns model TF; robot_localization owns odom→base_footprint. Controller odom TF is
disabled. Stopping only EKF stops that edge while source health remains valid.
No velocity command was published. Initial and independent final readbacks show
both drives status6 (inhibited), alarm0, current RPM0 and target RPM0.

## Limits and remaining acceptance

Wheel-seat posture is nominal, not measured suspension travel. Encoder origin
is not calibrated mechanical wheel phase. Other unmeasured passive branches are
not accepted by this result. Formal covariance, displacement calibration,
dynamic IMU validation, physical counter/reset behavior, production settings and
AGX Orin compatibility remain open. Temporary commissioning uncertainty is used
only for this static check. This does not complete35/38 or remove dependencies.
Operator Foxglove acceptance of the new integrated wheel/model chain remains to
be performed; earlier sensor-frame acceptance is not reused as wheel acceptance.

Native fixed joints are published statically; movable joints need JointState:
[robot_state_publisher3.3.4](https://github.com/ros/robot_state_publisher/blob/3.3.4/README.md).

[Evidence archive](artifacts/m1-position-native-tf-20261007.tar.gz) includes executed
scripts/configurations/models, phase1 retained separately, phase2 outputs, raw
ROS events, readbacks, software logs and SHA256 manifest. Failed intermediate
harness/assertion attempts are retained separately from final passing checks.
