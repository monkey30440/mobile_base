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

"""Unit and syntax tests for S2 dual SICK LiDAR launch and configuration."""

import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import pytest
import yaml


def _load_launch_module(launch_file_path: str):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'sick_dual_lidar_launch', launch_file_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_package_and_configs_installed():
    """Verify package share directory and config files exist."""
    pkg_share = get_package_share_directory('mobile_base_perception')
    assert os.path.isdir(pkg_share), f'Package share missing: {pkg_share}'

    front_cfg = os.path.join(pkg_share, 'config', 'sick_front_lidar.yaml')
    rear_cfg = os.path.join(pkg_share, 'config', 'sick_rear_lidar.yaml')
    launch_file = os.path.join(pkg_share, 'launch', 'sick_dual_lidar.launch.py')

    assert os.path.isfile(front_cfg), f'Missing front lidar config: {front_cfg}'
    assert os.path.isfile(rear_cfg), f'Missing rear lidar config: {rear_cfg}'
    assert os.path.isfile(launch_file), f'Missing launch file: {launch_file}'


def test_yaml_configs_syntax_and_values():
    """Validate YAML parsing and parameter contracts for FL and BR LiDARs."""
    pkg_share = get_package_share_directory('mobile_base_perception')
    front_cfg = os.path.join(pkg_share, 'config', 'sick_front_lidar.yaml')
    rear_cfg = os.path.join(pkg_share, 'config', 'sick_rear_lidar.yaml')

    with open(front_cfg, 'r') as f:
        fl_data = yaml.safe_load(f)

    with open(rear_cfg, 'r') as f:
        br_data = yaml.safe_load(f)

    assert 'front_lidar_node' in fl_data, 'front_lidar_node missing in FL config'
    assert 'rear_lidar_node' in br_data, 'rear_lidar_node missing in BR config'

    fl_params = fl_data['front_lidar_node']['ros__parameters']
    br_params = br_data['rear_lidar_node']['ros__parameters']

    # Contract checks for Front-Left
    assert fl_params['hostname'] == '192.168.0.1'
    assert fl_params['frame_id'] == 'base_lidar_link_FL'
    assert fl_params['laserscan_topic'] == '/scan_front'
    assert fl_params['tf_publish_rate'] == 0.0, 'FL TF publish must be 0.0'
    assert fl_params['ros_qos'] == 4, 'FL QoS must be SensorDataQoS (4)'

    # Contract checks for Rear-Right
    assert br_params['hostname'] == '192.168.0.2'
    assert br_params['frame_id'] == 'base_lidar_link_BR'
    assert br_params['laserscan_topic'] == '/scan_rear'
    assert br_params['tf_publish_rate'] == 0.0, 'BR TF publish must be 0.0'
    assert br_params['ros_qos'] == 4, 'BR QoS must be SensorDataQoS (4)'

    # Isolation check: FL and BR must have distinct IP, frame, and topic
    assert fl_params['hostname'] != br_params['hostname']
    assert fl_params['frame_id'] != br_params['frame_id']
    assert fl_params['laserscan_topic'] != br_params['laserscan_topic']


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

    # Verify no dual_laser_merger or static_transform_publisher is launched in #10
    forbidden_packages = {'dual_laser_merger', 'tf2_ros'}
    for node in node_actions:
        assert node._Node__package not in forbidden_packages


if __name__ == '__main__':
    pytest.main(['-v', __file__])
