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

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for RF2O laser odometry."""
    try:
        rf2o_pkg = get_package_share_directory('rf2o_laser_odometry')
        default_config_path = PathJoinSubstitution([
            rf2o_pkg, 'config', 'rf2o_laser_odometry.yaml'
        ])
    except Exception:
        default_config_path = ''

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_config_path,
        description='Path to RF2O parameter YAML file'
    )

    laser_scan_topic_arg = DeclareLaunchArgument(
        'laser_scan_topic',
        default_value='/scan',
        description='Topic name of the 2D LaserScan input'
    )

    odom_topic_arg = DeclareLaunchArgument(
        'odom_topic',
        default_value='/rf2o/odom',
        description='Topic name of the output laser odometry'
    )

    base_frame_id_arg = DeclareLaunchArgument(
        'base_frame_id',
        default_value='base_footprint',
        description='Robot base reference coordinate frame'
    )

    odom_frame_id_arg = DeclareLaunchArgument(
        'odom_frame_id',
        default_value='odom',
        description='Odometry coordinate frame'
    )

    publish_tf_arg = DeclareLaunchArgument(
        'publish_tf',
        default_value='false',
        description='Whether to broadcast dynamic odom -> base_frame_id TF (must be false for S3 EKF)'
    )

    init_pose_from_topic_arg = DeclareLaunchArgument(
        'init_pose_from_topic',
        default_value='',
        description='Topic to initialize robot pose from ground truth (empty string disables)'
    )

    freq_arg = DeclareLaunchArgument(
        'freq',
        default_value='20.0',
        description='Execution and publication frequency (Hz)'
    )

    laser_scan_topic = LaunchConfiguration('laser_scan_topic')
    odom_topic = LaunchConfiguration('odom_topic')
    base_frame_id = LaunchConfiguration('base_frame_id')
    odom_frame_id = LaunchConfiguration('odom_frame_id')
    publish_tf = LaunchConfiguration('publish_tf')
    init_pose_from_topic = LaunchConfiguration('init_pose_from_topic')
    freq = LaunchConfiguration('freq')

    rf2o_node = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        name='rf2o_laser_odometry',
        output='screen',
        parameters=[{
            'laser_scan_topic': laser_scan_topic,
            'odom_topic': odom_topic,
            'base_frame_id': base_frame_id,
            'odom_frame_id': odom_frame_id,
            'publish_tf': publish_tf,
            'init_pose_from_topic': init_pose_from_topic,
            'freq': freq,
        }],
    )

    return LaunchDescription([
        params_file_arg,
        laser_scan_topic_arg,
        odom_topic_arg,
        base_frame_id_arg,
        odom_frame_id_arg,
        publish_tf_arg,
        init_pose_from_topic_arg,
        freq_arg,
        rf2o_node,
    ])
