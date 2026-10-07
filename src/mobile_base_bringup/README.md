# mobile_base_bringup

## Operator and verification entries

All real-device and integration verification starts from this installed ROS
package. Reusable sensor/control launch implementations stay in their owning
packages; do not assemble a second parallel runtime with temporary /tmp launch
copies. Use only one of the model-containing entries at a time.

| Entry | Starts | Explicit inputs |
| --- | --- | --- |
| model.launch.py | model-only RSP | no device inputs |
| control.launch.py | M1, native controllers and sole RSP | hardware_config; optional model_file override |
| imu.launch.py | USB IMU only | imu_config |
| lidar.launch.py | native dual picoScan only | all sensor/receiver network facts |
| sensor_model.launch.py | dual picoScan and model-only RSP | all sensor/receiver network facts |
| local_base.launch.py | control, IMU, model and native EKF | hardware_config, imu_config, filter_config |
| base.launch.py | local_base plus dual picoScan; optional Foxglove | above inputs plus all network facts |

These are component/local-chain verification entries. Their existence or a
running process does not establish complete Mapping/Navigation readiness.
They start no SLAM, AMCL, Navigation, Teleop or velocity publisher.
Control-containing entries activate the hardware/controllers and can Servo ON
at zero command; normal native lifecycle stopping applies. Run only under the
reviewed Operator conditions. No automatic physical-stop guarantee is added.

Model defaults to the installed mobile_base_description deployment model.
Both measured wheel angles are provided by mobile_base_control. The two nominal
fixed drive seats remain geometry, not measured suspension travel. One native
RSP owns model TF; native EKF alone owns odom→base_footprint. Do not start an
extra description/sensor_model RSP alongside control-containing entries.

Configuration YAML files must be explicit; no target serial parameters,
covariance, operating limits or calibration are invented. local_base checks
that all selected configuration/model files exist before starting nodes. Native
ROS/device configuration owns parsing and invalid configuration errors. Errors
and source logs are preserved; start success is not a health/readiness verdict.

Example for the currently recorded platform network facts (reconfirm if changed):

```bash
ros2 launch mobile_base_bringup base.launch.py \
  hardware_config:=/absolute/hardware.yaml \
  imu_config:=/absolute/imu.yaml \
  filter_config:=/absolute/ekf.yaml \
  fl_hostname:=192.168.0.52 br_hostname:=192.168.0.53 \
  udp_receiver_ip:=192.168.0.51 \
  fl_udp_port:=2115 fl_check_udp_port:=2116 \
  br_udp_port:=2117 br_check_udp_port:=2118 \
  ros_qos:=4 foxglove:=True
```

Both sensors default to native LAST echo, active startup and elapsed-tick
timestamps. listen_only_mode is exposed for passive software/network fixtures;
those fixtures do not accept real sensor data or sensor shutdown. Native startup
changes transient echo/output settings; concurrent sensor drivers must not run.
Foxglove defaults off. When explicitly enabled, connect ws://localhost:8765
(or the target host address); port is configurable via foxglove_port. In 3D use
odom fixed frame, model Mesh up-axis Z-up, /robot_description and both formal
scans. Ctrl+C requests native process shutdown; independently verify inhibited
zero state where hardware acceptance requires it. Foxglove visualization does
not replace native error/status or physical-stop checks.

## Build and software tests

Use a clean build/install prefix after package renaming. Do not source the old
install overlay or treat historic package names as compatible aliases.

```bash
colcon build --packages-up-to mobile_base_bringup
source install/setup.bash
colcon test --packages-select mobile_base_control mobile_base_perception mobile_base_description mobile_base_bringup
colcon test-result --verbose
```

Public control/LiDAR workflows and full local-chain integration tests are in
Bringup. The latter uses OS serial peers and native control/RSP/EKF processes
with the installed model; it does not map hardware. Necessary bounded protocol
checks remain in Control/Perception; model checks remain in Description.

# Dataset loading (#40)

`dataset.launch.py` accepts one required `dataset` directory and selects exactly
`map.pgm`, `map.yaml`, and `route_graph.geojson`. It checks that each required path
is an existing file before starting any native node, and reports the directory
and missing path on failure. Selected paths are logged. Relative paths resolve
against the launch caller's working directory; `~` is expanded. No root directory,
time-based folder name, manifest, dataset catalog or fallback is imposed.

## Prepare and load

Choose a writable directory yourself, for example:

```bash
mkdir -p /workspace/maps/warehouse
```

