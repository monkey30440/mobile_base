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

"""Launch file for rf2o_laser_odometry node with authoritative AMR contracts."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for RF2O laser odometry."""
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='warn',
        description='RF2O logger level (use info for per-scan diagnostics)'
    )

    rf2o_node = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        name='rf2o_laser_odometry',
        output='screen',
        parameters=[{
            'laser_scan_topic': '/scan',
            'odom_topic': '/rf2o/odom',
            'base_frame_id': 'base_footprint',
            'odom_frame_id': 'odom',
            'publish_tf': False,
            'init_pose_from_topic': '',
            'freq': 20.0,
        }],
        arguments=[
            '--ros-args',
            '--log-level',
            ['rf2o_laser_odometry:=', LaunchConfiguration('log_level')],
        ],
    )

    return LaunchDescription([
        log_level_arg,
        rf2o_node,
    ])
