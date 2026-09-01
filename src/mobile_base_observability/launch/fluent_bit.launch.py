# Copyright 2026 FIH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Launch Fluent Bit as an independent AMR-side observability process."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess


def generate_launch_description():
    """Start Fluent Bit with the package-owned client configuration."""
    config_path = os.path.join(
        get_package_share_directory('mobile_base_observability'),
        'config',
        'fluent-bit.conf',
    )
    fluent_bit = ExecuteProcess(
        cmd=['/opt/fluent-bit/bin/fluent-bit', '-c', config_path],
        name='mobile_base_fluent_bit',
        output='screen',
    )
    return LaunchDescription([fluent_bit])
