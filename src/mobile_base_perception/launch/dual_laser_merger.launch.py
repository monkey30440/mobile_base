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

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for dual LiDAR scan merger."""
    perception_pkg = get_package_share_directory('mobile_base_perception')

    default_config_path = PathJoinSubstitution([
        perception_pkg, 'config', 'dual_laser_merger.yaml'
    ])

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_config_path,
        description='Path to dual_laser_merger parameter YAML file'
    )

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

    params_file = LaunchConfiguration('params_file')
    laser_1_topic = LaunchConfiguration('laser_1_topic')
    laser_2_topic = LaunchConfiguration('laser_2_topic')
    target_frame = LaunchConfiguration('target_frame')
    merged_scan_topic = LaunchConfiguration('merged_scan_topic')

    merger_node = Node(
        package='dual_laser_merger',
        executable='dual_laser_merger_node',
        name='dual_laser_merger_node',
        output='screen',
        parameters=[
            params_file,
            {
                'laser_1_topic': laser_1_topic,
                'laser_2_topic': laser_2_topic,
                'target_frame': target_frame,
                'merged_scan_topic': merged_scan_topic,
            }
        ],
    )

    return LaunchDescription([
        params_file_arg,
        laser_1_topic_arg,
        laser_2_topic_arg,
        target_frame_arg,
        merged_scan_topic_arg,
        merger_node,
    ])
