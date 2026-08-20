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

"""Compose the validated real-hardware Mapping Mode launches."""

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


def _python_launch(package_name, launch_file):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory(package_name),
                'launch',
                launch_file,
            )
        )
    )


def generate_launch_description():
    """Generate the thin Mapping Mode orchestration description."""
    use_foxglove_arg = DeclareLaunchArgument(
        'use_foxglove',
        default_value='false',
        description='Start Foxglove Bridge for optional visualization',
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
    rf2o = _python_launch(
        'rf2o_laser_odometry', 'rf2o_laser_odometry.launch.py'
    )
    ekf = _python_launch(
        'mobile_base_state_estimation', 'ekf.launch.py'
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
        base_control,
        tdk_imu,
        sick_dual_lidar,
        dual_laser_merger,
        rf2o,
        ekf,
        mapping,
        foxglove,
    ])
