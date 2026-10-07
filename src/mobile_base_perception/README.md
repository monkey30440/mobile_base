# mobile_base_perception

Owns the minimal USB IMU adapter and reusable native dual picoScan configuration.
It replaces mobile_base_imu and mobile_base_lidar. No sensor decoder, scan merger,
TF publisher or fusion engine is added. usb_imu remains the installed executable;
its Python module is now mobile_base_perception.node. Device/topic/frame and
source diagnostics behavior are unchanged.

Component verification uses the installed owning-package entries:

```bash
ros2 launch mobile_base_perception imu.launch.py imu_config:=/absolute/imu.yaml
ros2 launch mobile_base_perception dual_picoscan.launch.py lidar_config:=/absolute/lidar.yaml
```

Installed example profiles are in `share/mobile_base_perception/config`:

```bash
perception_share="$(ros2 pkg prefix mobile_base_perception)/share/mobile_base_perception"
ros2 launch mobile_base_perception imu.launch.py imu_config:="$perception_share/config/imu.yaml"
ros2 launch mobile_base_perception dual_picoscan.launch.py lidar_config:="$perception_share/config/lidar.yaml"
```

Run each command separately in the correctly provisioned hardware container.
These commands open the IMU device or start/configure the LiDARs; they are not
hardware-free inspection commands. For argument inspection use `--show-args`.
Only run one driver per device. No motor controller is started.

`imu.yaml` is native ROS parameter YAML for node `usb_imu`; `lidar.yaml` is a flat
mapping of the dual-LiDAR launch arguments. Both profiles must be explicitly
selected. Relative config paths resolve from the caller's working directory;
`~` is expanded. Missing files fail launch. Native ROS loads/validates IMU YAML
and the adapter validates its parameters; the LiDAR launch parses its settings
and retains native driver validation. There is no fallback profile. LiDAR CLI
arguments override individual YAML entries; the original all-CLI workflow is
still supported. Unspecified echo/time options retain the existing LAST/mode1
behavior. Config files are installed examples, not hot-reloaded settings.

IMU framing/baud have passive target evidence; firmware identity, independent
unit/axis verification and calibration retain their existing limitations.
Its 0.3-second timeout is a commissioning choice. Gyro covariance is deliberately
unknown (zeros), not imported from the temporary stationary-noise experiment.
This profile is not an accepted deployment EKF uncertainty. LiDAR host IP/ports
must match the actual current network; native shutdown/long-run timing acceptance
remains incomplete. Edit a copied profile for different targets or validated tuning.

Perception starts only its own sensor nodes. For manual model/scan inspection,
start `mobile_base_description description.launch.py` separately, then the IMU
and/or dual-LiDAR entries in their own terminals. Start the native Foxglove bridge
separately if needed. The former sensor_model composition is removed. Native
SICK TF/embedded IMU remain disabled; Description owns mounting/scan transforms.
Both formal scans retain LAST echo and native _1 frames. Core acceptance still
precedes #38 integration and #39/#41 product Bringup delivery.

The following IMU protocol and historical observations retain their original
evidence scope. The latest deployment mount is model yaw+90 degrees; the dated
zero-rpy observation below predates that Operator revision. Adapter axis
configuration and physical axis/scale/calibration still need applicable evidence.

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
-1 (unavailable); acceleration covariance remains all zero (unknown). Angular velocity covariance
also defaults to all zero, the ROS convention for unknown covariance. Optional
`angular_velocity_variances` is a ROS double array of exactly three values in
published `base_imu_link` x/y/z axes, in `(rad/s)^2`, already after unit/axis
conversion. Use floating-point YAML entries. All zeros preserve unknown; supplied
entries must all be finite and positive. Mixed zeros, negatives, nonfinite or
wrong-length vectors fail configuration before serial open. Supplied values
populate only diagonal entries0/4/8, with zero off-diagonals. The adapter does
not rescale/permutate these already-published-axis variances or verify calibration.
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
colcon build --packages-select mobile_base_perception --symlink-install
colcon test --packages-select mobile_base_perception
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

## Connected-device observation (2026-10-02)

An authorized bounded read-only capture from `/dev/fihRobotBaseIMU` at the guide's
115200 setting observed 539 XOR-valid 59-byte AA55 packets over 3.001 seconds
(about 179.6 packets/s received), with one invalid candidate. The first wire
acceleration triplet was approximately (-0.00823, 0.00457, 0.99653). This confirms
observed framing/layout compatibility, not firmware identity, units, mounted
axis directions, timestamp accuracy, bias or calibration. No serial commands or
firmware writes were sent. This observation is distinct from the adapter's
software fixture tests; an actual calibrated ROS/estimation run remains pending.

## Installation confirmation and passive sample (2026-10-07)

The operator confirmed that the IMU installation coordinates match the authoritative
URDF. Its `base_imu_link` joint has zero rpy relative to `base_link`; identity
adapter axes `[1,2,3]` are therefore the operator-confirmed installation choice.
This does not independently verify the firmware's wire-axis convention or gyro
signs during rotation.

A five-second passive capture at 115200 received 869 finite XOR-valid packets
over 5.008 seconds (173.5 packets/s), with zero invalid candidates. Mean wire
acceleration was approximately (-0.00822, 0.00231, 0.99595), consistent with the
guide's approximately +1g Z reading. Mean wire gyro was approximately
(0.03662, -0.00212, -0.04443). These are observations, not calibrated bias,
covariance, scale, acquisition rate or timing accuracy. Controlled directional
rotation and scale verification remain pending. No motor commands or serial
payload commands were sent.

The bounded capture script, raw bytes and timestamped summary are retained in
`docs/validation/artifacts/imu-passive-20261007.tar.gz`. The script uses exclusive
serial access; no production adapter or fusion runtime was changed.

Diagnostics distinguish angular velocity covariance supplied, unknown or invalid configuration, while retaining the calibration-not-verified limitation. No deployment covariance values are provided; calibration and estimation acceptance remain separate requirements.
