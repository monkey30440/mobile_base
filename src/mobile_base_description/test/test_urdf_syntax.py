#!/usr/bin/env python3
# Copyright 2026 Jim Chen
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

import math
import os
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import numpy as np
import pytest
import xacro


def rpy_to_matrix(roll, pitch, yaw):
    """Compute 3x3 rotation matrix using URDF / REP-103 convention: R = Rz*Ry*Rx."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1.0, 0.0, 0.0],
                   [0.0, cr, -sr],
                   [0.0, sr, cr]])
    ry = np.array([[cp, 0.0, sp],
                   [0.0, 1.0, 0.0],
                   [-sp, 0.0, cp]])
    rz = np.array([[cy, -sy, 0.0],
                   [sy, cy, 0.0],
                   [0.0, 0.0, 1.0]])
    return rz @ ry @ rx


def read_stl_vertices(filename):
    """Read all 3D vertices from a binary STL file."""
    with open(filename, 'rb') as f:
        f.read(80)
        num_triangles = struct.unpack('<I', f.read(4))[0]
        verts = []
        for _ in range(num_triangles):
            data = f.read(50)
            v1 = struct.unpack('<3f', data[12:24])
            v2 = struct.unpack('<3f', data[24:36])
            v3 = struct.unpack('<3f', data[36:48])
            verts.extend([v1, v2, v3])
        return np.array(verts)


@pytest.fixture(scope='module')
def xacro_path():
    """Locate the mobile_base.urdf.xacro file."""
    try:
        pkg_dir = get_package_share_directory('mobile_base_description')
    except Exception:
        pkg_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
        )
    return os.path.join(pkg_dir, 'urdf', 'mobile_base.urdf.xacro')


@pytest.fixture(scope='module')
def urdf_xml_string(xacro_path):
    """Generate the URDF XML string by expanding mobile_base.urdf.xacro with explicit timeout."""
    doc = xacro.process_file(
        xacro_path,
        mappings={
            'use_mock_hardware': 'true',
            'response_timeout_ms': '50',
        },
    )
    return doc.toxml()


def test_timeout_omission_produces_no_param(xacro_path):
    """Verify that expanding Xacro without response_timeout_ms produces no timeout param."""
    doc = xacro.process_file(
        xacro_path,
        mappings={
            'use_mock_hardware': 'true',
        },
    )
    xml_str = doc.toxml()
    root = ET.fromstring(xml_str)
    hw = root.find('ros2_control/hardware')
    assert hw is not None
    params = {p.attrib.get('name'): p.text for p in hw.findall('param')}
    assert 'response_timeout_ms' not in params, (
        'response_timeout_ms must NOT be present when omitted by caller'
    )


def test_xacro_expansion(urdf_xml_string):
    """Test that xacro expands successfully to non-empty XML."""
    assert urdf_xml_string is not None
    assert len(urdf_xml_string) > 100
    assert '<robot' in urdf_xml_string
    assert '</robot>' in urdf_xml_string


def test_check_urdf_cli(urdf_xml_string, tmp_path):
    """Test that check_urdf CLI tool validates the expanded URDF structure."""
    check_urdf_bin = shutil.which('check_urdf')
    if check_urdf_bin is None:
        pytest.skip('check_urdf command not found in PATH')

    urdf_file = tmp_path / 'mobile_base.urdf'
    urdf_file.write_text(urdf_xml_string)

    result = subprocess.run(
        [check_urdf_bin, str(urdf_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f'check_urdf failed: {result.stderr}'
    valid_out = ('Successfully Parsed XML' in result.stdout or
                 'robot name is: mobile_base' in result.stdout)
    assert valid_out


def test_canonical_links_and_root(urdf_xml_string):
    """Verify canonical links and root link base_footprint."""
    root = ET.fromstring(urdf_xml_string)
    assert root.attrib.get('name') == 'mobile_base'

    links = [link.attrib.get('name') for link in root.findall('link')]
    required_links = [
        'base_footprint',
        'base_link',
        'driving_wheel_link_L',
        'driving_wheel_link_R',
        'base_lidar_link_FL',
        'base_lidar_link_FL_1',
        'base_lidar_link_BR',
        'base_lidar_link_BR_1',
        'base_imu_link',
    ]
    for req_link in required_links:
        assert req_link in links, f'Required link {req_link} missing from URDF'

    # Check that base_footprint is not a child of any joint (i.e. It is the root)
    child_links = [
        joint.find('child').attrib.get('link')
        for joint in root.findall('joint')
        if joint.find('child') is not None
    ]
    assert 'base_footprint' not in child_links, 'base_footprint must be the root link'


def test_canonical_joints_and_transforms(urdf_xml_string):
    """Verify canonical joints, types, origins, and axes."""
    root = ET.fromstring(urdf_xml_string)
    joints = {j.attrib.get('name'): j for j in root.findall('joint')}

    # 1. Base Joint
    assert 'base_joint' in joints
    base_j = joints['base_joint']
    assert base_j.attrib.get('type') == 'fixed'
    assert base_j.find('parent').attrib.get('link') == 'base_footprint'
    assert base_j.find('child').attrib.get('link') == 'base_link'
    xyz_b = [float(v) for v in base_j.find('origin').attrib.get('xyz').split()]
    rpy_b = [float(v) for v in base_j.find('origin').attrib.get('rpy').split()]
    assert pytest.approx(xyz_b, abs=1e-4) == [0.0, 0.0, 0.2560]
    assert pytest.approx(rpy_b, abs=1e-4) == [0.0, 0.0, 0.0]

    # 2. Left Wheel Joint (driving_wheel_joint_L)
    assert 'driving_wheel_joint_L' in joints
    wheel_l = joints['driving_wheel_joint_L']
    assert wheel_l.attrib.get('type') == 'continuous'
    assert wheel_l.find('parent').attrib.get('link') == 'base_link'
    assert wheel_l.find('child').attrib.get('link') == 'driving_wheel_link_L'
    xyz_l = [float(v) for v in wheel_l.find('origin').attrib.get('xyz').split()]
    assert pytest.approx(xyz_l, abs=1e-4) == [0.0205, 0.2775, -0.1760]
    axis_l = [float(v) for v in wheel_l.find('axis').attrib.get('xyz').split()]
    assert axis_l == [0.0, 1.0, 0.0]

    # 3. Right Wheel Joint (driving_wheel_joint_R)
    assert 'driving_wheel_joint_R' in joints
    wheel_r = joints['driving_wheel_joint_R']
    assert wheel_r.attrib.get('type') == 'continuous'
    assert wheel_r.find('parent').attrib.get('link') == 'base_link'
    assert wheel_r.find('child').attrib.get('link') == 'driving_wheel_link_R'
    xyz_r = [float(v) for v in wheel_r.find('origin').attrib.get('xyz').split()]
    assert pytest.approx(xyz_r, abs=1e-4) == [0.0205, -0.2770, -0.1760]
    axis_r = [float(v) for v in wheel_r.find('axis').attrib.get('xyz').split()]
    assert axis_r == [0.0, 1.0, 0.0]

    # 4. Front-Left LiDAR (base_lidar_joint_FL)
    assert 'base_lidar_joint_FL' in joints
    lidar_fl = joints['base_lidar_joint_FL']
    assert lidar_fl.attrib.get('type') == 'fixed'
    assert lidar_fl.find('parent').attrib.get('link') == 'base_link'
    assert lidar_fl.find('child').attrib.get('link') == 'base_lidar_link_FL'
    xyz_fl = [float(v) for v in lidar_fl.find('origin').attrib.get('xyz').split()]
    rpy_fl = [float(v) for v in lidar_fl.find('origin').attrib.get('rpy').split()]
    assert pytest.approx(xyz_fl, abs=1e-4) == [0.28771, 0.26721, -0.06011]
    assert pytest.approx(rpy_fl, abs=1e-4) == [math.pi, 0.0, math.pi / 4.0]

    # 4b. Front-Left LiDAR Layer 1 (base_lidar_joint_FL_1)
    assert 'base_lidar_joint_FL_1' in joints
    lidar_fl_1 = joints['base_lidar_joint_FL_1']
    assert lidar_fl_1.attrib.get('type') == 'fixed'
    assert lidar_fl_1.find('parent').attrib.get('link') == 'base_lidar_link_FL'
    assert lidar_fl_1.find('child').attrib.get('link') == 'base_lidar_link_FL_1'
    xyz_fl_1 = [float(v) for v in lidar_fl_1.find('origin').attrib.get('xyz').split()]
    rpy_fl_1 = [float(v) for v in lidar_fl_1.find('origin').attrib.get('rpy').split()]
    assert pytest.approx(xyz_fl_1, abs=1e-4) == [0.0, 0.0, 0.0]
    assert pytest.approx(rpy_fl_1, abs=1e-4) == [0.0, 0.0, 0.0]

    # 5. Rear-Right LiDAR (base_lidar_joint_BR)
    assert 'base_lidar_joint_BR' in joints
    lidar_br = joints['base_lidar_joint_BR']
    assert lidar_br.attrib.get('type') == 'fixed'
    assert lidar_br.find('parent').attrib.get('link') == 'base_link'
    assert lidar_br.find('child').attrib.get('link') == 'base_lidar_link_BR'
    xyz_br = [float(v) for v in lidar_br.find('origin').attrib.get('xyz').split()]
    rpy_br = [float(v) for v in lidar_br.find('origin').attrib.get('rpy').split()]
    assert pytest.approx(xyz_br, abs=1e-4) == [-0.24671, -0.26721, -0.06011]
    assert pytest.approx(rpy_br, abs=1e-4) == [math.pi, 0.0, -3.0 * math.pi / 4.0]

    # 5b. Rear-Right LiDAR Layer 1 (base_lidar_joint_BR_1)
    assert 'base_lidar_joint_BR_1' in joints
    lidar_br_1 = joints['base_lidar_joint_BR_1']
    assert lidar_br_1.attrib.get('type') == 'fixed'
    assert lidar_br_1.find('parent').attrib.get('link') == 'base_lidar_link_BR'
    assert lidar_br_1.find('child').attrib.get('link') == 'base_lidar_link_BR_1'
    xyz_br_1 = [float(v) for v in lidar_br_1.find('origin').attrib.get('xyz').split()]
    rpy_br_1 = [float(v) for v in lidar_br_1.find('origin').attrib.get('rpy').split()]
    assert pytest.approx(xyz_br_1, abs=1e-4) == [0.0, 0.0, 0.0]
    assert pytest.approx(rpy_br_1, abs=1e-4) == [0.0, 0.0, 0.0]

    # 6. IMU Joint (base_imu_joint)
    assert 'base_imu_joint' in joints
    imu_j = joints['base_imu_joint']
    assert imu_j.attrib.get('type') == 'fixed'
    assert imu_j.find('parent').attrib.get('link') == 'base_link'
    assert imu_j.find('child').attrib.get('link') == 'base_imu_link'
    xyz_imu = [float(v) for v in imu_j.find('origin').attrib.get('xyz').split()]
    rpy_imu = [float(v) for v in imu_j.find('origin').attrib.get('rpy').split()]
    assert pytest.approx(xyz_imu, abs=1e-4) == [0.04375, -0.00800, -0.01459]
    assert pytest.approx(rpy_imu, abs=1e-4) == [0.0, 0.0, math.pi / 2.0]


def test_sensor_mesh_alignment_and_compensation(urdf_xml_string):
    """Verify that visual/collision compensation transforms satisfy R_joint * R_comp ~= I."""
    root = ET.fromstring(urdf_xml_string)
    joints = {j.attrib.get('name'): j for j in root.findall('joint')}
    links_map = {link_elem.attrib.get('name'): link_elem for link_elem in root.findall('link')}

    sensor_checks = [
        ('base_lidar_joint_FL', 'base_lidar_link_FL'),
        ('base_lidar_joint_BR', 'base_lidar_link_BR'),
        ('base_imu_joint', 'base_imu_link'),
    ]

    for j_name, l_name in sensor_checks:
        j_elem = joints[j_name]
        l_elem = links_map[l_name]

        j_rpy = [float(v) for v in j_elem.find('origin').attrib.get('rpy').split()]
        R_joint = rpy_to_matrix(*j_rpy)

        v_elem = l_elem.find('visual/origin')
        assert v_elem is not None, f'{l_name} missing visual origin'
        v_rpy = [float(v) for v in v_elem.attrib.get('rpy').split()]
        R_visual = rpy_to_matrix(*v_rpy)

        c_elem = l_elem.find('collision/origin')
        assert c_elem is not None, f'{l_name} missing collision origin'
        c_rpy = [float(v) for v in c_elem.attrib.get('rpy').split()]

        # Collision RPY must match visual RPY
        assert pytest.approx(c_rpy, abs=1e-6) == v_rpy

        # R_joint * R_visual must be Identity within floating-point tolerance
        prod = R_joint @ R_visual
        err = np.linalg.norm(prod - np.eye(3))
        assert err < 1e-12, f'{l_name} R_joint * R_visual residual error {err} exceeds tolerance'


def test_lidar_mesh_bounding_boxes(urdf_xml_string):
    """Verify that compensated LiDAR meshes occupy their exact CAD mounting recesses."""
    try:
        pkg_dir = get_package_share_directory('mobile_base_description')
    except Exception:
        pkg_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
        )

    fl_stl = os.path.join(pkg_dir, 'meshes', 'base_lidar_link_FL.STL')
    verts_fl = read_stl_vertices(fl_stl)

    # Transform FL vertices into base_link coordinate system
    R_joint_fl = rpy_to_matrix(math.pi, 0.0, math.pi / 4.0)
    R_vis_fl = rpy_to_matrix(math.pi, 0.0, math.pi / 4.0)
    p_fl = np.array([0.28771, 0.26721, -0.06011])
    v_base_fl = (R_joint_fl @ (R_vis_fl @ verts_fl.T)).T + p_fl

    # Verify FL front-left corner bounding box matches CAD flush recess
    assert pytest.approx(v_base_fl[:, 0].max(), abs=1e-3) == 0.3271
    assert pytest.approx(v_base_fl[:, 1].max(), abs=1e-3) == 0.3066


def test_ros2_control_structure(urdf_xml_string):
    """Verify ros2_control hardware interface block and parameter contracts."""
    root = ET.fromstring(urdf_xml_string)
    r2c = root.find('ros2_control')
    assert r2c is not None, 'ros2_control tag missing from URDF'
    assert r2c.attrib.get('name') == 'M1Hardware'
    assert r2c.attrib.get('type') == 'system'

    hw = r2c.find('hardware')
    assert hw is not None
    assert hw.find('plugin').text.strip() == 'mobile_base_control/M1Hardware'

    params = {p.attrib.get('name'): p.text.strip() for p in hw.findall('param')}
    assert 'serial_port' in params
    assert 'baud_rate' in params
    assert 'response_timeout_ms' in params
    assert params['response_timeout_ms'] == '50'
    assert params['left_driver_id'] == '2'
    assert params['right_driver_id'] == '1'
    assert float(params['gear_ratio']) == 20.0
    assert params['left_wheel_sign'] == '1'
    assert params['right_wheel_sign'] == '-1'

    # Check joints in ros2_control
    ctrl_joints = {j.attrib.get('name'): j for j in r2c.findall('joint')}
    assert 'driving_wheel_joint_L' in ctrl_joints
    assert 'driving_wheel_joint_R' in ctrl_joints

    for joint_name, joint_elem in ctrl_joints.items():
        cmd_ifaces = [ci.attrib.get('name') for ci in joint_elem.findall('command_interface')]
        state_ifaces = [si.attrib.get('name') for si in joint_elem.findall('state_interface')]
        assert 'velocity' in cmd_ifaces, f'{joint_name} missing velocity command interface'
        assert 'position' in state_ifaces, f'{joint_name} missing position state interface'
        assert 'velocity' in state_ifaces, f'{joint_name} missing velocity state interface'
