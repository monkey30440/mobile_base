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

"""Unit and syntax tests for S2 TDK IMU launch and configuration."""

import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch_ros.actions import Node
import pytest
import yaml


def _load_launch_module(launch_file_path: str):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'tdk_imu_launch', launch_file_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_package_and_configs_installed():
    """Verify package share directory and config files exist."""
    pkg_share = get_package_share_directory('mobile_base_perception')
    assert os.path.isdir(pkg_share), f'Package share missing: {pkg_share}'

    imu_cfg = os.path.join(pkg_share, 'config', 'tdk_imu.yaml')
    launch_file = os.path.join(pkg_share, 'launch', 'tdk_imu.launch.py')

    assert os.path.isfile(imu_cfg), f'Missing IMU config: {imu_cfg}'
    assert os.path.isfile(launch_file), f'Missing launch file: {launch_file}'


def test_yaml_config_contract():
    """Validate YAML parsing and parameter contracts for TDK IMU."""
    pkg_share = get_package_share_directory('mobile_base_perception')
    imu_cfg = os.path.join(pkg_share, 'config', 'tdk_imu.yaml')

    with open(imu_cfg, 'r') as f:
        cfg_data = yaml.safe_load(f)

    assert 'imu_driver_node' in cfg_data, 'imu_driver_node missing in config'
    params = cfg_data['imu_driver_node']['ros__parameters']

    assert params['port'] == '/dev/ttyACM0'
    assert params['baud_rate'] == 115200
    assert params['frame_id'] == 'base_imu_link'


def test_launch_description_generation():
    """Verify tdk_imu.launch.py builds valid LaunchDescription with imu_driver_node."""
    pkg_share = get_package_share_directory('mobile_base_perception')
    launch_file = os.path.join(pkg_share, 'launch', 'tdk_imu.launch.py')

    module = _load_launch_module(launch_file)
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription), 'Generated object is not a LaunchDescription'

    node_actions = [a for a in ld.entities if isinstance(a, Node)]
    assert len(node_actions) == 1, f'Expected 1 Node action, found {len(node_actions)}'

    imu_node = node_actions[0]
    assert imu_node._Node__package == 'tdk_ros2_imu'
    assert imu_node._Node__node_executable == 'tdk_imu_node'
    assert imu_node._Node__node_name == 'imu_driver_node'

    remappings = imu_node._Node__remappings
    assert len(remappings) == 1
    context = LaunchContext()
    src_str = ''.join([s.perform(context) for s in remappings[0][0]])
    assert src_str == '/tdk/imu'


if __name__ == '__main__':
    pytest.main(['-v', __file__])
