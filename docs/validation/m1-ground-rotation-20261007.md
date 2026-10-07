# M1 initial ground rotation — 2026-10-07

Ticket35; runtime source9658979, no production code or drive parameter change.
Operator confirmed landed AMR, clear rotation envelope, onsite observation and
ability to use the known hardware stop. Trials were sequential; each was stopped,
deactivated, independently read back, and physically confirmed before the next.

| Trial | Nonzero commands | Duration to explicit zero | Nominal command integral | Wheel-feedback odometry yaw delta | Operator observation |
| --- | ---: | ---: | ---: | ---: | --- |
| Left short | 17 | 1.700620s | +9.7438° | +9.6137° | Approximately10° left, stopped |
| Left longer | 52 | 5.199954s | +29.7935° | +29.4554° | Visually approximately30° left, stopped |
| Right longer | 52 | 5.200264s | −29.7953° | −29.5375° | Visually approximately30° right, stopped |

Each uses pure yaw ±0.10rad/s with zero commanded linear velocity, nominal
radius0.08m/separation0.555m/gear20:1 and the bounded150motorRPM commissioning
profile. Initial exclusive FC03 guards require alarm-free zero current/targetRPM.
The separate network-none/domain213 temporary container maps only the motor USB
serial device with GID20. Native controller owns kinematics/odometry/limits;
enable_odom_tf remains false. No IMU or EKF was started by this test.

Reviewed temporary publishers bound the command interval, check observer abort,
and send explicit zero in finally followed by0.7s settling. Native observation
requires actual150RPM caps, linear limit0.03 and angular limit0.10, source-specific
fresh healthy statuses and finite complete two-wheel feedback within0.6rad/s.
Left-turn feedback is left-negative/right-positive; right-turn signs reverse.
The gate confirms movement occurred with expected signs and native pure yaw,
not uninterrupted speed regulation. Post-zero new feedback is near zero, native
deactivation succeeds and each final independent CRC/prefix-checked FC03 reports
IDs1/2 inhibited6, alarm0, currentRPM0, targetRPM0. All three temporary motor
containers were removed. Shutdown is separate from the operator's physical stop
observation; this does not isolate command-timeout or bus-loss stopping.

Odometry yaw deltas are calculated from the first and last native odometry
quaternion in each complete trace with wrapped yaw subtraction. They are dependent
wheel-feedback estimates using nominal geometry, not external angle measurements.
The signed command integral uses recorded first nonzero-to-explicit-zero duration;
it is not physical angle or a hard real-time duration guarantee. Only Operator
approximate visual angles are available. These support ground rotation direction,
approximate behavior and observed stopping, not effective wheel separation,
precise yaw accuracy, calibrated displacement, IMU alignment or EKF performance.
Straight-ground displacement and the remaining ticket acceptance stay open.

[Raw evidence](artifacts/m1-ground-rotation-20261007.tar.gz) contains separate cases,
exact temporary scripts/profile/model, native launch/build logs, public ROS traces,
command timing, initial/final FC03 bytes, summaries and SHA256 manifests. Archived
scripts are supervised commissioning evidence, not unattended execution guidance.
