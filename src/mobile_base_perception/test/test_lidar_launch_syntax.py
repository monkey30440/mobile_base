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

"""Unit and syntax tests for S2 dual SICK picoScan150 LiDAR launch and configuration."""

import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import pytest


def _load_launch_module(launch_file_path: str):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'sick_dual_lidar_launch', launch_file_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launch_description_generation():
    """Verify sick_dual_lidar.launch.py builds valid LaunchDescription with 2 distinct nodes."""
    pkg_share = get_package_share_directory('mobile_base_perception')
    launch_file = os.path.join(pkg_share, 'launch', 'sick_dual_lidar.launch.py')

    module = _load_launch_module(launch_file)
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription), 'Generated object is not a LaunchDescription'

    node_actions = [a for a in ld.entities if isinstance(a, Node)]
    assert len(node_actions) == 2, f'Expected 2 Node actions, found {len(node_actions)}'

    node_names = {node._Node__node_name for node in node_actions}
    assert node_names == {'front_lidar_node', 'rear_lidar_node'}, f'Bad nodes: {node_names}'

    for node in node_actions:
        assert node._Node__package == 'sick_scan_xd', f'Node not sick_scan_xd: {node}'
        assert node._Node__node_executable == 'sick_generic_caller', f'Node not generic: {node}'

        argument_text = str(node._Node__arguments)
        assert 'imu_enable:=' in argument_text
        assert 'False' in argument_text
        assert 'start_sopas_service:=' in argument_text
        assert 'publish_laserscan_segment_topic:=' in argument_text
        assert 'custom_pointclouds:=' in argument_text
        assert '/sick_internal/' in argument_text
        assert "custom_pointclouds:=', 'none'" in argument_text
        assert 'tf_publish_rate:=' in argument_text
        assert '0.0' in argument_text

    # Verify no dual_laser_merger or static_transform_publisher is launched in #10
    forbidden_packages = {'dual_laser_merger', 'tf2_ros'}
    for node in node_actions:
        assert node._Node__package not in forbidden_packages


if __name__ == '__main__':
    pytest.main(['-v', __file__])
