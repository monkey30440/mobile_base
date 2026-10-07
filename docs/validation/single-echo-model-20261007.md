# Native dual single-echo scan + base model integration

2026-10-07. User requested production-oriented `/lidar/fl/scan` /
`/lidar/br/scan`, native frames `base_lidar_link_FL_1` /
`base_lidar_link_BR_1`, and integration with mobile_base_description.
This supersedes the earlier BR ALL decision; #32/#37 reflect the revision.
No custom scan decoder/merger/header rewrite or viewing-only topic is used.

## Stages and evidence

1. **Native settings:** sick_scan_xd 3.9.0 LAST=2 is applied on each startup.
   Both actual sensors read back `sRA FREchoFilter 2`. This is transient SOPAS
   setup; a device power-cycle/reconnect is not claimed validated.
2. **Installed model:** build-time extraction retains the authoritative base
   subtree, geometry/inertials/movable joints, removes the upper-body branch,
   installs base meshes with resolvable package URIs, reroots normalized
   base_footprint, and adds optical children. Native RSP is the sole model owner.
   The native public model/TF test went RED (package missing), then GREEN.
3. **Configuration regression:** native CLI booleans True/False are string
   overrides. Upstream `rosConvParam(string,bool)` uses `stoi`; True fails and
   leaves the previous/default value. A public parameter-service regression
   distinguishes old True strings from the corrected native 1/0 strings.
   Mixing XML with ROS YAML overrides was tried and rejected: XML defaults
   replaced some YAML values, causing wrong ports. The final launch uses only
   the upstream XML/CLI configuration entrance and numeric booleans.
   See [pinned native wrapper](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/include/sick_scan/sick_ros_wrapper.h#L298-L347)
   and [native ROS2 launch](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/launch/sick_picoscan.launch.py).
4. **Software suite:** model and LiDAR packages build; 4 pytest cases pass,
   including both native parameter services. Colcon's aggregate counts also
   include CTest wrappers; do not describe the wrapper count as extra test cases.
5. **Stationary hardware observation:** 10-second bounded observer received:

| Topic | Messages | Rate | Valid points | Max arrival gap |
|---|---:|---:|---:|---:|
| /lidar/fl/scan | 233 | 25.00 Hz | 1096–1099 | 43.5 ms |
| /lidar/br/scan | 242 | 25.00 Hz | 1087–1095 | 43.2 ms |

Each topic had one publisher and only its specified `_1` frame. Startup/discovery
explains fewer than 250 messages; rates use first/last received times. Maximum
observed stamp age was about 51 ms, not proof of sensor acquisition-time accuracy.
The operator's previously confirmed stable view_echo0 source is now stopped.

6. **TF and assets:** one /tf_static publisher; actual RSP published
   /robot_description. Lookup from base_footprint gives FL (.28771,.26721,.19589),
   BR (-.24671,-.26721,.19589), IMU (.04375,-.008,.24141). Explicit optical yaw
   is +45/+135 degrees. Native Bridge was restarted with the installed overlay;
   package asset fetch returned the 11,573,684-byte base STL exactly equal to the
   installed file (SHA256 d5f0f246b20f8f1f715455f6f5f554c6d6044f8f2831d0c47eecf91407ba32d9).
7. **Client boundary:** SDK WebSocket received both single-frame streams and
   model static TF. Replaying the real installed Foxglove 3.3.0 zero-decay batch
   filter with the final scans yielded FL 0/126 empty updates and BR 0/125. This
   is the same seam that previously reproduced empty BR updates. It does not
   replace final operator GUI/physical alignment verification.

Artifact: `artifacts/single-echo-model-20261007.tar.gz`: observer, expanded
published model, settings/readback logs, RED regression evidence, suite output,
WebSocket capture, asset result and renderer result. Renderer extraction/replay
method is retained in the earlier root-cause artifact/report.

## Reusable launch

After building the two packages and sourcing the resulting install:

```bash
ros2 launch mobile_base_lidar sensor_model.launch.py \
  fl_hostname:=192.168.0.52 br_hostname:=192.168.0.53 \
  udp_receiver_ip:=192.168.0.51 \
  fl_udp_port:=2115 br_udp_port:=2117 \
  fl_check_udp_port:=2116 br_check_udp_port:=2118 ros_qos:=4 \
  fl_scan_yaw:=0.7853981633974483 br_scan_yaw:=2.356194490192345
```

This composes native drivers with native RSP; no motor driver is started.
A separate native Bridge must source the same overlay for package asset lookup.
Current temporary test container is mobile_base_view (ROS_DOMAIN_ID176), with
installed overlay `/tmp/base-model-install`; its install is rebuilt from tracked
sources, not a durable production deployment location. Host main Compose container
is unchanged. Do not start a second sensor/model launch while this one is active.

## Final operator gate

Reconnect Foxglove to ws://localhost:8765. Fixed/Display frame base_footprint;
show only /lidar/fl/scan, /lidar/br/scan and /robot_description. Use decay0,
distinct scan colors, and axes/TF visibility. Inspect FL at front-left, BR at
rear-right; overlapping stationary walls should agree in base coordinates.
Place a target in robot-forward/left/right/rear positions within coverage and
check its transformed position and change, separately for each scanner. Robot
need not move. Actual GUI stability/alignment is **pending operator evidence**.

## Explicit limits

Nominal optical +45/+135 yaw follows coarse operator observations, not precise
calibration. Optical translation uses the supplied CAD origin pending measurement;
extrinsic pitch/roll/offset/yaw accuracy remains uncalibrated. This stage establishes
the fixed base/sensor tree, not all movable-joint TF: real wheel/caster/suspension
feedback is required; no joint_state_publisher/zero-state fabrication is introduced.
No odom->base_footprint or map->odom is fabricated; EKF/mapping/localization remain
separate owners. Do not co-start M1's standalone RSP with this model-only RSP;
final full bringup must have one model/control-description owner. IMU acquisition
and motors are not started here. Native -11 shutdown, reconnect/power-cycle,
long-duration/drop behavior, Orin target evidence and production calibration remain
open. #37/#38 remain partial and are not closed by this integration.
