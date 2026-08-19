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

"""Unit and syntax tests for S2 dual_laser_merger launch and parameter configurations."""

import importlib.util
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
import yaml


def _load_launch_module(launch_file_path: Path):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'dual_laser_merger_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dual_laser_merger_yaml_configuration():
    """Verify that dual_laser_merger.yaml matches authoritative S2 contracts."""
    pkg_dir = Path(__file__).resolve().parent.parent
    config_path = pkg_dir / 'config' / 'dual_laser_merger.yaml'
    assert config_path.exists(), f'Configuration file not found: {config_path}'

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    assert 'dual_laser_merger_node' in data
    params = data['dual_laser_merger_node']['ros__parameters']

    assert params['laser_1_topic'] == '/scan_front'
    assert params['laser_2_topic'] == '/scan_rear'
    assert params['target_frame'] == 'base_link'
    assert params['merged_scan_topic'] == '/scan'
    assert params['range_min'] == 0.05
    assert params['range_max'] == 25.0
    assert params['min_height'] == -1.0
    assert params['max_height'] == 1.0
    assert params['use_inf'] is True


def test_dual_laser_merger_launch_description_generation():
    """Verify that dual_laser_merger.launch.py generates valid launch actions."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'dual_laser_merger.launch.py'
    assert launch_path.exists(), f'Launch file not found: {launch_path}'

    module = _load_launch_module(launch_path)
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription)

    # Inspect declared launch arguments
    declared_args = [
        action.name for action in ld.entities
        if isinstance(action, DeclareLaunchArgument)
    ]
    assert 'params_file' in declared_args
    assert 'laser_1_topic' in declared_args
    assert 'laser_2_topic' in declared_args
    assert 'target_frame' in declared_args
    assert 'merged_scan_topic' in declared_args

    # Inspect Node actions
    node_actions = [
        action for action in ld.entities
        if isinstance(action, Node)
    ]
    assert len(node_actions) == 1
    merger_node = node_actions[0]
    assert merger_node._Node__package == 'dual_laser_merger'
    assert merger_node._Node__node_executable == 'dual_laser_merger_node'
    assert merger_node._Node__node_name == 'dual_laser_merger_node'
