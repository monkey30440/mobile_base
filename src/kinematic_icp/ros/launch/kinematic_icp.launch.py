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

"""Launch file for Kinematic-ICP Online Node in mobile_base."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for Kinematic-ICP online node."""
    pkg_share = get_package_share_directory('kinematic_icp')
    default_params_file = os.path.join(pkg_share, 'config', 'kinematic_icp_ros.yaml')

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Full path to the Kinematic-ICP parameter YAML file',
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true',
    )

    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Logging level for Kinematic-ICP node',
    )

    lidar_topic_arg = DeclareLaunchArgument(
        'lidar_topic',
        default_value='/scan_front',
        description='Sensor topic for input pointcloud/laser scan',
    )

    use_2d_lidar_arg = DeclareLaunchArgument(
        'use_2d_lidar',
        default_value='true',
        description='Whether input sensor is a 2D laser scan',
        choices=['true', 'false'],
    )

    lidar_odometry_topic_arg = DeclareLaunchArgument(
        'lidar_odometry_topic',
        default_value='lidar_odometry',
        description='Output topic for estimated LiDAR odometry',
    )

    lidar_odom_frame_arg = DeclareLaunchArgument(
        'lidar_odom_frame',
        default_value='odom',
        description='Odometry parent frame ID',
    )

    wheel_odom_frame_arg = DeclareLaunchArgument(
        'wheel_odom_frame',
        default_value='odom',
        description='Wheel odometry frame ID',
    )

    base_frame_arg = DeclareLaunchArgument(
        'base_frame',
        default_value='base_footprint',
        description='Robot base frame ID',
    )

    publish_odom_tf_arg = DeclareLaunchArgument(
        'publish_odom_tf',
        default_value='false',
        description='Whether to publish odom TF',
        choices=['true', 'false'],
    )

    invert_odom_tf_arg = DeclareLaunchArgument(
        'invert_odom_tf',
        default_value='false',
        description='Whether to invert published odom TF',
        choices=['true', 'false'],
    )

    wheel_odom_topic_arg = DeclareLaunchArgument(
        'wheel_odom_topic',
        default_value='/diff_drive_controller/odom',
        description='Wheel odometry input topic',
    )

    kinematic_icp_node = Node(
        package='kinematic_icp',
        executable='kinematic_icp_online_node',
        name='kinematic_icp_online_node',
        output='screen',
        remappings=[
            ('lidar_odometry', LaunchConfiguration('lidar_odometry_topic')),
        ],
        parameters=[
            LaunchConfiguration('params_file'),
            {
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'lidar_topic': LaunchConfiguration('lidar_topic'),
                'use_2d_lidar': LaunchConfiguration('use_2d_lidar'),
                'wheel_odom_topic': LaunchConfiguration('wheel_odom_topic'),
                'lidar_odom_frame': LaunchConfiguration('lidar_odom_frame'),
                'wheel_odom_frame': LaunchConfiguration('wheel_odom_frame'),
                'base_frame': LaunchConfiguration('base_frame'),
                'publish_odom_tf': LaunchConfiguration('publish_odom_tf'),
                'invert_odom_tf': LaunchConfiguration('invert_odom_tf'),
            },
        ],
        arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
    )

    return LaunchDescription([
        params_file_arg,
        use_sim_time_arg,
        log_level_arg,
        lidar_topic_arg,
        use_2d_lidar_arg,
        lidar_odometry_topic_arg,
        lidar_odom_frame_arg,
        wheel_odom_frame_arg,
        base_frame_arg,
        publish_odom_tf_arg,
        invert_odom_tf_arg,
        wheel_odom_topic_arg,
        kinematic_icp_node,
    ])
