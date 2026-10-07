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
LiDAR, Teleop, SLAM or Navigation. The independently launched Description owns robot_state_publisher;
Control consumes that model and starts no RSP. Composition must preserve this
single model TF owner.

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

## Development phase correction (2026-10-07)

Core Control/IMU/LiDAR verification uses each owning package's installed entry.
After core acceptance, ticket #38 integrates the model, real wheel/IMU data and
native EKF; #39/#41 then deliver Mapping/Navigation product composition.
The existing dataset and local-estimation entries below are partial software
deliveries, not complete product Bringup or prerequisites for component tests.
The additional component/base wrappers introduced in dc3f6ee were withdrawn.
Their recorded software results remain historical evidence, not current entries.
