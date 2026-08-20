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

"""Launch composition for dual_laser_merger in S2 Perception."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for dual LiDAR scan merger."""
    laser_1_topic_arg = DeclareLaunchArgument(
        'laser_1_topic',
        default_value='/scan_front',
        description='Topic name of first LaserScan input (Front-Left LiDAR)'
    )

    laser_2_topic_arg = DeclareLaunchArgument(
        'laser_2_topic',
        default_value='/scan_rear',
        description='Topic name of second LaserScan input (Rear-Right LiDAR)'
    )

    target_frame_arg = DeclareLaunchArgument(
        'target_frame',
        default_value='base_link',
        description='Target TF coordinate frame for merged LaserScan'
    )

    merged_scan_topic_arg = DeclareLaunchArgument(
        'merged_scan_topic',
        default_value='/scan',
        description='Output topic name for merged 360-degree LaserScan'
    )

    laser_1_topic = LaunchConfiguration('laser_1_topic')
    laser_2_topic = LaunchConfiguration('laser_2_topic')
    target_frame = LaunchConfiguration('target_frame')
    merged_scan_topic = LaunchConfiguration('merged_scan_topic')

    merger_parameters = {
        'laser_1_topic': laser_1_topic,
        'laser_2_topic': laser_2_topic,
        'target_frame': target_frame,
        'merged_scan_topic': merged_scan_topic,
        'merged_cloud_topic': '/sick_internal/merged_cloud',
        'angle_min': -3.141592653589793,
        'angle_max': 3.141592653589793,
        'angle_increment': 0.0058171823974636,
        'scan_time': 0.04,
        'range_min': 0.05,
        'range_max': 25.0,
        'min_height': -1.0,
        'max_height': 1.0,
        'tolerance': 0.05,
        'allowed_radius': 0.20,
        'use_inf': True,
        'inf_epsilon': 1.0,
    }

    merger_node = Node(
        package='dual_laser_merger',
        executable='dual_laser_merger_node',
        name='dual_laser_merger_node',
        output='screen',
        parameters=[merger_parameters],
    )

    return LaunchDescription([
        laser_1_topic_arg,
        laser_2_topic_arg,
        target_frame_arg,
        merged_scan_topic_arg,
        merger_node,
    ])
