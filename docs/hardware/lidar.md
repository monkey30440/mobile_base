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

Upstream 3.9.0 unconditionally appends a layer suffix to LaserScan `header.frame_id`; the single picoScan layer produces `base_lidar_link_FL_1` / `base_lidar_link_BR_1`. Multiple published echoes also append an echo index. `publish_frame_id` remains the physical mounting frame prefix. Exact unsuffixed LaserScan IDs are not provided by this native API. Required resolution is a model-owned identity child alias or a revised frame contract; no custom header rewrite is implemented. Until this is resolved, exact frame acceptance remains open.

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
