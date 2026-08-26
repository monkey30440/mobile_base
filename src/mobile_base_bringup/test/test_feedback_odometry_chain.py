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

"""Automated consolidated tests for Feedback and Odometry Chain (Checklist #22)."""

from pathlib import Path

import yaml


def get_workspace_root() -> Path:
    """Get the root directory of mobile_base workspace."""
    return Path(__file__).resolve().parent.parent.parent.parent


def test_m1_physical_feedback_contract():
    """Verify M1 physical feedback, state interfaces, and GAP-05 prohibition of substitution."""
    ws_root = get_workspace_root()

    # 1. URDF ros2_control Xacro state interface verification
    xacro_file = (
        ws_root / 'src' / 'mobile_base_description' / 'urdf' /
        'mobile_base_ros2_control.xacro'
    )
    assert xacro_file.exists(), f'File not found: {xacro_file}'
    with open(xacro_file, 'r', encoding='utf-8') as f:
        xacro_content = f.read()

    assert '<state_interface name="position"/>' in xacro_content
    assert '<state_interface name="velocity"/>' in xacro_content
    assert 'driving_wheel_joint_L' in xacro_content
    assert 'driving_wheel_joint_R' in xacro_content

    # 2. C++ source contract: M1Hardware read path and error handling (GAP-05 / SYS-029)
    cpp_source = (
        ws_root / 'src' / 'mobile_base_control' / 'src' / 'm1_hardware.cpp'
    )
    assert cpp_source.exists(), f'File not found: {cpp_source}'
    with open(cpp_source, 'r', encoding='utf-8') as f:
        cpp_content = f.read()

    assert 'driver_->read_state' in cpp_content
    assert 'hw_positions_[0]' in cpp_content
    assert 'hw_velocities_[0]' in cpp_content
    assert 'has_valid_state_' in cpp_content
    assert 'return_type::ERROR' in cpp_content


def test_wheel_odometry_contract():
    """Verify diff_drive_controller configuration, geometry, and odometry contract."""
    ws_root = get_workspace_root()
    ctrl_yaml = (
        ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml'
    )
    assert ctrl_yaml.exists(), f'File not found: {ctrl_yaml}'
    with open(ctrl_yaml, 'r', encoding='utf-8') as f:
        params = yaml.safe_load(f)['diff_drive_controller']['ros__parameters']

    # Joint names
    assert params['left_wheel_names'] == ['driving_wheel_joint_L']
    assert params['right_wheel_names'] == ['driving_wheel_joint_R']

    # Authoritative physical parameters
    assert params['wheel_separation'] == 0.5545
    assert params['wheel_radius'] == 0.080

    # Feedback and TF prohibitions
    assert params['enable_odom_tf'] is False
    assert params['position_feedback'] is True
    assert params['open_loop'] is False
    assert params['use_stamped_vel'] is True


def test_fused_odometry_ekf_contract():
    """Verify canonical Kinematic-ICP and IMU fusion plus sole TF authority."""
    ws_root = get_workspace_root()
    ekf_yaml = (
        ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    )
    assert ekf_yaml.exists(), f'File not found: {ekf_yaml}'
    with open(ekf_yaml, 'r', encoding='utf-8') as f:
        ekf_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']

    # Fused streams
    assert ekf_params['odom0'] == '/lidar_odometry'
    assert 'odom1' not in ekf_params
    assert ekf_params['imu0'] == '/imu/data_raw'

    # Frames and TF authority
    assert ekf_params['publish_tf'] is True
    assert ekf_params['map_frame'] == 'map'
    assert ekf_params['odom_frame'] == 'odom'
    assert ekf_params['base_link_frame'] == 'base_footprint'
    assert ekf_params['world_frame'] == 'odom'

    # Execution rate and freshness timeout
    assert ekf_params['frequency'] == 50.0
    assert ekf_params['sensor_timeout'] == 0.1
    assert ekf_params['two_d_mode'] is True


def test_tf_authority_odometry_prohibitions():
    """Verify neither diff-drive nor Kinematic-ICP publishes the EKF-owned TF."""
    ws_root = get_workspace_root()

    # 1. diff_drive_controller TF disabled
    ctrl_yaml = (
        ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml'
    )
    assert ctrl_yaml.exists()
    with open(ctrl_yaml, 'r', encoding='utf-8') as f:
        ctrl_params = yaml.safe_load(f)['diff_drive_controller']['ros__parameters']
    assert ctrl_params['enable_odom_tf'] is False

    # 2. Kinematic-ICP TF disabled
    kicp_yaml = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'config' /
        'kinematic_icp_ros.yaml'
    )
    assert kicp_yaml.exists(), f'File not found: {kicp_yaml}'
    with open(kicp_yaml, 'r', encoding='utf-8') as f:
        kicp_params = yaml.safe_load(f)['/**']['ros__parameters']
    assert kicp_params['publish_odom_tf'] is False
    assert kicp_params['lidar_odom_frame'] == 'odom'


def test_feedback_failure_and_stale_data_contract():
    """Verify stale data detection and timeout contracts across feedback and control layers."""
    ws_root = get_workspace_root()

    # 1. EKF sensor timeout (100 ms)
    ekf_yaml = (
        ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    )
    assert ekf_yaml.exists()
    with open(ekf_yaml, 'r', encoding='utf-8') as f:
        ekf_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    assert ekf_params['sensor_timeout'] == 0.1

    # 2. Base control command timeout (500 ms)
    ctrl_yaml = (
        ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml'
    )
    assert ctrl_yaml.exists()
    with open(ctrl_yaml, 'r', encoding='utf-8') as f:
        ctrl_params = yaml.safe_load(f)['diff_drive_controller']['ros__parameters']
    assert ctrl_params['cmd_vel_timeout'] == 0.5