Place the native saved `map.pgm`/`map.yaml` there. The operator contract is that
`map.yaml` uses `image: map.pgm` from this same directory. Prepare the native
GeoJSON route graph manually in the map's coordinates as `route_graph.geojson`.
Use graph `Point` features with unique `properties.id` and `frame: map`, and
`LineString` edges whose `properties.startid`/`endid` refer to nodes. Legal routes,
direction and costs are engineering inputs, not automatically generated here.
See the [official Nav2 1.3.13 graph example](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_route/graphs/sample_graph.geojson)
and [native GeoJSON loader](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_route/src/plugins/graph_file_loaders/geojson_graph_file_loader.cpp).

```bash
ros2 launch mobile_base_bringup dataset.launch.py dataset:=/workspace/maps/warehouse
```

This narrow launch starts native `map_server` and `route_server` **unconfigured**;
it performs no automatic motion/readiness transition. In another sourced shell:

```bash
ros2 lifecycle set /map_server configure
ros2 lifecycle set /route_server configure
ros2 lifecycle set /map_server activate
ros2 lifecycle get /map_server
ros2 lifecycle get /route_server
```

Both configure results must succeed. Map Server should then be active and Route
Server inactive. Failed configure is failed dataset loading; preserve its native
screen/log reason and fix that selected dataset. A running process is not load
success. No graphless configure, empty graph, alternative dataset or previous map
is offered as a substitute. Full Navigation composition/lifecycle ownership is
provided by subsequent bringup work; this standalone workflow only verifies
native dataset loading and map publication.

Map Server owns YAML/image parsing and I/O errors. Route Server owns JSON/graph
parsing and required graph-to-map TF failures. A nonempty `graph_filepath` is
always supplied, preventing upstream's intentionally permitted graphless
configuration mode. Launch does not parse/read back the map YAML or graph,
rewrite the image reference, inspect map quality, or add a custom validator.
Maintaining the `image: map.pgm` contract and matching graph/map coordinates is
operator responsibility. Native parsing success does not prove semantic pairing,
physical traversability or complete Navigation readiness.

## Software verification

Build/test with the development image and source the overlay. The package's
pytest tests invoke the installed `ros2 launch` entrypoint, real native lifecycle
services and a transient-local `/map` subscription. Tests require isolation from
other ROS applications (use a separate `ROS_DOMAIN_ID`, e.g. 142 for this fixture).

```bash
colcon build --packages-select mobile_base_bringup --symlink-install
source install/setup.bash
colcon test --packages-select mobile_base_bringup
colcon test-result --verbose
```

The controlled 10×10 map/two-node GeoJSON fixture verifies native load and map
publication, with Route Server remaining inactive. Each of the three missing
files fails launch immediately with source path. Invalid YAML, invalid PGM,
invalid JSON, empty graph and missing graph TF each fail the relevant native
configure and do not become inactive/active. These are software fixtures, not a
real robot map, legal route-network review or hardware acceptance.

## Local estimation wiring (#38, partial software delivery)

`local_estimation.launch.py` starts only native `robot_localization/ekf_node`.
It requires an explicit native YAML configuration:

```bash
ros2 launch mobile_base_bringup local_estimation.launch.py filter_config:=/path/to/ekf.yaml
```

The selected path is resolved from the caller's working directory (`~` is
expanded); a missing file fails launch. Native ROS parameter loading owns YAML
parsing errors. There is no default deployment tuning or calibration profile.
The native node name is `ekf_filter_node`; the YAML must configure that node.
The caller supplies one existing robot_state_publisher and valid sensor/model
TF. This launch does not start another model publisher, control hardware, IMU,
LiDAR, Teleop, SLAM or Navigation. The current standalone M1 launch already
starts robot_state_publisher; composition must preserve one model TF owner.

For V1, configure `world_frame: odom`, `odom_frame: odom`,
`base_link_frame: base_footprint`, `publish_tf: true`, and planar estimation.
Use `/base_controller/odom` and `/imu/data_raw` as the actual native input topics
(subject to the chosen namespace/remapping). The controller's odom TF remains
disabled. Only the EKF owns `odom → base_footprint`; model TF belongs to RSP.
Unusable IMU orientation must not be selected. Select gyro yaw rate only once
its axis/scale/timing are validated and its message has calibrated variance;
unknown zeros are not an acceptable input uncertainty for deployment fusion.
Wheel feedback covariance, measurement selections, timeouts and filter tuning
also require deployment evidence. This narrow launch and a running EKF do not
assert Bringup readiness, calibrated uncertainty or complete #38 acceptance.

The software test uses isolated native EKF and RSP processes with explicitly
synthetic wheel speed 0.2 m/s and gyro yaw rate 0.5 rad/s. Synthetic variances
are test inputs, not deployment defaults. It checks public filtered odometry,
TF continuity to the IMU, and that stopping EKF stops the odom transform while
RSP's static model remains available. RSP advertises `/tf` even without moving
joints; publisher count alone is not proof of ownership of a particular edge.
The test has no devices or physical wheel/IMU data and does not establish
physical accuracy, LiDAR optical transforms or a production model package.
