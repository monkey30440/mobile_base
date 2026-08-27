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

"""Narrow structural and contract tests for the project-owned Navigation bringup."""

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
import yaml


def _load_launch_module(launch_file_path: Path):
    spec = importlib.util.spec_from_file_location(
        'mobile_base_bringup_navigation_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_path(include: IncludeLaunchDescription) -> str:
    source = include.launch_description_source
    substitutions = source._LaunchDescriptionSource__location
    return ''.join(getattr(part, 'text', str(part)) for part in substitutions)


def test_navigation_launch_composes_all_subsystems_without_slam(monkeypatch):
    """Verify Navigation Mode launch includes all required subsystems and excludes mapping/slam."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_file = pkg_dir / 'launch' / 'navigation.launch.py'
    assert launch_file.exists(), f'Missing {launch_file}'

    module = _load_launch_module(launch_file)
    monkeypatch.setattr(
        module,
        'get_package_share_directory',
        lambda package: f'/opt/ros/share/{package}',
    )

    launch_description = module.generate_launch_description()
    assert isinstance(launch_description, LaunchDescription)

    arguments = {
        entity.name: entity
        for entity in launch_description.entities
        if isinstance(entity, DeclareLaunchArgument)
    }
    expected_args = {
        'map',
        'route_graph',
        'use_sim_time',
        'autostart',
        'localization_params_file',
        'nav2_params_file',
        'bt_xml',
        'use_foxglove',
        'log_level',
        'serial_port',
        'baud_rate',
        'response_timeout_ms',
        'use_mock_hardware',
        'lidar_odom_frame',
        'publish_odom_tf',
        'invert_odom_tf',
        'lidar_topic',
        'wheel_odom_topic',
    }
    assert expected_args.issubset(set(arguments))

    includes = [
        entity for entity in launch_description.entities
        if isinstance(entity, IncludeLaunchDescription)
    ]
    paths = [_source_path(include) for include in includes]

    expected_suffixes = {
        'mobile_base_control/launch/base_control.launch.py',
        'mobile_base_perception/launch/tdk_imu.launch.py',
        'mobile_base_perception/launch/sick_dual_lidar.launch.py',
        'kinematic_icp/launch/kinematic_icp.launch.py',
        'mobile_base_state_estimation/launch/ekf.launch.py',
        'mobile_base_localization/launch/localization.launch.py',
        'mobile_base_navigation/launch/navigation.launch.py',
        'foxglove_bridge/launch/foxglove_bridge_launch.xml',
    }
    assert len(includes) == len(expected_suffixes)
    assert all(any(path.endswith(suffix) for path in paths) for suffix in expected_suffixes)

    # Prohibited includes in Navigation Mode
    assert not any('mobile_base_mapping' in path for path in paths), (
        'Must not include mobile_base_mapping'
    )
    assert not any('slam_toolbox' in path for path in paths), (
        'Must not include slam_toolbox'
    )
    assert not any('mobile_base_description' in path for path in paths), (
        'Must not directly include description (encapsulated in base_control)'
    )
    assert not any('nav2_bringup' in path for path in paths), (
        'Must not include nav2_bringup directly'
    )
    assert not any('rf2o' in path.lower() for path in paths)

    # Foxglove conditional launch
    foxglove = next(include for include, path in zip(includes, paths) if 'foxglove' in path)
    assert isinstance(foxglove.condition, IfCondition)
    assert all(include.condition is None for include in includes if include is not foxglove)


def test_navigation_launch_argument_forwarding(monkeypatch):
    """Verify launch argument forwarding to downstream child launches."""
    pkg_dir = Path(__file__).resolve().parent.parent
    module = _load_launch_module(pkg_dir / 'launch' / 'navigation.launch.py')
    monkeypatch.setattr(
        module,
        'get_package_share_directory',
        lambda package: f'/opt/ros/share/{package}',
    )

    ld = module.generate_launch_description()
    includes = [e for e in ld.entities if isinstance(e, IncludeLaunchDescription)]
    paths = [_source_path(inc) for inc in includes]

    # Check localization launch arguments
    loc_inc = next(inc for inc, p in zip(includes, paths) if 'mobile_base_localization' in p)
    assert loc_inc.launch_arguments is not None
    loc_arg_names = {k for k, _ in loc_inc.launch_arguments}
    expected_loc_args = {'map', 'params_file', 'use_sim_time', 'autostart', 'log_level'}
    assert expected_loc_args.issubset(loc_arg_names)

    # Check navigation launch arguments
    nav_inc = next(inc for inc, p in zip(includes, paths) if 'mobile_base_navigation' in p)
    assert nav_inc.launch_arguments is not None
    nav_arg_names = {k for k, _ in nav_inc.launch_arguments}
    expected_nav_args = {
        'use_sim_time', 'autostart', 'params_file', 'bt_xml', 'route_graph', 'log_level'
    }
    assert expected_nav_args.issubset(nav_arg_names)

    # Check base_control launch arguments
    ctrl_inc = next(inc for inc, p in zip(includes, paths) if 'mobile_base_control' in p)
    assert ctrl_inc.launch_arguments is not None
    ctrl_arg_names = {k for k, _ in ctrl_inc.launch_arguments}
    expected_ctrl_args = {
        'use_sim_time', 'use_mock_hardware', 'serial_port', 'baud_rate', 'response_timeout_ms'
    }
    assert expected_ctrl_args.issubset(ctrl_arg_names)


def test_package_declares_navigation_runtime_dependencies():
    """Verify package.xml declares mobile_base_localization and mobile_base_navigation."""
    package_dir = Path(__file__).resolve().parent.parent
    root = ET.parse(package_dir / 'package.xml').getroot()
    runtime_dependencies = {
        element.text for element in root.findall('exec_depend')
    }
    assert 'mobile_base_localization' in runtime_dependencies
    assert 'mobile_base_navigation' in runtime_dependencies
    assert 'mobile_base_control' in runtime_dependencies
    assert 'mobile_base_perception' in runtime_dependencies
    assert 'mobile_base_state_estimation' in runtime_dependencies
    assert 'kinematic_icp' in runtime_dependencies
    assert 'rf2o_laser_odometry' not in runtime_dependencies
    assert 'nav2_map_server' in runtime_dependencies
    assert 'foxglove_bridge' in runtime_dependencies


def test_navigation_mode_tf_authority_and_cmd_vel_chain():
    """Verify TF authority and cmd_vel remappings for Navigation Mode."""
    ws_root = Path(__file__).resolve().parent.parent.parent.parent

    # 1. AMCL is map -> odom sole authority
    amcl_yaml = ws_root / 'src' / 'mobile_base_localization' / 'config' / 'amcl_params.yaml'
    assert amcl_yaml.exists()
    with open(amcl_yaml, 'r', encoding='utf-8') as f:
        amcl_params = yaml.safe_load(f)['amcl']['ros__parameters']
    assert amcl_params['tf_broadcast'] is True
    assert amcl_params['global_frame_id'] == 'map'
    assert amcl_params['odom_frame_id'] == 'odom'

    # 2. EKF is odom -> base_footprint sole authority
    ekf_yaml = ws_root / 'src' / 'mobile_base_state_estimation' / 'config' / 'ekf.yaml'
    assert ekf_yaml.exists()
    with open(ekf_yaml, 'r', encoding='utf-8') as f:
        ekf_params = yaml.safe_load(f)['ekf_filter_node']['ros__parameters']
    assert ekf_params['publish_tf'] is True
    assert ekf_params['world_frame'] == 'odom'

    # 3. Navigation cmd_vel -> Collision Monitor -> diff_drive_controller chain
    nav_launch = ws_root / 'src' / 'mobile_base_navigation' / 'launch' / 'navigation.launch.py'
    assert nav_launch.exists()
    with open(nav_launch, 'r', encoding='utf-8') as f:
        nav_launch_text = f.read()

    assert "'/cmd_vel_nav'" in nav_launch_text
    assert "'/diff_drive_controller/cmd_vel'" in nav_launch_text
