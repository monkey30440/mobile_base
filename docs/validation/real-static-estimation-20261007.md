# Real static wheel / IMU / EKF integration — 2026-10-07

Source5ca566b, specification32 and tickets35/36/38. Operator adopted a temporary
commissioning uncertainty configuration for real data-chain and TF ownership
checks only. AMR remained on ground. No velocity publisher or movement command
was introduced. Native M1 lifecycle activated at zero command, then deactivated.
No runtime source or formal target profile was changed.

## Result: PARTIAL

The final15s observation received302 native wheel odometry messages,2601 real IMU
messages and296 native filtered odometry messages. Source diagnostics and freshness
checks passed, wheel velocities stayed within the stationary guard, and filtered
pose/twist/covariance were finite with normalized orientation. Frame IDs were
odom/base_footprint and base_imu_link. Native EKF subscribed to both real sources;
lookup from odom to base_link, IMU and both native LiDAR scan frames succeeded.
This does not verify dynamic axes, displacement accuracy or calibrated covariance.

The actual native controller parameter enable_odom_tf was false. Native RSP was
the only static TF publisher, its actual model contained no odom frame, and native
EKF was the only filtered-output publisher. All three nodes advertised /tf:
RSP, base_controller and EKF. Native controller4.42.1 creates its TF publisher
unconditionally but gates publication with enable_odom_tf; a software-only PTY
reproduction confirmed that distinction. After stopping only EKF, the odom to
base_footprint edge ceased while source health, stationarity and model static
TF remained available. Ownership attribution uses the native graph and controlled
shutdown, not per-message publisher GID: this installed rclpy MessageInfo dictionary
has timestamps and sequence numbers, but no publisher_gid field.

## Confirmed wheel TF gap; position scale UNRESOLVED

Actual JointState contains both correct wheel names and finite zero velocity, but
position=[NaN,NaN]. Current M1 adapter exposes velocity state only. Installed native
joint_state_broadcaster4.42.1 initializes missing position to NaN; native RSP then
produces invalid transforms for driving_wheel_link_L/R, which tf2 rejects. Both
wheel transforms were observed invalid; no invalid transform outside these two
known children was observed. Complete model/TF acceptance is therefore NOT passed.

A minimal no-hardware replay of the actual captured JointState reproduced both
invalid wheel transforms. Replaying the same model with finite fixture positions
removed that failure, isolating missing position from model geometry. That fixture
was diagnostic-only and was never substituted into real hardware integration.
No additional TF publisher, fake wheel state or guessed conversion was added.

Manufacturer M1 communication manual Read Data5/6 current-position words were
successfully read while inhibited (right ID1 raw923840; left ID2 raw-1045392),
with checked response framing/CRC and final stopped status. These are raw counters,
not radians. Saved01-06=2500 specifies single-phase encoder pulses per revolution;
it does not establish the current-position counter's counts per motor revolution.
Operator confirms the scale unknown and offers a later raised test. That test has
not occurred. A verified scale and applicable real position interface are required
before accepting rotating-wheel TF; tickets remain open and blockers remain.

## Commissioning uncertainty and limitations

Only temporary launch/config copies were used. Native wheel pose/twist diagonals
used the documented initial values[.001,.001,.001,.001,.001,.01]. IMU angular
variance inputs were the prior stationary observation's second moments about zero
[4.576113064e-7,9.063136026e-8,2.738478209e-7](rad/s)^2, retaining observed mean
contribution without bias correction. These are not calibrated covariance or bounds
on unmeasured drift, thermal, scale or timing errors. EKF fused wheel linear X/Y
velocity and IMU yaw rate only; no orientation or acceleration fusion. The last
filtered yaw was about-0.00635rad and yaw rate-0.000389rad/s despite stationary
wheels, consistent with the unresolved stationary IMU bias limitation. No accuracy
acceptance is inferred from finite output.

Attempts1/2 failed observer assumptions about MessageInfo, and attempt3 failed an
incorrect two-endpoint graph expectation. Their exact scripts/logs and cleanup
readbacks are preserved. Software-only API/source/graph checks corrected those
observer assumptions before the final attempt; they were not hardware fixes.
Final attempt exited1 intentionally for PARTIAL, not an unhandled test failure.
Native deactivation returned0. Independent final FC03 readback confirmed both
drives inhibited(status6), alarm0, currentRPM0 and targetRPM0. The dedicated
static container was removed; existing development/view containers were retained.

[Evidence archive](artifacts/real-static-estimation-20261007.tar.gz) includes
attempt-separated scripts/logs, actual ROS traces, temporary configs/model,
read-only transactions, software reproductions and SHA256 manifest. Historical
pre-adoption notes are explicitly superseded by checkpoint.md. These harnesses
are evidence, not a production launch or instructions for unattended motion.

Primary sources: exact [native broadcaster4.42.1 source](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/joint_state_broadcaster/src/joint_state_broadcaster.cpp)
and [native controller4.42.1 source](https://github.com/ros-controls/ros2_controllers/blob/4.42.1/diff_drive_controller/src/diff_drive_controller.cpp).
Local manufacturer references: reference/M1-COMM_UM-01-S0686.pdf, current-position
Read Data5/6; reference/M1-UserManual_UM-01-S0701.pdf, encoder parameter01-06.
