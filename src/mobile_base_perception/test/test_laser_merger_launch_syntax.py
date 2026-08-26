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

from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters


def _load_launch_module(launch_file_path: Path):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'dual_laser_merger_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    assert 'params_file' not in declared_args
    assert 'laser_1_topic' in declared_args
    assert 'laser_2_topic' in declared_args
    assert 'target_frame' in declared_args
    assert 'merged_scan_topic' in declared_args

    # Inspect Node actions
    node_actions = [
        action for action in ld.entities
        if isinstance(action, Node)
    ]
    assert len(node_actions) == 2
    node_names = {n._Node__node_name for n in node_actions}
    assert 'dual_laser_merger_node' in node_names
    assert 'collision_scan_filter' in node_names

    merger_node = next(n for n in node_actions if n._Node__node_name == 'dual_laser_merger_node')
    assert merger_node._Node__package == 'dual_laser_merger'
    assert merger_node._Node__node_executable == 'dual_laser_merger_node'


def test_dual_laser_merger_uses_complete_inline_parameters():
    """Prevent shared params_file launch state from replacing merger settings."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'dual_laser_merger.launch.py'

    module = _load_launch_module(launch_path)
    ld = module.generate_launch_description()

    declared_args = {
        action.name for action in ld.entities
        if isinstance(action, DeclareLaunchArgument)
    }
    assert 'params_file' not in declared_args

    merger_node = next(
        action for action in ld.entities
        if isinstance(action, Node)
    )
    context = LaunchContext()
    context.launch_configurations.update({
        'laser_1_topic': '/scan_front',
        'laser_2_topic': '/scan_rear',
        'target_frame': 'base_link',
        'merged_scan_topic': '/scan',
    })
    evaluated = evaluate_parameters(context, merger_node._Node__parameters)

    assert len(evaluated) == 1
    assert isinstance(evaluated[0], dict)
    assert evaluated[0]['laser_1_topic'] == '/scan_front'
    assert evaluated[0]['laser_2_topic'] == '/scan_rear'
    assert evaluated[0]['target_frame'] == 'base_link'
    assert evaluated[0]['merged_scan_topic'] == '/scan'
    assert evaluated[0]['merged_cloud_topic'] == '/sick_internal/merged_cloud'
    assert evaluated[0]['angle_increment'] == 0.0058171823974636
    assert evaluated[0]['range_max'] == 25.0
    assert evaluated[0]['min_height'] == -1.0
    assert evaluated[0]['max_height'] == 1.0
    assert evaluated[0]['allowed_radius'] == 0.20
