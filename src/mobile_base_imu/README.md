# USB IMU adapter (#36)

This independent V1 adapter implements the HandBoard V1 wire facts documented in
`reference/tdk_ros2_imu/HandBoard_IMU_V1_Quick_Guide.md`: 59 bytes, AA55,
14 little-endian float32 values, XOR over bytes 0–57. It consumes acceleration
indices 0–2 and angular velocity indices 5–7. It rejects wrong header/checksum
and all nonfinite packet values. Arbitrary read chunks are resynchronized with
at most 58 residual bytes after each poll; each read is bounded to 4096 bytes.
No reference implementation is imported. Its prior validation is not evidence
for this adapter. Bridge-derived angles are unused; there is no fusion or TF.

## Configuration and operation

All transport/conversion/timeout facts must be supplied explicitly. No physical
serial path, baud, firmware profile, scales, installation axes or sample timeout
is selected by a runtime default. Missing/invalid configuration produces ERROR
on `/diagnostics`, opens no port and publishes no measurements.

| Parameter | Meaning |
|---|---|
| `port` | Actual accessible stable USB serial path (user identified `/dev/fihRobotBaseIMU`; mapping into container remains operator setup) |
| `baud` | Explicit supported POSIX serial baud; guide example is 115200, target must be verified |
| `protocol_profile` | `handboard_v1` only after confirming target firmware matches the guide |
| `acceleration_scale` | Positive finite m/s² per wire unit; guide describes g using 9.81 |
| `gyro_scale` | Positive finite rad/s per wire unit; guide describes deg/s |
| `axes` | Right-handed signed permutation: each ROS output axis selects signed device axis 1/2/3. General non-axis-aligned mounting must be corrected in hardware/frame design, not approximated here |
| `sample_timeout` | Positive finite seconds since last valid measurement; choose from actual stream/consumer requirements |

Output `imu/data_raw` is `sensor_msgs/Imu` with `base_imu_link`. Timestamp is the
ROS host receipt time; no sensor acquisition timestamp exists in this packet,
and latency/synchronization are unverified. Orientation covariance starts with
-1 (unavailable); acceleration/angular velocity covariances are all zero,
the ROS convention for unknown covariance. They are not calibrated noise values.
Do not configure estimation as if calibrated covariance or orientation exists.

Native `diagnostic_updater` identifies port/profile, invalid packets, valid
sample count, sample age, time/covariance limitations and configuration,
communication, packet/data and valid-sample timeout errors. A later valid sample
recovers packet/data status; counters retain evidence. Disconnection/open failure
requires fixing the cause and restarting the node. There is no implicit fallback
port, retry policy or cached measurement publication. “Valid bridge samples” only
means the configured decoder accepts samples, not hardware health/calibration.

## Software fixture evidence

Build/test inside the development container with system Jazzy Python:

```bash
colcon build --packages-select mobile_base_imu --symlink-install
colcon test --packages-select mobile_base_imu
colcon test-result --verbose
```

Tests use literal documented packet examples and Linux pseudo terminals. They
exercise real ROS topics and native diagnostics, including invalid sample
suppression, timeout and stream disconnection. Fixture values 115200, 9.81,
pi/180, identity axes, 0.25 seconds are controlled examples, not accepted target
configuration. They access no physical serial port.

Hardware validation remains required: confirm firmware/protocol/baud, observe
stationary gravity and controlled rotations against installation axes, verify
rate/latency/clock behavior and reconnect/error conditions. Calibrate bias,
noise/covariance and mounting before accepting estimation performance. Actual
firmware, scale and axis evidence are unresolved. Unknown covariance is explicitly
reported rather than invented. No hardware acceptance or Feature Freeze claim.
