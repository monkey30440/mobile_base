# Copyright 2026 FIH
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

"""Launch the TDK HandBoard IMU driver."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Create the IMU driver launch description."""
    port = LaunchConfiguration('port')
    baud_rate = LaunchConfiguration('baud_rate')
    frame_id = LaunchConfiguration('frame_id')
    imu_topic = LaunchConfiguration('imu_topic')

    return LaunchDescription([
        DeclareLaunchArgument('port', default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('baud_rate', default_value='115200'),
        DeclareLaunchArgument('frame_id', default_value='base_imu_link'),
        DeclareLaunchArgument('imu_topic', default_value='/imu/data_raw'),
        Node(
            package='tdk_ros2_imu',
            executable='tdk_imu_node',
            name='tdk_imu',
            output='screen',
            parameters=[{
                'port': port,
                'baud_rate': baud_rate,
                'frame_id': frame_id,
            }],
            remappings=[
                ('/tdk/imu', imu_topic),
            ],
        ),
    ])
