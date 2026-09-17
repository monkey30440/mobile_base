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

"""
Compatibility wrapper for Mapping Mode bringup.

Delegates to canonical mobile_base.launch.py with mode:=mapping.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """Generate mapping launch description via canonical mobile_base.launch.py."""
    pkg_share = get_package_share_directory('mobile_base_bringup')
    canonical_launch = os.path.join(pkg_share, 'launch', 'mobile_base.launch.py')

    use_foxglove_arg = DeclareLaunchArgument(
        'use_foxglove',
        default_value='false',
        description='Start Foxglove Bridge for optional visualization',
    )

    include_canonical = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(canonical_launch),
        launch_arguments={
            'mode': 'mapping',
            'platform': 'real',
            'variant': 'default',
            'use_foxglove': LaunchConfiguration('use_foxglove'),
        }.items(),
    )

    return LaunchDescription([
        use_foxglove_arg,
        include_canonical,
    ])
