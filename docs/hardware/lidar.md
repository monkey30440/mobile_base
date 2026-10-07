# Dual picoScan150 Operator workflow

Ticket #37 / spec #32: `mobile_base_lidar` composes native `sick_scan_xd` processes only. Install `ros-jazzy-sick-scan-xd`; software verification used 3.9.0. Build with colcon, source the workspace, and inspect `ros2 launch mobile_base_lidar dual_picoscan.launch.py --show-args`.

All sensor/host IPs and UDP receive/check ports are required arguments. Both receive ports and both native receiver-IP check ports must be distinct on the host. Namespace is `/lidar/fl` or `/lidar/br`; full scans are `/lidar/fl/scan` and `/lidar/br/scan`, segments end in `/scan_segment`. Native node names `picoscan_fl` / `picoscan_br` identify process logs and ROS interfaces. Native `udp_sender` remains empty (bind all local interfaces). In 3.9.0 this parameter binds a local address rather than filtering a remote sender. Source association uses exclusive sensor destination configuration and distinct UDP ports; the driver does not enforce remote sender-IP filtering. Timestamps and native frames pass through untouched. No decoder, merger or monitoring runtime is added. Native IMU and TF publication are disabled; model TF belongs to robot_state_publisher.

## Target facts read 2026-10-02

Operator confirmed FL=192.168.0.52, BR=192.168.0.53. Target wired host `enP2p1s0` is 192.168.0.51/24. SOPAS `sRN` reads on TCP2111 returned:

| Source | Serial | Firmware | ScanDataFormat | FREchoFilter | Current UDP destination |
|---|---|---|---|---|---|
| FL | 25350157 | 2.1.0 | 2 compact | 2 LAST | 192.168.0.51:2115 |
| BR | 25450354 | 2.1.0 | 2 compact | 1 ALL | 192.168.0.100:2115 |

These are observed settings, not acceptable independent host receive configuration by themselves. Native startup configures the requested receiver address/port and enables output; shutdown disables output. Do not run concurrent drivers against the same device. No persistent IP change, firmware change or factory reset is required. Native defaults include SOPAS timeout5000ms, initial UDP timeout60000ms and running UDP timeout10000ms; these are upstream defaults, not measured operating thresholds. Record actual native startup logs and target configuration with each hardware result.

## Frames and echo selection

Upstream 3.9.0 unconditionally appends a layer suffix to LaserScan `header.frame_id`; the single picoScan layer produces `base_lidar_link_FL_1` / `base_lidar_link_BR_1`. Multiple published echoes also append an echo index. `publish_frame_id` remains the physical mounting frame prefix. Exact unsuffixed LaserScan IDs are not provided by this native API.

On 2026-10-07 the operator confirmed model-owned child frames for the native scan names, preserving FL LAST and BR ALL echo settings. The observed children to support are `base_lidar_link_FL_1` and `base_lidar_link_BR_1_0`, `base_lidar_link_BR_1_1`, `base_lidar_link_BR_1_2`. `robot_state_publisher` owns these model transforms; the driver retains its native headers. This resolves the naming approach, not transform geometry or hardware acceptance. Identity transforms are not assumed from suffixes: the relationship between the CAD mounting frames and scan coordinate frames still requires source/hardware evidence and extrinsic validation before model acceptance.

By default this launch preserves the device's current echo filter. `set_echo_filter:=True echo_filter:=2` explicitly selects native LAST echo during startup; do not assume changing BR ALL to LAST has already been approved/validated. Echo choice must agree with downstream LaserScan consumption and frame aliases.

## Source inspection and faults

Use `ros2 node list`, `ros2 topic info /lidar/fl/scan --verbose` and the BR equivalent to inspect source ownership and offered QoS. Native QoS selectors are0 system defaults and4 SensorDataQoS (BEST_EFFORT); choose an explicit `ros_qos` compatible with the actual consumers. Use `ros2 topic echo /lidar/fl/scan --once --qos-reliability best_effort` to inspect sensor frame, nonzero timestamp and ranges. `ros2 topic hz` observes arrival rate for an operator check; it does not establish sensor timestamp accuracy or a permanent health monitor.

For a fault, retain the native process prefix, timestamp, sensor IP, receiver IP/port and native reason. SOPAS connection/response errors concern TCP2111; UDP receive timeout can indicate routing/interface/firewall, wrong destination, port collision or disabled output. Inspect `ip route get <sensor-IP>` and `ss -lunp`; compare device destination settings against the selected host. Native CRC/compact/msgpack parse failures need native error logs and firmware/format context. Reconnect behavior and actual recovery must be observed on the device; restart success alone does not prove physical recovery.

