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

"""Launch the standalone ROS observability adapter."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Create the standalone adapter launch description."""
    arguments = [
        DeclareLaunchArgument(
            'influxdb_url',
            default_value=EnvironmentVariable(
                'MOBILE_BASE_INFLUXDB_URL', default_value=''
            ),
        ),
        DeclareLaunchArgument(
            'influxdb_organization',
            default_value=EnvironmentVariable(
                'MOBILE_BASE_INFLUXDB_ORGANIZATION', default_value=''
            ),
        ),
        DeclareLaunchArgument(
            'influxdb_bucket',
            default_value=EnvironmentVariable(
                'MOBILE_BASE_INFLUXDB_BUCKET', default_value=''
            ),
        ),
        DeclareLaunchArgument(
            'robot_id',
            default_value=EnvironmentVariable(
                'MOBILE_BASE_ROBOT_ID', default_value=''
            ),
        ),
        DeclareLaunchArgument(
            'diagnostic_status_name',
            default_value=EnvironmentVariable(
                'MOBILE_BASE_DIAGNOSTIC_STATUS_NAME',
                default_value=(
                    'controller_manager: Hardware Components Activity'
                ),
            ),
        ),
        DeclareLaunchArgument('sample_rate_hz', default_value='1.0'),
        DeclareLaunchArgument('queue_capacity', default_value='60'),
        DeclareLaunchArgument('http_timeout_seconds', default_value='2.0'),
    ]
    adapter = Node(
        package='mobile_base_observability',
        executable='observability_adapter',
        name='ros_observability_adapter',
        output='screen',
        parameters=[{
            'influxdb_url': LaunchConfiguration('influxdb_url'),
            'influxdb_organization': LaunchConfiguration('influxdb_organization'),
            'influxdb_bucket': LaunchConfiguration('influxdb_bucket'),
            'robot_id': LaunchConfiguration('robot_id'),
            'diagnostic_status_name': LaunchConfiguration(
                'diagnostic_status_name'
            ),
            'sample_rate_hz': ParameterValue(
                LaunchConfiguration('sample_rate_hz'), value_type=float
            ),
            'queue_capacity': ParameterValue(
                LaunchConfiguration('queue_capacity'), value_type=int
            ),
            'http_timeout_seconds': ParameterValue(
                LaunchConfiguration('http_timeout_seconds'), value_type=float
            ),
        }],
    )
    return LaunchDescription(arguments + [adapter])
