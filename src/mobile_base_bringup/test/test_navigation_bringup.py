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

"""Narrow structural and contract tests for the project-owned Navigation bringup and wrapper."""

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
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


def test_navigation_launch_delegates_to_canonical_mobile_base_launch(monkeypatch):
    """Verify navigation.launch.py acts as a thin wrapper forwarding to canonical launch."""
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
        'site',
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
    assert len(includes) == 1
    canonical_include = includes[0]
    path = _source_path(canonical_include)
    assert path.endswith('mobile_base_bringup/launch/mobile_base.launch.py')

    forwarded_args = dict(canonical_include.launch_arguments)
    assert forwarded_args['mode'] == 'navigation'
    assert forwarded_args['platform'] == 'real'
    assert forwarded_args['variant'] == 'default'
    assert 'site' in forwarded_args
    assert 'map' in forwarded_args
    assert 'route_graph' in forwarded_args
    assert 'use_sim_time' in forwarded_args
    assert 'autostart' in forwarded_args
    assert 'localization_params_file' in forwarded_args
    assert 'nav2_params_file' in forwarded_args
    assert 'bt_xml' in forwarded_args
    assert 'use_foxglove' in forwarded_args
    assert 'log_level' in forwarded_args
    assert 'serial_port' in forwarded_args
    assert 'baud_rate' in forwarded_args
    assert 'response_timeout_ms' in forwarded_args
    assert 'use_mock_hardware' in forwarded_args
    assert 'lidar_odom_frame' in forwarded_args
    assert 'publish_odom_tf' in forwarded_args
    assert 'invert_odom_tf' in forwarded_args
    assert 'lidar_topic' in forwarded_args
    assert 'wheel_odom_topic' in forwarded_args


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

    # 3. Navigation controller_server -> diff_drive_controller direct chain
    nav_launch = ws_root / 'src' / 'mobile_base_navigation' / 'launch' / 'navigation.launch.py'
    assert nav_launch.exists()
    with open(nav_launch, 'r', encoding='utf-8') as f:
        nav_launch_text = f.read()

    assert "'/cmd_vel_nav'" not in nav_launch_text
    assert "'/diff_drive_controller/cmd_vel'" in nav_launch_text
