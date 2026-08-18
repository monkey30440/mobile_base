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
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_description = get_package_share_directory('mobile_base_description')
    default_model_path = os.path.join(pkg_description, 'urdf', 'mobile_base.urdf.xacro')

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true',
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
        description='Response timeout in milliseconds (required parameter, no implicit default)',
    )

    publish_frequency_arg = DeclareLaunchArgument(
        'publish_frequency',
        default_value='30.0',
        description='Publishing frequency of robot_state_publisher (Hz)',
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name='xacro')]),
            ' ',
            default_model_path,
            ' ',
            'use_mock_hardware:=',
            LaunchConfiguration('use_mock_hardware'),
            ' ',
            'serial_port:=',
            LaunchConfiguration('serial_port'),
            ' ',
            'baud_rate:=',
            LaunchConfiguration('baud_rate'),
            ' ',
            'response_timeout_ms:=',
            LaunchConfiguration('response_timeout_ms'),
        ]
    )

    robot_description = ParameterValue(robot_description_content, value_type=str)

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[
            {
                'robot_description': robot_description,
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'publish_frequency': LaunchConfiguration('publish_frequency'),
            }
        ],
    )

    return LaunchDescription(
        [
            use_sim_time_arg,
            use_mock_hardware_arg,
            serial_port_arg,
            baud_rate_arg,
            response_timeout_ms_arg,
            publish_frequency_arg,
            robot_state_publisher_node,
        ]
    )
