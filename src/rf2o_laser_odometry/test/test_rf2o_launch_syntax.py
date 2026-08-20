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
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile
import yaml


def _load_launch_module(launch_file_path: Path):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'rf2o_laser_odometry_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rf2o_yaml_configuration():
    """Verify that rf2o_laser_odometry.yaml matches authoritative S2/S3 contracts."""
    pkg_dir = Path(__file__).resolve().parent.parent
    config_path = pkg_dir / 'config' / 'rf2o_laser_odometry.yaml'
    assert config_path.exists(), f'Configuration file not found: {config_path}'

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    assert 'rf2o_laser_odometry' in data
    params = data['rf2o_laser_odometry']['ros__parameters']

    assert params['laser_scan_topic'] == '/scan'
    assert params['odom_topic'] == '/rf2o/odom'
    assert params['base_frame_id'] == 'base_footprint'
    assert params['odom_frame_id'] == 'odom'
    # Critical TF ownership check: RF2O must NOT publish odom -> base_footprint TF
    assert params['publish_tf'] is False
    assert params['freq'] == 20.0


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
    assert 'params_file' in declared_args
    assert len(declared_args) == 1

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
    parameters = rf2o_node._Node__parameters
    assert len(parameters) == 1
    assert isinstance(parameters[0], ParameterFile)
    parameter_file_substitutions = parameters[0]._ParameterFile__param_file
    assert len(parameter_file_substitutions) == 1
    assert isinstance(parameter_file_substitutions[0], LaunchConfiguration)
    variable_name = parameter_file_substitutions[0]._LaunchConfiguration__variable_name
    assert len(variable_name) == 1
    assert variable_name[0].perform(LaunchContext()) == 'params_file'
