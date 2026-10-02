# tdk_ros2_imu

ROS 2 driver for the HandBoard IMU V1 using the TDK IIM-42652 sensor.

The device streams 59-byte binary packets over USB serial. The node validates
the packet header and XOR checksum, converts the measurements to SI units, and
publishes `sensor_msgs/msg/Imu` on `/tdk/imu`.

## Parameters

| Name | Default | Description |
| --- | --- | --- |
| `port` | `/dev/ttyACM0` | USB serial device |
| `baud_rate` | `115200` | Serial baud rate |
| `frame_id` | `base_imu_link` | Frame written to each IMU message |

## Run

```bash
ros2 run tdk_ros2_imu tdk_imu_node \
  --ros-args -p port:=/dev/ttyACM0
```

or:

```bash
ros2 launch tdk_ros2_imu tdk_imu.launch.py port:=/dev/ttyACM0
```

The fusion orientation is relative to the device pose at power-on. Because the
sensor has no magnetometer, yaw can drift and is not an absolute heading.

The driver preserves the device axes. The physical installation must align the
sensor axes with the frame supplied through `frame_id`, or provide a suitable
TF relationship using a distinct sensor frame.
