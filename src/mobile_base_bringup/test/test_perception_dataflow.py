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
    """Verify Front LiDAR driver launch parameters, topic, frame, and consumers."""
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


def test_rear_lidar_data_contract():
    """Verify Rear LiDAR driver launch parameters, topic, frame, and consumers."""
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


def test_lidar_routing_contracts_a_through_e():
    """Verify independent LiDAR routing contracts A through E."""
    ws_root = get_workspace_root()

    # Requirement A: slam_toolbox scan_topic == /scan_front
    slam_config = ws_root / 'src' / 'mobile_base_mapping' / 'config' / 'slam_toolbox.yaml'
    assert slam_config.exists()
    with open(slam_config, 'r', encoding='utf-8') as f:
        slam_params = yaml.safe_load(f)['async_slam_toolbox_node']['ros__parameters']
    assert slam_params['scan_topic'] == '/scan_front'

    # Requirement B: kinematic_icp lidar_topic == /scan_front
    kicp_config = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'config' / 'kinematic_icp_ros.yaml'
    )
    assert kicp_config.exists()
    with open(kicp_config, 'r', encoding='utf-8') as f:
        kicp_params = yaml.safe_load(f)['/**']['ros__parameters']
    assert kicp_params['lidar_topic'] == '/scan_front'

    # Requirements C, D, E: Nav2 local/global costmaps and collision_monitor
    nav2_config = ws_root / 'src' / 'mobile_base_navigation' / 'config' / 'nav2_params.yaml'
    assert nav2_config.exists()
    with open(nav2_config, 'r', encoding='utf-8') as f:
        nav2_params = yaml.safe_load(f)

    # Requirement C: Nav2 local costmap observation_sources contains scan_front and scan_rear
    lc_obstacle = (
        nav2_params['local_costmap']['local_costmap']['ros__parameters']
        ['obstacle_layer']
    )
    assert 'scan_front' in lc_obstacle['observation_sources']
    assert 'scan_rear' in lc_obstacle['observation_sources']
    assert lc_obstacle['scan_front']['topic'] == '/scan_front'
    assert lc_obstacle['scan_rear']['topic'] == '/scan_rear'

    # Requirement D: Nav2 global costmap observation_sources contains scan_front and scan_rear
    gc_obstacle = (
        nav2_params['global_costmap']['global_costmap']['ros__parameters']
        ['obstacle_layer']
    )
    assert 'scan_front' in gc_obstacle['observation_sources']
    assert 'scan_rear' in gc_obstacle['observation_sources']
    assert gc_obstacle['scan_front']['topic'] == '/scan_front'
    assert gc_obstacle['scan_rear']['topic'] == '/scan_rear'

    # Requirement E: collision_monitor observation_sources contains scan_front and scan_rear
    cm_params = nav2_params['collision_monitor']['ros__parameters']
    assert 'scan_front' in cm_params['observation_sources']
    assert 'scan_rear' in cm_params['observation_sources']
    assert cm_params['scan_front']['topic'] == '/scan_front'
    assert cm_params['scan_rear']['topic'] == '/scan_rear'
    assert cm_params['scan_front']['type'] == 'scan'
    assert cm_params['scan_rear']['type'] == 'scan'

    # S5 AMCL scan_topic == /scan_front
    amcl_config = ws_root / 'src' / 'mobile_base_localization' / 'config' / 'amcl_params.yaml'
    assert amcl_config.exists()
    with open(amcl_config, 'r', encoding='utf-8') as f:
        amcl_params = yaml.safe_load(f)['amcl']['ros__parameters']
    assert amcl_params['scan_topic'] == '/scan_front'


