#!/usr/bin/env python3
# Copyright 2026 Jim Chen
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

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_description = get_package_share_directory('mobile_base_description')
    pkg_control = get_package_share_directory('mobile_base_control')

    default_params_file = os.path.join(pkg_control, 'config', 'base_control_params.yaml')

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true',
    )

    use_mock_hardware_arg = DeclareLaunchArgument(
        'use_mock_hardware',
        default_value='false',
        description='Use mock hardware plugin instead of real M1 hardware',
    )

    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for M1 motor drivers',
    )

    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='230400',
        description='Baud rate for M1 serial communication',
    )

    response_timeout_ms_arg = DeclareLaunchArgument(
        'response_timeout_ms',
        default_value='50',
        description='Response timeout in milliseconds (IMP-008 frozen runtime baseline: 50 ms)',
    )

    robot_description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_description, 'launch', 'robot_description.launch.py')
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'use_mock_hardware': LaunchConfiguration('use_mock_hardware'),
            'serial_port': LaunchConfiguration('serial_port'),
            'baud_rate': LaunchConfiguration('baud_rate'),
            'response_timeout_ms': LaunchConfiguration('response_timeout_ms'),
        }.items(),
    )

    control_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[default_params_file],
        output='both',
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager', '/controller_manager',
            '--controller-manager-timeout', '30',
        ],
        output='both',
    )

    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'diff_drive_controller',
            '--controller-manager', '/controller_manager',
            '--controller-manager-timeout', '30',
        ],
        output='both',
    )

    return LaunchDescription(
        [
            use_sim_time_arg,
            use_mock_hardware_arg,
            serial_port_arg,
            baud_rate_arg,
            response_timeout_ms_arg,
            robot_description_launch,
            control_node,
            joint_state_broadcaster_spawner,
            diff_drive_controller_spawner,
        ]
    )
