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

"""Automated consolidated tests for TF Authority and Frame Consistency (Checklist #19)."""

from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest
import yaml


def get_workspace_root() -> Path:
    """Get the root directory of mobile_base workspace."""
    return Path(__file__).resolve().parent.parent.parent.parent


def test_s1_urdf_tf_tree_structure():
    """Verify S1 Robot Description URDF static and dynamic joint hierarchy."""
    ws_root = get_workspace_root()
    xacro_path = ws_root / 'src' / 'mobile_base_description' / 'urdf' / 'mobile_base.urdf.xacro'
    assert xacro_path.exists(), f'Xacro file not found at {xacro_path}'

    # Process Xacro to generate complete URDF
    cmd = ['xacro', str(xacro_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    urdf_xml = result.stdout
    assert len(urdf_xml) > 0

    root = ET.fromstring(urdf_xml)
    assert root.tag == 'robot'

    links = {elem.attrib['name'] for elem in root.findall('link')}
    joints = {elem.attrib['name']: elem for elem in root.findall('joint')}

    # Expected canonical links (docs/05_architecture.md §7.1, docs/06_subsystem.md §4.1)
    required_links = {
        'base_footprint',
        'base_link',
        'base_lidar_link_FL',
        'base_lidar_link_BR',
        'base_imu_link',
        'driving_wheel_link_L',
        'driving_wheel_link_R',
    }
    assert required_links.issubset(links), f'Missing links in URDF: {required_links - links}'

    # 1. base_joint: base_footprint -> base_link (Ground clearance elevation)
    assert 'base_joint' in joints
    bj = joints['base_joint']
    assert bj.attrib['type'] == 'fixed'
    assert bj.find('parent').attrib['link'] == 'base_footprint'
    assert bj.find('child').attrib['link'] == 'base_link'
    origin = bj.find('origin')
    assert origin is not None
    xyz = [float(v) for v in origin.attrib['xyz'].split()]
    assert pytest.approx(xyz[0]) == 0.0
    assert pytest.approx(xyz[1]) == 0.0
    assert pytest.approx(xyz[2]) == 0.2560  # Canonical elevation 256.0mm

    # 2. LiDAR joints: base_link -> base_lidar_link_FL / BR
    assert 'base_lidar_joint_FL' in joints or 'lidar_fl_joint' in joints
    fl = joints.get('base_lidar_joint_FL') or joints.get('lidar_fl_joint')
    assert fl.attrib['type'] == 'fixed'
    assert fl.find('parent').attrib['link'] == 'base_link'
    assert fl.find('child').attrib['link'] == 'base_lidar_link_FL'

    assert 'base_lidar_joint_BR' in joints or 'lidar_br_joint' in joints
    br = joints.get('base_lidar_joint_BR') or joints.get('lidar_br_joint')
    assert br.attrib['type'] == 'fixed'
    assert br.find('parent').attrib['link'] == 'base_link'
    assert br.find('child').attrib['link'] == 'base_lidar_link_BR'

    # 3. IMU joint: base_link -> base_imu_link
    assert 'base_imu_joint' in joints or 'imu_joint' in joints
    imu = joints.get('base_imu_joint') or joints.get('imu_joint')
    assert imu.attrib['type'] == 'fixed'
    assert imu.find('parent').attrib['link'] == 'base_link'
    assert imu.find('child').attrib['link'] == 'base_imu_link'

    # 4. Driving wheel joints: base_link -> driving_wheel_link_L / R
    assert 'driving_wheel_joint_L' in joints
    wl = joints['driving_wheel_joint_L']
    assert wl.attrib['type'] == 'continuous'
    assert wl.find('parent').attrib['link'] == 'base_link'
    assert wl.find('child').attrib['link'] == 'driving_wheel_link_L'

    assert 'driving_wheel_joint_R' in joints
    wr = joints['driving_wheel_joint_R']
    assert wr.attrib['type'] == 'continuous'
    assert wr.find('parent').attrib['link'] == 'base_link'
    assert wr.find('child').attrib['link'] == 'driving_wheel_link_R'


def test_s3_odom_to_base_footprint_sole_authority():
    """Verify that EKF is the SOLE authority configured to publish odom -> base_footprint."""
    ws_root = get_workspace_root()

    # 1. Check EKF configuration (S3 State Estimation)
    ekf_config_path = (
        ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    )
    assert ekf_config_path.exists()
    with open(ekf_config_path, 'r', encoding='utf-8') as f:
        ekf_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']

    assert ekf_params['publish_tf'] is True
    assert ekf_params['world_frame'] == 'odom'
    assert ekf_params['odom_frame'] == 'odom'
    assert ekf_params['base_link_frame'] == 'base_footprint'
    assert ekf_params['map_frame'] == 'map'
    assert ekf_params['frequency'] == 50.0

    # 2. Check diff_drive_controller (S7 Base Control) - MUST NOT publish odom TF
    ctrl_config_path = (
        ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml'
    )
    assert ctrl_config_path.exists()
    with open(ctrl_config_path, 'r', encoding='utf-8') as f:
        ctrl_params = yaml.safe_load(f)['diff_drive_controller']['ros__parameters']

    assert ctrl_params['enable_odom_tf'] is False, (
        'diff_drive_controller must have enable_odom_tf: false to prevent duplicate TF'
    )

    # 3. Check Kinematic-ICP parameters - MUST NOT publish odom TF
    kicp_config_path = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'config' /
        'kinematic_icp_ros.yaml'
    )
    assert kicp_config_path.exists()
    with open(kicp_config_path, 'r', encoding='utf-8') as f:
        kicp_params = yaml.safe_load(f)['/**']['ros__parameters']
    assert kicp_params['publish_odom_tf'] is False


def test_s4_mapping_mode_map_to_odom_authority():
    """Verify S4 Mapping Mode configuration: slam_toolbox publishes map -> odom, AMCL absent."""
    ws_root = get_workspace_root()

    # 1. Check slam_toolbox configuration
    slam_config_path = ws_root / 'src' / 'mobile_base_mapping' / 'config' / 'slam_toolbox.yaml'
    assert slam_config_path.exists()
    with open(slam_config_path, 'r', encoding='utf-8') as f:
        slam_params = yaml.safe_load(f)['async_slam_toolbox_node']['ros__parameters']

    assert slam_params['mode'] == 'mapping'
    assert slam_params['map_frame'] == 'map'
    assert slam_params['odom_frame'] == 'odom'
    assert slam_params['base_frame'] == 'base_footprint'
    assert slam_params['transform_publish_period'] > 0.0  # 20 Hz map -> odom TF

    # 2. Check Mapping launch file does not launch AMCL
    mapping_launch_path = ws_root / 'src' / 'mobile_base_bringup' / 'launch' / 'mapping.launch.py'
    assert mapping_launch_path.exists()
    with open(mapping_launch_path, 'r', encoding='utf-8') as f:
        mapping_launch_content = f.read()

    assert (
        'slam_toolbox' in mapping_launch_content or
        'mobile_base_mapping' in mapping_launch_content
    )
    assert 'amcl' not in mapping_launch_content, 'Mapping Mode must not launch AMCL'


def test_s5_navigation_mode_map_to_odom_authority():
    """Verify S5 Navigation Mode configuration: AMCL publishes map -> odom, slam_toolbox absent."""
    ws_root = get_workspace_root()

    # 1. Check AMCL configuration
    amcl_config_path = (
        ws_root / 'src' / 'mobile_base_localization' / 'config' / 'amcl_params.yaml'
    )
    assert amcl_config_path.exists()
    with open(amcl_config_path, 'r', encoding='utf-8') as f:
        amcl_params = yaml.safe_load(f)['amcl']['ros__parameters']

    assert amcl_params['global_frame_id'] == 'map'
    assert amcl_params['odom_frame_id'] == 'odom'
    assert amcl_params['base_frame_id'] == 'base_footprint'
    assert amcl_params['tf_broadcast'] is True  # Publishes map -> odom

    # 2. Check Navigation launch file does not launch slam_toolbox
    nav_launch_path = (
        ws_root / 'src' / 'mobile_base_navigation' / 'launch' / 'navigation.launch.py'
    )
    assert nav_launch_path.exists()
    with open(nav_launch_path, 'r', encoding='utf-8') as f:
        nav_launch_content = f.read()

    assert 'slam_toolbox' not in nav_launch_content, 'Navigation Mode must not launch slam_toolbox'


def test_sensor_and_perception_frame_ids_match_urdf():
    """Verify S2 sensor frame IDs in launch/configs match authoritative S1 URDF frames."""
    ws_root = get_workspace_root()

    # 1. Dual laser merger target frame
    merger_launch_path = (
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'dual_laser_merger.launch.py'
    )
    assert merger_launch_path.exists()
    with open(merger_launch_path, 'r', encoding='utf-8') as f:
        merger_content = f.read()

    assert (
        "'target_frame', default_value='base_link'" in merger_content or
        "default_value='base_link'" in merger_content
    )
    assert (
        "'merged_scan_topic', default_value='/scan'" in merger_content or
        "default_value='/scan'" in merger_content
    )

    # 2. Dual LiDAR driver frames
    lidar_launch_path = (
        ws_root / 'src' / 'mobile_base_perception' / 'launch' / 'sick_dual_lidar.launch.py'
    )
    assert lidar_launch_path.exists()
    with open(lidar_launch_path, 'r', encoding='utf-8') as f:
        lidar_content = f.read()

    assert 'base_lidar_link_FL' in lidar_content
    assert 'base_lidar_link_BR' in lidar_content

    # 3. IMU driver frame
    imu_config_path = (
        ws_root / 'src' / 'mobile_base_perception' / 'config' / 'tdk_imu.yaml'
    )
    assert imu_config_path.exists()
    with open(imu_config_path, 'r', encoding='utf-8') as f:
        imu_content = f.read()

    assert 'base_imu_link' in imu_content


def test_kinematic_icp_frame_semantics_and_tf_authority():
    """Verify canonical Kinematic-ICP frame semantics and sole EKF TF authority."""
    ws_root = get_workspace_root()

    # 1. Kinematic-ICP configuration
    kicp_config_path = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'config' / 'kinematic_icp_ros.yaml'
    )
    assert kicp_config_path.exists()
    with open(kicp_config_path, 'r', encoding='utf-8') as f:
        kicp_data = yaml.safe_load(f)
        kicp_params = (
            kicp_data.get('/**') or kicp_data.get('kinematic_icp_online_node')
        )['ros__parameters']

    assert kicp_params['lidar_odom_frame'] == 'odom'
    assert kicp_params['base_frame'] == 'base_footprint'
    assert kicp_params['publish_odom_tf'] is False
    assert kicp_params['invert_odom_tf'] is False

    # 2. Canonical EKF configuration
    ekf_kicp_config_path = (
        ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    )
    assert ekf_kicp_config_path.exists()
    with open(ekf_kicp_config_path, 'r', encoding='utf-8') as f:
        ekf_kicp_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']

    assert ekf_kicp_params['publish_tf'] is True
    assert ekf_kicp_params['world_frame'] == 'odom'
    assert ekf_kicp_params['odom_frame'] == 'odom'
    assert ekf_kicp_params['base_link_frame'] == 'base_footprint'
    assert ekf_kicp_params['odom0'] == '/lidar_odometry'

    # 3. Protect that no active configuration introduces odom_lidar
    for config_file in (kicp_config_path, ekf_kicp_config_path):
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'odom_lidar' not in content, (
            f"Found forbidden 'odom_lidar' frame in {config_file}"
        )
