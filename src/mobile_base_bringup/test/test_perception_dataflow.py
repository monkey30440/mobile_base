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

"""Automated consolidated tests for Perception Data Flow (Checklist #20)."""

from pathlib import Path

import yaml


def get_workspace_root() -> Path:
    """Get the root directory of mobile_base workspace."""
    return Path(__file__).resolve().parent.parent.parent.parent


def test_front_lidar_data_contract():
    """Verify Front LiDAR driver launch parameters, topic, frame, and consumer."""
    ws_root = get_workspace_root()
    launch_path = (
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'sick_dual_lidar.launch.py'
    )
    assert launch_path.exists(), f'File not found: {launch_path}'

    with open(launch_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verify Producer node, topic, and frame contract
    assert "package='sick_scan_xd'" in content or 'package="sick_scan_xd"' in content
    assert "'front_topic'" in content
    assert "'front_frame_id'" in content
    assert "default_value='/scan_front'" in content
    assert "default_value='base_lidar_link_FL'" in content

    # Verify Consumer in dual_laser_merger
    merger_launch = (
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'dual_laser_merger.launch.py'
    )
    assert merger_launch.exists()
    with open(merger_launch, 'r', encoding='utf-8') as f:
        merger_content = f.read()

    assert (
        "'laser_1_topic', default_value='/scan_front'" in merger_content or
        "default_value='/scan_front'" in merger_content
    )


def test_rear_lidar_data_contract():
    """Verify Rear LiDAR driver launch parameters, topic, frame, and consumer."""
    ws_root = get_workspace_root()
    launch_path = (
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'sick_dual_lidar.launch.py'
    )
    assert launch_path.exists()

    with open(launch_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verify Producer node, topic, and frame contract
    assert "'rear_topic'" in content
    assert "'rear_frame_id'" in content
    assert "default_value='/scan_rear'" in content
    assert "default_value='base_lidar_link_BR'" in content

    # Verify Consumer in dual_laser_merger
    merger_launch = (
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'dual_laser_merger.launch.py'
    )
    assert merger_launch.exists()
    with open(merger_launch, 'r', encoding='utf-8') as f:
        merger_content = f.read()

    assert (
        "'laser_2_topic', default_value='/scan_rear'" in merger_content or
        "default_value='/scan_rear'" in merger_content
    )


def test_merged_scan_data_contract_and_consumers():
    """Verify merged scan remains wired to mapping, localization, and Nav2."""
    ws_root = get_workspace_root()

    # 1. Producer: dual_laser_merger
    merger_launch = (
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'dual_laser_merger.launch.py'
    )
    assert merger_launch.exists()
    with open(merger_launch, 'r', encoding='utf-8') as f:
        merger_content = f.read()

    assert "default_value='base_link'" in merger_content
    assert "default_value='/scan'" in merger_content

    # 2. Consumer: S4 slam_toolbox (Mapping Mode)
    slam_config = ws_root / 'src' / 'mobile_base_mapping' / 'config' / 'slam_toolbox.yaml'
    assert slam_config.exists()
    with open(slam_config, 'r', encoding='utf-8') as f:
        slam_params = yaml.safe_load(f)['async_slam_toolbox_node']['ros__parameters']
    assert slam_params['scan_topic'] == '/scan'

    # 3. Consumer: S5 AMCL (Navigation Mode)
    amcl_config = ws_root / 'src' / 'mobile_base_localization' / 'config' / 'amcl_params.yaml'
    assert amcl_config.exists()
    with open(amcl_config, 'r', encoding='utf-8') as f:
        amcl_params = yaml.safe_load(f)['amcl']['ros__parameters']
    assert amcl_params['scan_topic'] == '/scan'

    # 4. Consumers: S6 Local/Global Costmaps and Collision Monitor
    nav2_config = ws_root / 'src' / 'mobile_base_navigation' / 'config' / 'nav2_params.yaml'
    assert nav2_config.exists()
    with open(nav2_config, 'r', encoding='utf-8') as f:
        nav2_params = yaml.safe_load(f)

    # Local costmap scan subscription
    local_scan = (
        nav2_params['local_costmap']['local_costmap']['ros__parameters']
        ['obstacle_layer']['scan']['topic']
    )
    assert local_scan == '/scan'

    # Global costmap scan subscription
    global_scan = (
        nav2_params['global_costmap']['global_costmap']['ros__parameters']
        ['obstacle_layer']['scan']['topic']
    )
    assert global_scan == '/scan'

    # Collision monitor scan subscription
    cm_scan = nav2_params['collision_monitor']['ros__parameters']['scan']['topic']
    assert cm_scan == '/scan'


def test_imu_data_contract_and_ekf_consumer():
    """Verify TDK IMU driver launch parameters, frame, and EKF consumer."""
    ws_root = get_workspace_root()

    # 1. IMU Driver config and launch
    imu_yaml = ws_root / 'src' / 'mobile_base_perception' / 'config' / 'tdk_imu.yaml'
    assert imu_yaml.exists()
    with open(imu_yaml, 'r', encoding='utf-8') as f:
        imu_params = yaml.safe_load(f)['imu_driver_node']['ros__parameters']
    assert imu_params['frame_id'] == 'base_imu_link'

    imu_launch = ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'tdk_imu.launch.py'
    assert imu_launch.exists()
    with open(imu_launch, 'r', encoding='utf-8') as f:
        imu_content = f.read()
    assert "default_value='/imu/data_raw'" in imu_content
    assert "('/tdk/imu', imu_topic)" in imu_content

    # 2. Consumer in S3 robot_localization EKF
    ekf_yaml = ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    assert ekf_yaml.exists()
    with open(ekf_yaml, 'r', encoding='utf-8') as f:
        ekf_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    assert ekf_params['imu0'] == '/imu/data_raw'
    # IMU orientation strictly excluded from 2D planar fusion
    assert ekf_params['imu0_config'][3:6] == [False, False, False]
    # IMU yaw rate (vyaw) and linear acceleration (ax) fused
    assert ekf_params['imu0_config'][11] is True  # vyaw
    assert ekf_params['imu0_config'][12] is True  # ax


def test_rf2o_laser_odometry_contract_and_ekf_consumer():
    """Verify RF2O uses the front physical scan and retains its EKF interface."""
    ws_root = get_workspace_root()

    # 1. RF2O Launch configuration
    rf2o_launch = (
        ws_root / 'src' / 'rf2o_laser_odometry' / 'launch' / 'rf2o_laser_odometry.launch.py'
    )
    assert rf2o_launch.exists()
    with open(rf2o_launch, 'r', encoding='utf-8') as f:
        rf2o_content = f.read()

    assert "'laser_scan_topic': '/scan_front'" in rf2o_content
    assert "'laser_scan_topic': '/scan'" not in rf2o_content
    assert "'odom_topic': '/rf2o/odom'" in rf2o_content
    assert "'base_frame_id': 'base_footprint'" in rf2o_content
    assert "'odom_frame_id': 'odom'" in rf2o_content
    assert "'publish_tf': False" in rf2o_content or '"publish_tf": False' in rf2o_content

    # 2. Consumer in S3 robot_localization EKF
    ekf_yaml = ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    assert ekf_yaml.exists()
    with open(ekf_yaml, 'r', encoding='utf-8') as f:
        ekf_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    assert ekf_params['odom1'] == '/rf2o/odom'
    # RF2O planar velocities fused (vx, vy, yaw_rate)
    assert ekf_params['odom1_config'][6] is True   # vx
    assert ekf_params['odom1_config'][7] is True   # vy
    assert ekf_params['odom1_config'][11] is True  # vyaw


def test_freshness_and_timeout_configurations():
    """Verify sensor freshness and timeout thresholds across S3, S6, and S7."""
    ws_root = get_workspace_root()

    # 1. S3 EKF sensor timeout (100 ms)
    ekf_yaml = ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    assert ekf_yaml.exists()
    with open(ekf_yaml, 'r', encoding='utf-8') as f:
        ekf_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    assert ekf_params['sensor_timeout'] == 0.1

    # 2. S6 Collision Monitor scan source timeout
    nav2_yaml = ws_root / 'src' / 'mobile_base_navigation' / 'config' / 'nav2_params.yaml'
    assert nav2_yaml.exists()
    with open(nav2_yaml, 'r', encoding='utf-8') as f:
        nav2_params = yaml.safe_load(f)
    cm_timeout = nav2_params['collision_monitor']['ros__parameters']['scan']['source_timeout']
    assert cm_timeout >= 0.5

    # 3. S7 diff_drive_controller command timeout (500 ms)
    ctrl_yaml = ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml'
    assert ctrl_yaml.exists()
    with open(ctrl_yaml, 'r', encoding='utf-8') as f:
        ctrl_params = yaml.safe_load(f)['diff_drive_controller']['ros__parameters']
    assert ctrl_params['cmd_vel_timeout'] == 0.5
