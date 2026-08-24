# mobile_base_bringup

## Purpose

`mobile_base_bringup` provides thin, top-level real-hardware workflow orchestration for `mobile_base` operational modes (Mapping Mode and Navigation Mode) by composing validated subsystem launch files. Subsystem packages remain authoritative for drivers, controllers, estimation, SLAM/AMCL parameters, Nav2 configuration, and TF ownership.

---

## Mapping Mode

### Purpose

Mapping Mode starts the complete real-hardware mapping stack. It does not command chassis motion; teleop remains a deliberate operator action in a separate terminal.

### Start Mapping Mode

Without Foxglove:

```bash
ros2 launch mobile_base_bringup mapping.launch.py
```

With optional Foxglove visualization:

```bash
ros2 launch mobile_base_bringup mapping.launch.py \
  use_foxglove:=true
```

Healthy Mapping Mode provides these major runtime contracts:

- `/scan`: merged front and rear LiDAR scan
- `/imu/data_raw`: raw IMU measurements
- `/rf2o/odom`: RF2O laser odometry, with RF2O TF publication disabled
- `/odometry/filtered`: EKF fused odometry
- `/map`: slam_toolbox occupancy grid
- TF `odom -> base_footprint`: owned by EKF
- TF `map -> odom`: owned by slam_toolbox

Mapping Mode does not start AMCL, `mobile_base_localization`, or S6 Navigation.

---

## Navigation Mode

### Purpose

Navigation Mode starts the complete real-hardware autonomous navigation stack by composing S7 base control, S1 description, S2 perception (IMU, dual LiDAR, laser merger, RF2O), S3 state estimation (EKF), S5 localization (Map Server, AMCL), and S6 navigation (Nav2 route-assisted stack, collision monitor).

Starting Navigation Mode does not command chassis motion. Motion occurs only upon receiving valid navigation goals.

### Start Navigation Mode

Without Foxglove:

```bash
ros2 launch mobile_base_bringup navigation.launch.py \
  map:=$(pwd)/maps/test_site/map.yaml \
  route_graph:=$(pwd)/maps/test_site/route_graph.geojson
```

With optional Foxglove visualization:

```bash
ros2 launch mobile_base_bringup navigation.launch.py \
  map:=$(pwd)/maps/test_site/map.yaml \
  route_graph:=$(pwd)/maps/test_site/route_graph.geojson \
  use_foxglove:=true
```

Healthy Navigation Mode provides these major runtime contracts:

- `/scan`: merged front and rear LiDAR scan
- `/imu/data_raw`: raw IMU measurements
- `/rf2o/odom`: RF2O laser odometry (TF disabled)
- `/odometry/filtered`: EKF fused odometry
- `/map`: static map published by `nav2_map_server`
- `/amcl_pose`: AMCL estimated global pose
- TF `odom -> base_footprint`: owned solely by EKF
- TF `map -> odom`: owned solely by `nav2_amcl` (after initial pose received)
- Velocity Command Chain: `controller_server` (`/cmd_vel_nav`) -> `collision_monitor` -> `/diff_drive_controller/cmd_vel`
- S4 `slam_toolbox` is strictly excluded and not running.

### Initial Pose Injection

After starting Navigation Mode, inject the approximate initial pose via RViz2 `2D Pose Estimate` tool or published `/initialpose` topic. AMCL will initialize its particle filter and begin publishing `map -> odom` TF.

---

## Start Teleop in a second terminal

First confirm Mapping Mode is healthy and the area is safe. Then open a second container terminal, source the environment, and run:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -p stamped:=true \
  -p speed:=0.10 \
  -r cmd_vel:=/diff_drive_controller/cmd_vel
```

Operator keys:

- `i`: forward
- `,`: reverse
- `j`: left
- `l`: right
- `k`: active stop

## Mapping operation

- Start slowly and keep the configured low speed.
- Cover fixed environmental geometry.
- Revisit useful features from multiple viewpoints.
- Avoid unnecessary high-speed motion.
- Press `k` and confirm the AMR is stationary before saving.

## Foxglove

Foxglove Bridge is optional visualization tooling and is not required for Mapping correctness. It starts only when `use_foxglove:=true` is supplied to Mapping Mode. Connect the Foxglove client to the bridge endpoint shown in the bridge startup output.

## Save and validate the map

After stopping the AMR, use a third sourced container terminal while Mapping Mode is still publishing `/map`:

```bash
ros2 run mobile_base_bringup save_map.sh
```

The helper creates a directory under the repository map root using local save time in `YYYYMMDD_HHMMSS` format. For example:

```text
maps/20260820_143012/
├── map.yaml
└── map.pgm
```

It preserves the validated `nav2_map_server map_saver_cli` topic, format, mode, thresholds, transient-local subscription, and timeout. After a successful save it automatically runs:

```bash
ros2 run mobile_base_mapping validate_map_readback \
  maps/<timestamp>/map.yaml
```

Successful read-back evidence includes:

```text
STATUS: LOAD_MAP_SUCCESS
RESOLUTION: 0.05
WIDTH: <value greater than 0>
HEIGHT: <value greater than 0>
DATA_SIZE: <value equal to WIDTH * HEIGHT>
```

Timestamped runtime maps are ignored by Git by default. `maps/template/` remains the tracked repository layout template.

## Shutdown

1. Press `k` and ensure the AMR is stationary.
2. Exit Teleop.
3. Save the map if needed while `/map` is still available.
4. Stop the Mapping Mode launch.
5. Exit the container as appropriate.

`Ctrl-C` stops a foreground process; it is not an emergency stop. Use the AMR E-stop/STO for an emergency.

## Troubleshooting

### `/map` is absent

```bash
ros2 topic list | grep '^/map$'
ros2 lifecycle get /async_slam_toolbox_node
ros2 topic hz /scan
ros2 run tf2_ros tf2_echo odom base_footprint
```

Confirm slam_toolbox is active and both `/scan` and the odometry TF are available.

### `/scan` is absent

```bash
ros2 topic list | grep -E '^/scan(_front|_rear)?$'
ros2 topic hz /scan_front
ros2 topic hz /scan_rear
ros2 node list | grep -E 'lidar|laser_merger'
```

Check both SICK devices, their network configuration, and the merger node output.

### The AMR does not respond to Teleop

```bash
ros2 topic hz /diff_drive_controller/cmd_vel
ros2 control list_controllers
ros2 topic echo /diff_drive_controller/cmd_vel --once
```

Confirm the Teleop terminal is focused, the controller is active, hardware is enabled, and no safety stop is asserted. Do not bypass E-stop/STO.

### Map save times out

```bash
ros2 topic info /map --verbose
ros2 topic echo /map --once
```

Keep Mapping Mode running and confirm `/map` has an active transient-local publisher before retrying.

### Read-back fails

```bash
ls -l maps/<timestamp>/map.yaml maps/<timestamp>/map.pgm
ros2 run mobile_base_mapping validate_map_readback \
  maps/<timestamp>/map.yaml
```

Use the exact timestamp directory reported by `save_map.sh`. Inspect the validator error and map YAML image path; do not hand-edit a partial save into appearing valid.

### Foxglove does not connect

```bash
ros2 node list | grep foxglove
ros2 node info /foxglove_bridge
```

Confirm Mapping Mode was launched with `use_foxglove:=true`, then use the bridge endpoint printed at startup and check container/network access.
