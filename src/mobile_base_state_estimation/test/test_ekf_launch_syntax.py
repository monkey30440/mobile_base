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

"""Unit and syntax tests for S3 State Estimation EKF launch and parameter configurations."""

import importlib.util
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters
import yaml


def _load_launch_module(launch_file_path: Path):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'ekf_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ekf_yaml_configuration():
    """Verify that ekf.yaml matches authoritative S3 contracts."""
    pkg_dir = Path(__file__).resolve().parent.parent
    config_path = pkg_dir / 'config' / 'ekf.yaml'
    assert config_path.exists(), f'Configuration file not found: {config_path}'

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    assert 'ekf_filter_node' in data
    params = data['ekf_filter_node']['ros__parameters']

    # Core EKF parameters
    assert params['frequency'] == 50.0
    assert params['sensor_timeout'] == 0.1
    assert params['two_d_mode'] is True
    assert params['publish_tf'] is True
    assert params['world_frame'] == 'odom'
    assert params['odom_frame'] == 'odom'
    assert params['base_link_frame'] == 'base_footprint'
    assert params['map_frame'] == 'map'

    # odom0 (wheel odometry)
    assert params['odom0'] == '/diff_drive_controller/odom'
    expected_odom0_config = [
        False, False, False,
        False, False, False,
        True,  True,  False,
        False, False, True,
        False, False, False
    ]
    assert params['odom0_config'] == expected_odom0_config

    # odom1 (RF2O laser odometry)
    assert params['odom1'] == '/rf2o/odom'
    expected_odom1_config = [
        False, False, False,
        False, False, False,
        True,  True,  False,
        False, False, True,
        False, False, False
    ]
    assert params['odom1_config'] == expected_odom1_config

    # imu0 (TDK IMU) - yaw rate only; orientation and acceleration excluded
    assert params['imu0'] == '/imu/data_raw'
    expected_imu0_config = [
        False, False, False,
        False, False, False,
        False, False, False,
        False, False, True,
        False, False, False
    ]
    assert params['imu0_config'] == expected_imu0_config
    assert params['imu0_remove_gravitational_acceleration'] is True


def test_ekf_launch_description_generation():
    """Verify that ekf.launch.py generates valid launch actions."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'ekf.launch.py'
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

    # Inspect Node actions
    node_actions = [
        action for action in ld.entities
        if isinstance(action, Node)
    ]
    assert len(node_actions) == 1
    ekf_node = node_actions[0]
    assert ekf_node._Node__package == 'robot_localization'
    assert ekf_node._Node__node_executable == 'ekf_node'
    assert ekf_node._Node__node_name == 'ekf_filter_node'


def test_ekf_loads_own_parameters_without_shared_launch_state():
    """Prevent another child launch from replacing the EKF parameter file."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'ekf.launch.py'

    module = _load_launch_module(launch_path)
    ld = module.generate_launch_description()

    declared_args = {
        action.name for action in ld.entities
        if isinstance(action, DeclareLaunchArgument)
    }
    assert 'params_file' not in declared_args

    ekf_node = next(
        action for action in ld.entities
        if isinstance(action, Node)
    )
    evaluated = evaluate_parameters(LaunchContext(), ekf_node._Node__parameters)

    expected_path = (
        Path(get_package_share_directory('mobile_base_state_estimation'))
        / 'config'
        / 'ekf.yaml'
    )
    assert evaluated == (expected_path,)


def test_ekf_kinematic_icp_yaml_configuration():
    """Verify that ekf_kinematic_icp.yaml matches authoritative S3 contracts."""
    pkg_dir = Path(__file__).resolve().parent.parent
    config_path = pkg_dir / 'config' / 'ekf_kinematic_icp.yaml'
    assert config_path.exists(), f'Configuration file not found: {config_path}'

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    assert 'ekf_filter_node' in data
    params = data['ekf_filter_node']['ros__parameters']

    # Core EKF parameters
    assert params['frequency'] == 50.0
    assert params['sensor_timeout'] == 0.1
    assert params['two_d_mode'] is True
    assert params['publish_tf'] is True
    assert params['world_frame'] == 'odom'
    assert params['odom_frame'] == 'odom'
    assert params['base_link_frame'] == 'base_footprint'
    assert params['map_frame'] == 'map'

    # odom0 (Kinematic-ICP laser odometry) - x, y, yaw
    assert params['odom0'] == '/lidar_odometry'
    expected_odom0_config = [
        True,  True,  False,
        False, False, True,
        False, False, False,
        False, False, False,
        False, False, False
    ]
    assert params['odom0_config'] == expected_odom0_config

    # imu0 (TDK IMU) - yaw rate only; orientation and acceleration excluded
    assert params['imu0'] == '/imu/data_raw'
    expected_imu0_config = [
        False, False, False,
        False, False, False,
        False, False, False,
        False, False, True,
        False, False, False
    ]
    assert params['imu0_config'] == expected_imu0_config
    assert params['imu0_remove_gravitational_acceleration'] is True


def test_ekf_kinematic_icp_launch_description_generation():
    """Verify that ekf_kinematic_icp.launch.py generates valid launch actions."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'ekf_kinematic_icp.launch.py'
    assert launch_path.exists(), f'Launch file not found: {launch_path}'

    module = _load_launch_module(launch_path)
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription)

    node_actions = [
        action for action in ld.entities
        if isinstance(action, Node)
    ]
    assert len(node_actions) == 1
    ekf_node = node_actions[0]
    assert ekf_node._Node__package == 'robot_localization'
    assert ekf_node._Node__node_executable == 'ekf_node'
    assert ekf_node._Node__node_name == 'ekf_filter_node'
