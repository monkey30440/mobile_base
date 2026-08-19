# Copyright 2026 Antigravity Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Launch composition for TDK IIM-42652 IMU acquisition in S2 Perception."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for TDK IIM-42652 IMU acquisition."""
    port_arg = DeclareLaunchArgument(
        'port',
        default_value='/dev/ttyACM0',
        description='USB serial port for TDK HandBoard IMU V1'
    )

    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='115200',
        description='Serial baud rate for TDK IMU'
    )

    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='base_imu_link',
        description='Authoritative TF frame ID for IMU'
    )

    imu_topic_arg = DeclareLaunchArgument(
        'imu_topic',
        default_value='/imu/data_raw',
        description='Authoritative output topic for raw IMU measurements'
    )

    port = LaunchConfiguration('port')
    baud_rate = LaunchConfiguration('baud_rate')
    frame_id = LaunchConfiguration('frame_id')
    imu_topic = LaunchConfiguration('imu_topic')

    imu_node = Node(
        package='tdk_ros2_imu',
        executable='tdk_imu_node',
        name='imu_driver_node',
        output='screen',
        parameters=[{
            'port': port,
            'baud_rate': baud_rate,
            'frame_id': frame_id,
        }],
        remappings=[
            ('/tdk/imu', imu_topic),
        ],
    )

    return LaunchDescription([
        port_arg,
        baud_rate_arg,
        frame_id_arg,
        imu_topic_arg,
        imu_node,
    ])
