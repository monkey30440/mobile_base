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

"""Compose the Kinematic-ICP PoC Mapping Mode launches."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import (
    AnyLaunchDescriptionSource,
    PythonLaunchDescriptionSource,
)
from launch.substitutions import LaunchConfiguration


def _python_launch(package_name, launch_file, launch_arguments=None):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory(package_name),
                'launch',
                launch_file,
            )
        ),
        launch_arguments=launch_arguments.items() if launch_arguments else None,
    )


def generate_launch_description():
    """Generate the Kinematic-ICP Mapping Mode orchestration description."""
    use_foxglove_arg = DeclareLaunchArgument(
        'use_foxglove',
        default_value='false',
        description='Start Foxglove Bridge for optional visualization',
    )
    lidar_odom_frame_arg = DeclareLaunchArgument(
        'lidar_odom_frame',
        default_value='odom',
        description='Odometry parent frame ID for Kinematic-ICP',
    )
    publish_odom_tf_arg = DeclareLaunchArgument(
        'publish_odom_tf',
        default_value='false',
        description='Whether Kinematic-ICP should publish odom TF',
    )
    invert_odom_tf_arg = DeclareLaunchArgument(
        'invert_odom_tf',
        default_value='false',
        description='Whether Kinematic-ICP should invert published odom TF',
    )
    lidar_topic_arg = DeclareLaunchArgument(
        'lidar_topic',
        default_value='/scan_front',
        description='Sensor topic for Kinematic-ICP',
    )
    wheel_odom_topic_arg = DeclareLaunchArgument(
        'wheel_odom_topic',
        default_value='/diff_drive_controller/odom',
        description='Wheel odometry input topic for Kinematic-ICP',
    )

    base_control = _python_launch(
        'mobile_base_control', 'base_control.launch.py'
    )
    tdk_imu = _python_launch(
        'mobile_base_perception', 'tdk_imu.launch.py'
    )
    sick_dual_lidar = _python_launch(
        'mobile_base_perception', 'sick_dual_lidar.launch.py'
    )
    dual_laser_merger = _python_launch(
        'mobile_base_perception', 'dual_laser_merger.launch.py'
    )
    kinematic_icp = _python_launch(
        'kinematic_icp',
        'kinematic_icp.launch.py',
        launch_arguments={
            'params_file': os.path.join(
                get_package_share_directory('kinematic_icp'),
                'config',
                'kinematic_icp_ros.yaml',
            ),
            'lidar_odom_frame': LaunchConfiguration('lidar_odom_frame'),
            'publish_odom_tf': LaunchConfiguration('publish_odom_tf'),
            'invert_odom_tf': LaunchConfiguration('invert_odom_tf'),
            'lidar_topic': LaunchConfiguration('lidar_topic'),
            'wheel_odom_topic': LaunchConfiguration('wheel_odom_topic'),
        },
    )
    ekf_kicp = _python_launch(
        'mobile_base_state_estimation', 'ekf_kinematic_icp.launch.py'
    )
    mapping = _python_launch(
        'mobile_base_mapping', 'mapping.launch.py'
    )

    foxglove = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('foxglove_bridge'),
                'launch',
                'foxglove_bridge_launch.xml',
            )
        ),
        condition=IfCondition(LaunchConfiguration('use_foxglove')),
    )

    return LaunchDescription([
        use_foxglove_arg,
        lidar_odom_frame_arg,
        publish_odom_tf_arg,
        invert_odom_tf_arg,
        lidar_topic_arg,
        wheel_odom_topic_arg,
        base_control,
        tdk_imu,
        sick_dual_lidar,
        dual_laser_merger,
        kinematic_icp,
        ekf_kicp,
        mapping,
        foxglove,
    ])