def test_no_production_runtime_reliance_on_merged_or_filtered_scan():
    """Verify production launch and configs do not rely on /scan or /scan_collision (Req F)."""
    ws_root = get_workspace_root()

    production_yaml_files = [
        ws_root / 'src' / 'mobile_base_mapping' / 'config' / 'slam_toolbox.yaml',
        ws_root / 'src' / 'mobile_base_localization' / 'config' / 'amcl_params.yaml',
        ws_root / 'src' / 'mobile_base_navigation' / 'config' / 'nav2_params.yaml',
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'config' / 'kinematic_icp_ros.yaml',
        ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml',
        ws_root / 'src' / 'mobile_base_perception' / 'config' / 'tdk_imu.yaml',
        ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml',
    ]

    def _find_exact_topic_values(obj):
        """Recursively collect string values from nested dicts/lists."""
        values = []
        if isinstance(obj, dict):
            for v in obj.values():
                values.extend(_find_exact_topic_values(v))
        elif isinstance(obj, list):
            for v in obj:
                values.extend(_find_exact_topic_values(v))
        elif isinstance(obj, str):
            values.append(obj)
        return values

    for ypath in production_yaml_files:
        assert ypath.exists(), f'Production config file missing: {ypath}'
        with open(ypath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        all_values = _find_exact_topic_values(data)
        assert '/scan' not in all_values, f'Forbidden exact topic /scan found in {ypath}'
        assert '/scan_collision' not in all_values, (
            f'Forbidden exact topic /scan_collision found in {ypath}'
        )

    # Check production launch files
    production_launch_files = [
        ws_root / 'src' / 'mobile_base_bringup' / 'launch' / 'mapping.launch.py',
        ws_root / 'src' / 'mobile_base_bringup' / 'launch' / 'navigation.launch.py',
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'sick_dual_lidar.launch.py',
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'tdk_imu.launch.py',
        ws_root / 'src' / 'mobile_base_mapping' / 'launch' / 'mapping.launch.py',
        ws_root / 'src' / 'mobile_base_localization' / 'launch' / 'localization.launch.py',
        ws_root / 'src' / 'mobile_base_navigation' / 'launch' / 'navigation.launch.py',
    ]

    for lpath in production_launch_files:
        assert lpath.exists(), f'Production launch file missing: {lpath}'
        with open(lpath, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'dual_laser_merger' not in content, (
            f'dual_laser_merger reference found in {lpath}'
        )
        assert 'collision_scan_filter' not in content, (
            f'collision_scan_filter reference found in {lpath}'
        )
        assert "'/scan'" not in content and '"/scan"' not in content, (
            f'Exact topic /scan literal found in {lpath}'
        )
        assert "'/scan_collision'" not in content and '"/scan_collision"' not in content, (
            f'Exact topic /scan_collision literal found in {lpath}'
        )


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
    # IMU yaw rate (vyaw) only; linear acceleration remains excluded
    assert ekf_params['imu0_config'][11] is True  # vyaw
    assert ekf_params['imu0_config'][12] is False  # ax


def test_kinematic_icp_odometry_contract_and_ekf_consumer():
    """Verify Kinematic-ICP uses front scan and wheel prior and feeds EKF pose."""
    ws_root = get_workspace_root()

    # 1. Kinematic-ICP configuration
    kicp_config = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'config' /
        'kinematic_icp_ros.yaml'
    )
    assert kicp_config.exists()
    with open(kicp_config, 'r', encoding='utf-8') as f:
        kicp_params = yaml.safe_load(f)['/**']['ros__parameters']

    assert kicp_params['lidar_topic'] == '/scan_front'
    assert kicp_params['wheel_odom_topic'] == '/diff_drive_controller/odom'
    assert kicp_params['lidar_odom_frame'] == 'odom'
    assert kicp_params['base_frame'] == 'base_footprint'
    assert kicp_params['publish_odom_tf'] is False
    assert kicp_params['invert_odom_tf'] is False

    # 2. Consumer in S3 robot_localization EKF
    ekf_yaml = ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    assert ekf_yaml.exists()
    with open(ekf_yaml, 'r', encoding='utf-8') as f:
        ekf_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    assert ekf_params['odom0'] == '/lidar_odometry'
    assert ekf_params['odom0_config'][0] is True   # x
    assert ekf_params['odom0_config'][1] is True   # y
    assert ekf_params['odom0_config'][5] is True   # yaw
    assert not any(ekf_params['odom0_config'][6:12])  # no Kinematic-ICP twist
    assert 'odom1' not in ekf_params


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
    cm_timeout = nav2_params['collision_monitor']['ros__parameters']['source_timeout']
    assert cm_timeout >= 0.5

    # 3. S7 diff_drive_controller command timeout (500 ms)
    ctrl_yaml = ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml'
    assert ctrl_yaml.exists()
    with open(ctrl_yaml, 'r', encoding='utf-8') as f:
        ctrl_params = yaml.safe_load(f)['diff_drive_controller']['ros__parameters']
    assert ctrl_params['cmd_vel_timeout'] == 0.5
