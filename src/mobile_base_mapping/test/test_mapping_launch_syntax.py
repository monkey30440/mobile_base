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

"""Unit and syntax tests for S4 Mapping launch and slam_toolbox parameters."""

import importlib.util
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import LifecycleNode
import yaml


def _load_launch_module(launch_file_path: Path):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'mapping_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_slam_toolbox_yaml_configuration():
    """Verify that slam_toolbox.yaml matches authoritative S4 contracts."""
    pkg_dir = Path(__file__).resolve().parent.parent
    config_path = pkg_dir / 'config' / 'slam_toolbox.yaml'
    assert config_path.exists(), f'Configuration file not found: {config_path}'

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    assert 'async_slam_toolbox_node' in data
    params = data['async_slam_toolbox_node']['ros__parameters']

    # Mode and frame bindings
    assert params['mode'] == 'mapping'
    assert params['map_frame'] == 'map'
    assert params['odom_frame'] == 'odom'
    assert params['base_frame'] == 'base_footprint'
    assert params['scan_topic'] == '/scan_front'

    # Core resolution and TF rate
    assert params['resolution'] == 0.05
    assert params['max_laser_range'] == 20.0
    assert params['minimum_time_interval'] == 0.2
    assert params['transform_publish_period'] == 0.05

    # Scan matching and loop closure
    assert params['use_scan_matching'] is True
    assert params['do_loop_closing'] is True


def test_mapping_launch_description_generation():
    """Verify that mapping.launch.py generates valid launch actions."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'mapping.launch.py'
    assert launch_path.exists(), f'Launch file not found: {launch_path}'

    module = _load_launch_module(launch_path)
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription)

    declared_args = [
        action.name for action in ld.entities
        if isinstance(action, DeclareLaunchArgument)
    ]
    assert 'params_file' in declared_args

    node_actions = [
        action for action in ld.entities
        if isinstance(action, LifecycleNode)
    ]
    assert len(node_actions) == 1
    slam_node = node_actions[0]
    assert slam_node._Node__package == 'slam_toolbox'
    assert slam_node._Node__node_executable == 'async_slam_toolbox_node'
    assert slam_node._Node__node_name == 'async_slam_toolbox_node'
