# mobile_base_bringup Mapping Mode

## Purpose

Mapping Mode starts the complete real-hardware mapping stack by composing the already validated subsystem launch files. `mobile_base_bringup` adds orchestration only; subsystem packages remain authoritative for drivers, controllers, estimation, SLAM parameters, and TF ownership.

Starting Mapping Mode does not command chassis motion. Teleop remains a deliberate operator action in a separate terminal.

## Prerequisites

- Docker is running.
- AMR hardware is connected and the required `/dev` devices are mapped into the container.
- The physical work area is safe and clear.
- E-stop/STO is available to the operator.
- The workspace has already been built.

## Start the container

On the host:

```bash
docker compose up -d
docker compose exec mobile_base bash
```

## Source the environment

In every new container terminal:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

## Start Mapping Mode

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
- `/rf2o/odom`: RF2O laser odometry, with RF2O TF publication disabled by its subsystem configuration
- `/odometry/filtered`: EKF fused odometry
- `/map`: slam_toolbox occupancy grid
- TF `odom -> base_footprint`: owned by EKF
- TF `map -> odom`: owned by slam_toolbox

Mapping Mode does not start AMCL, `mobile_base_localization`, or S6 Navigation.

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
