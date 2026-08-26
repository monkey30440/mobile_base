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

"""Unit and syntax tests for rf2o_laser_odometry launch and parameter configuration."""

import importlib.util
from pathlib import Path

from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters


def _load_launch_module(launch_file_path: Path):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'rf2o_laser_odometry_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rf2o_launch_description_generation():
    """Verify that rf2o_laser_odometry.launch.py generates valid launch actions."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'rf2o_laser_odometry.launch.py'
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
    assert 'log_level' in declared_args

    # Inspect Node actions
    node_actions = [
        action for action in ld.entities
        if isinstance(action, Node)
    ]
    assert len(node_actions) == 1
    rf2o_node = node_actions[0]
    assert rf2o_node._Node__package == 'rf2o_laser_odometry'
    assert rf2o_node._Node__node_executable == 'rf2o_laser_odometry_node'
    assert rf2o_node._Node__node_name == 'rf2o_laser_odometry'
    argument_text = str(rf2o_node._Node__arguments)
    assert '--ros-args' in argument_text
    assert '--log-level' in argument_text
    assert 'rf2o_laser_odometry:=' in argument_text


def test_rf2o_uses_complete_inline_parameters():
    """Prevent shared params_file launch state from replacing RF2O contracts."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'rf2o_laser_odometry.launch.py'

    module = _load_launch_module(launch_path)
    ld = module.generate_launch_description()

    declared_args = {
        action.name for action in ld.entities
        if isinstance(action, DeclareLaunchArgument)
    }
    assert 'params_file' not in declared_args

    rf2o_node = next(
        action for action in ld.entities
        if isinstance(action, Node)
    )
    evaluated = evaluate_parameters(LaunchContext(), rf2o_node._Node__parameters)

    assert evaluated == ({
        'laser_scan_topic': '/scan_front',
        'odom_topic': '/rf2o/odom',
        'base_frame_id': 'base_footprint',
        'odom_frame_id': 'odom',
        'publish_tf': False,
        'init_pose_from_topic': '',
        'freq': 20.0,
    },)