Use native `ros2 service list -t` to discover each driver's SOPAS service and `ros2 interface show` its request type before calling read commands. No generic diagnosed-publisher frequency/timestamp coverage is claimed for picoScan. An absent diagnostic task is not healthy evidence. TF availability is separate from the scan frame label.

## Evidence

Software tests run at the public Operator/ROS seam with real native processes in passive loopback mode, no mock driver. They verify argument failure, discoverability and separate publishers with SensorDataQoS. They do not supply sensor data and therefore do not validate ranges, timestamps, CRC, geometry or hardware reconnection. Actual dual scans, sensor identity/frame association, fault injection/recovery and extrinsic calibration remain hardware work.

Primary API evidence: [native launch](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/launch/sick_picoscan.launch), [native ROS2 wrapper](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/launch/sick_picoscan.launch.py), [frame suffix implementation](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/ros_msgpack_publisher.cpp#L901), [QoS selectors](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/include/sick_scan/sick_ros_wrapper.h#L393), and repository-authoritative `reference/operating_instructions_picoscan150_2d_lidar_sensors_en_im0106691.pdf`. These source facts do not replace hardware evidence.

### Bounded hardware sample (2026-10-02, not full acceptance)

A25s native run used host192.168.0.51, FL scan/check2115/2116 and BR2117/2118, QoS4, existing device echo policies and native startup/shutdown. FL yielded616 fullframe messages with `base_lidar_link_FL_1`; BR yielded618 messages **per echo** with `base_lidar_link_BR_1_0`, `_1_1`, `_1_2`. Each last message had1200 finite ranges; arrival was approximately25Hz per echo. This proves only that both independently configured sources produced data in this bounded run; neither range accuracy nor calibrated frame geometry is established.

First native timestamp seconds were1426 (device uptime); later timestamps were host epoch1790924879 after native time synchronization. Startup time validity is therefore **not accepted**. Before downstream use, inspect timestamp convergence and establish applicable native synchronization settings/operating limits. No project-owned timestamp observer/rewrite is introduced.

Both native drivers exited with signal11 during SIGINT teardown and logged ROS subscription/context cleanup errors. Output stop commands were logged, but graceful driver shutdown is **not accepted**. Native receiver binding faults were also observed when remote sensor IP was mistakenly supplied as `udp_sender`; this was corrected by retaining the native empty local bind setting. Hardware reconnect, induced timeout, corrupt packet/CRC handling, time convergence acceptance and clean shutdown require further evidence. These limitations must not be hidden by successful software graph tests.

### Native startup timestamp alternative

`tick_to_timestamp_mode:=1` selects upstream elapsed-tick conversion: first host timestamp plus sensor elapsed microsecond ticks. It avoids publishing device-uptime timestamps during PLL startup; this is a native timestamp conversion, not a project observer. A separate15s run with unchanged echo filters produced369 messages per FL/BR echo, host-epoch FIRST stamps1790925215 and last-message arrival age45–47ms. It establishes epoch alignment from first received samples in this bounded run; absolute acquisition-time error, long-run clock drift and cross-device timing remain uncalibrated. The launch selects mode1 by default for the measured startup alternative and exposes an explicit override; mode0 retains the upstream PLL path with the observed pre-lock limitation. Mode2 deliberately publishes sensor clock and is unsuitable for normal ROS consumers.

`sw_pll_only_publish` belongs to other scanner paths and is absent from the picoScan compact parser/configuration path. It must not be assumed to suppress this driver's pre-lock samples. Source: [picoScan native time modes](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/launch/sick_picoscan.launch#L273), [compact parser pre-lock behavior](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/compact_parser.cpp#L1056), [native mode initialization](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/include/sick_scan/softwarePLL.h#L64).

Official releases checked2026-10-02 report [3.9.0](https://github.com/SICKAG/sick_scan_xd/releases/tag/3.9.0) as latest stable. Official crash reports reviewed include [#525](https://github.com/SICKAG/sick_scan_xd/issues/525) (Humble runtime crash) and [#539](https://github.com/SICKAG/sick_scan_xd/issues/539) (RMS2000 startup/protocol issue); neither verifies a fix for the observed Jazzy picoScan SIGINT cleanup crash. No matching verified stable fix was identified. Clean shutdown remains unresolved; no custom driver patch is introduced.

Aligned-image follow-up: `mobile-base-v1-test:jazzy` image SHA256 `f6b55a322a52b908faff8fa284ce85f9d74df6854c6fca16b0fca283642bd262` produced119FL/118perBR echo messages in5s with mode1 and host-epoch first stamps, then both native processes again exited-11 on SIGINT with DDS datareader deletion errors. Updating the test image's ROS/DDS dependencies did not resolve the observed shutdown failure; its cause is not established.

### Frame-direction baseline (2026-10-07)

A stationary, bounded native run on the same production-check image and host
192.168.0.51 received 125 FL scans and 125 scans per BR echo. The current native
responses retained FL LAST=2 and BR ALL=1. No motor device was mapped, no motor
command was sent and the echo filters were not changed. Driver startup used
native transient UDP-output configuration as in the earlier workflow.

Observed scan metadata: 1200 ranges, angle_min=-2.40862894 rad,
angle_max=2.82301044 rad, angle_increment=0.004363336 rad. Use actual metadata,
not the launch collection defaults, when inspecting angles. All floats were
finite, but finite alone does not establish valid range data: the saved last
FL scan had 1096 values within its reported bounds, BR echo0 had 1080, echo1
had 57, and echo2 had zero (its range_max=0.001 was below range_min=0.05).
This is a baseline observation, not proof that all echoes carry obstacles or
that consumer invalid/no-return handling is accepted.

Both native child drivers again exited -11 on SIGINT; the parent launch returned
0. Parent status must not be used as clean-driver-shutdown evidence. The earlier
shutdown limitation remains open. Raw last-scan snapshots, summary, bounded
capture script and native logs are in
`docs/validation/artifacts/lidar-frame-baseline-20261007.tar.gz`.

Native layer/echo frame conventions and optical-axis evidence are in
`docs/research/v1-lidar-frame-preflight.md`. Optical-to-CAD direction still needs
an operator-positioned target before accepting actual scan transforms; no
unvalidated optical yaw has been installed as production TF.

### Operator front-left direction check (2026-10-07)

The operator observed `/lidar/fl/scan` in Foxglove with display frame
`base_lidar_link_FL_1`, reporting the target at x=+0.92 m, y=-0.87 m.
They explicitly confirmed that the target was placed from the front-left
scanner along the AMR forward direction, without intended lateral offset.
The reported point azimuth is -43.40 degrees; under that placement, the
coarse optical-to-robot yaw is approximately 43.40 degrees, supporting
a nominal front-left viewing direction near +45 degrees (robot front-left).
The mounting link itself has zero rpy in the source URDF.

This is operator-reported coarse direction evidence, not a recorded precise
point/target survey or calibrated extrinsic transform. Target extent, optical
origin, placement and measurement error were not quantified. It excludes the
assumption that optical +X is robot-forward, but does not establish exact
translation, yaw/pitch/roll or acceptance tolerances. No production optical
TF is changed from this one point; rear-right direction remains unverified.

### Foxglove ALL-echo observation correction (2026-10-07)

The operator reported no BR points in Foxglove despite correct native frames.
ROS-side observation found dense echo0 and compatible BEST_EFFORT subscriptions;
all three echo transforms were available. A direct SDK WebSocket/CDR probe at
8765 reproduced missing dense echo0: five seconds delivered mostly echo2,
which then had zero valid ranges. Thus the missing dense data was observable
before the 3D panel. This is not evidence that optical mounting TF is calibrated.

An otherwise comparable observation bridge at 8766 with native
`min_qos_depth:=10 max_qos_depth:=10` received 25 messages per echo, including
1096 valid echo0 points. After the previous viewer container was removed, the
agent recreated the independent viewer at ROS domain 176 with those bridge
settings at 8765. The original probe then passed again: 25 messages per echo,
1092 valid echo0 points, matching SDK/CDR schemas and both identity echo TFs.
This supports a queue-depth correction for this bursty multi-echo stream;
internal DDS drop counters were not measured. It does not establish production
queue sizing, no-loss guarantees or successful user-side rendering yet.

Reproduce the observation bridge configuration with:

```bash
ros2 launch foxglove_bridge foxglove_bridge_launch.xml \
  port:=8765 min_qos_depth:=10 max_qos_depth:=10
```

The temporary viewer uses native RSP only for identity connections among BR
echo coordinates; no optical-to-base transform or motor control is added. Device
FL LAST/BR ALL settings remain unchanged. The native driver shutdown fault also
remains open. The UI needs to reconnect after Bridge restart and retain the BR
display frame; a short scan decay can retain the interleaved echoes visually.
Actual Foxglove rendering must still be confirmed by the operator.

The bounded observation probe, RED/alternate-bridge/main-port GREEN results and
errors are retained in
`docs/validation/artifacts/foxglove-br-queue-diagnostic-20261007.tar.gz`.
The installed Bridge 3.5.0 accepts `foxglove.sdk.v1` for the probe. The obsolete
`foxglove.websocket.v1` subprotocol was rejected by this server; this was a
probe compatibility adjustment, not the cause of the user's established UI
connection symptom. No permanent custom Bridge, filter or republisher is added.

### Stable single-echo observation source (2026-10-07, operator confirmed)

The operator confirmed that points returned after the queue correction but the
ALL-echo LaserScan display still flickered. Queue correction therefore did not
complete the visual workflow. Interleaved dense/sparse/empty echoes remain in
one scan topic; no claim is made that scan decay alone fixes this.

For this stationary viewing experiment only, the agent restarted the BR native
driver with an additional native custom PointCloud2 configuration:

```text
custom_pointclouds:=br_view
br_view:=coordinateNotation=0 updateMethod=0 echos=0 layers=1 reflectors=0,1 infringed=0,1 rangeFilter=0.05,120,1 topic=/lidar/br/view_echo0 frameid=base_lidar_link_BR_1_0 publish=1
```

All other network/native settings stayed as in the viewer; in particular
`host_set_FREchoFilter=False`. Native SOPAS readback still reports ALL=1.
The FL driver was not restarted. BR scan topics retain native ALL-echo output;
no merger, decoder or project-owned republisher is added. The pointcloud uses
native full-frame first-echo selection and drops invalid ranges for this
observation. Its optical frame is still separate from the uncalibrated base
model. The configuration is not installed as a product/default navigation input
and does not settle the eventual navigation echo policy.

A bounded ROS observation received 75 PointCloud2 messages, each with 1094–1098
points, fields x/y/z/i and the single expected optical frame. This confirms a
nonempty single-source stream, not successful Foxglove rendering yet. The
operator is asked to disable BR scan/segment display and use
`/lidar/br/view_echo0` with the same native display frame. Precise mounting and
native teardown evidence remain unchanged. These temporary viewer settings
end with the observation container; no permanent runtime files were modified.

The operator subsequently confirmed `/lidar/br/view_echo0` is stable in
Foxglove. This completes the stationary single-echo viewing check only; the
ALL-echo LaserScan display was not demonstrated stable. BR optical mounting
direction/calibration and production consumer echo policy remain unresolved.

### Operator coarse BR direction observation (2026-10-07)

After confirming `/lidar/br/view_echo0` stable, the operator followed the
request to place a scan-height target approximately 1 m along the AMR rearward
direction from the BR sensor, with no intended lateral offset. The reported
optical coordinates were x=+0.71 m, y=+0.68 m (quadrant +X/+Y).
Their bearing is atan2(0.68,0.71)=43.76 degrees; a robot-relative rearward
bearing of 180 degrees implies optical yaw approximately 136.24 degrees.
This supports a nominal +135-degree rear-right optical direction, complementing
the earlier nominal +45-degree FL observation.

This is operator-reported coarse direction evidence, not calibrated mounting
TF: target alignment, dimensions, placement uncertainty and sensor translation
were not measured. No production TF or runtime configuration is changed by
this observation. Exact optical mounting calibration remains required.

### Completed flicker diagnosis (2026-10-07)

See [root-cause verification](../validation/lidar-foxglove-root-cause-20261007.md):
490 matched ROS/WebSocket messages, controlled queue-depth contrast, and replay
of the actual installed Foxglove batch/geometry/history code. BR multiplexed
ALL echoes replace the same topic geometry; the empty third echo clears points
at zero decay. FL has one echo stream. Native echo0 observation is operator-
confirmed stable; original ALL scan GUI repair is not claimed.

### Current formal scan contract (2026-10-07 revision)

The user explicitly superseded BR ALL with a production-oriented single native
scan/frame contract. Both drivers now apply native LAST=2 on startup; frames are
FL_1/BR_1 under the original mounting links, published by mobile_base_description
and native RSP. Native bool CLI values use 1/0 (stoi conversion), not True/False.
See [staged integration evidence and manual gate](../validation/single-echo-model-20261007.md).
Historical ALL/echo-view experiments above are evidence, not current deployment
settings. Nominal +45/+135 yaw remains uncalibrated; final GUI alignment is pending.

### Inverted mounting fact and corrected profile (2026-10-07)

Operator accepted stable formal single-echo scans but rejected yaw-only model
orientation, confirming both LiDAR tops face downward. Initial yaw-only profile
is superseded: nominal roll=pi/pitch0, FL yaw=-pi/4, BR yaw=-3pi/4. Mounting and
scan device axes now have +Z down; source CAD meshes stay in separately named
CAD links. Body/IMU TF is preserved. Whole-model visual-only orientation is
checked via Foxglove Scene Mesh up-axis Z-up, rather than an arbitrary +90-degree
URDF rotation. See [correction and pending manual gate](../validation/inverted-model-20261007.md).

## Source-link correction (2026-10-07)

Operator rejected additional base_lidar_cad_link_FL/BR frames. The current model
preserves the source base_lidar_link_FL/BR CAD transforms and geometry and places
explicit optical orientation on native _1 children only. Earlier extra-CAD-link
model notes are superseded. See [validation](../validation/source-link-model-20261007.md).
