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

"""Regression tests for Kinematic-ICP Launch Parameter Precedence and Resolution."""

import importlib.util
from pathlib import Path

from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters
import yaml


def _load_launch_module(launch_file_path: Path):
    spec = importlib.util.spec_from_file_location(
        launch_file_path.stem, str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _source_path(include: IncludeLaunchDescription) -> str:
    source = include.launch_description_source
    substitutions = source._LaunchDescriptionSource__location
    return ''.join(getattr(part, 'text', str(part)) for part in substitutions)


def test_common_args_default_contract():
    """Verify common_args.launch.py defaults match mobile_base approved architecture."""
    ws_root = _get_workspace_root()
    common_args_path = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'launch' / 'common_args.launch.py'
    )
    assert common_args_path.exists()
    module = _load_launch_module(common_args_path)
    ld = module.generate_launch_description()

    args = {
        entity.name: entity.default_value[0].text
        for entity in ld.entities
        if isinstance(entity, DeclareLaunchArgument) and entity.default_value is not None
    }

    assert args.get('lidar_odom_frame') == 'odom'
    assert args.get('publish_odom_tf') == 'false'
    assert args.get('invert_odom_tf') == 'false'
    assert args.get('use_2d_lidar') == 'true'
    assert args.get('lidar_topic') == '/scan_front'
    assert args.get('wheel_odom_topic') == '/diff_drive_controller/odom'
    assert args.get('wheel_odom_frame') == 'odom'
    assert args.get('base_frame') == 'base_footprint'


def test_yaml_wildcard_applicability_and_values():
    """Verify kinematic_icp_ros.yaml uses wildcard scope and approved defaults."""
    ws_root = _get_workspace_root()
    yaml_path = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'config' / 'kinematic_icp_ros.yaml'
    )
    assert yaml_path.exists()
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    assert '/**' in data, 'YAML must use wildcard /** scope to avoid node naming mismatch'
    params = data['/**']['ros__parameters']

    assert params['lidar_odom_frame'] == 'odom'
    assert params['publish_odom_tf'] is False
    assert params['invert_odom_tf'] is False
    assert params['use_2d_lidar'] is True
    assert params['lidar_topic'] == '/scan_front'
    assert params['wheel_odom_topic'] == '/diff_drive_controller/odom'
    assert params['base_frame'] == 'base_footprint'


def test_kinematic_icp_launch_effective_defaults():
    """Verify kinematic_icp.launch.py resolves to approved defaults without extra arguments."""
    ws_root = _get_workspace_root()
    launch_path = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'launch' / 'kinematic_icp.launch.py'
    )
    assert launch_path.exists()
    module = _load_launch_module(launch_path)

    ld = module.generate_launch_description()
    context = LaunchContext()

    # Find DeclareLaunchArgument entities and populate context with default values
    for entity in ld.entities:
        if isinstance(entity, DeclareLaunchArgument):
            entity.execute(context)

    # Find the Kinematic-ICP Node entity
    node = next(
        entity for entity in ld.entities
        if isinstance(entity, Node) and entity._Node__node_name == 'kinematic_icp_online_node'
    )

    # Evaluate the parameter dictionary passed to the node
    param_dict = next(
        item for item in evaluate_parameters(context, node._Node__parameters)
        if isinstance(item, dict)
    )

    assert param_dict['lidar_odom_frame'] == 'odom'
    assert param_dict['publish_odom_tf'] is False
    assert param_dict['invert_odom_tf'] is False
    assert param_dict['lidar_topic'] == '/scan_front'
    assert param_dict['wheel_odom_topic'] == '/diff_drive_controller/odom'
    assert param_dict['use_2d_lidar'] is True
    assert param_dict['wheel_odom_frame'] == 'odom'
    assert param_dict['base_frame'] == 'base_footprint'


def test_kinematic_icp_launch_cli_override():
    """Verify kinematic_icp.launch.py accepts and forwards CLI overrides."""
    ws_root = _get_workspace_root()
    launch_path = (
        ws_root / 'src' / 'kinematic_icp' / 'ros' / 'launch' / 'kinematic_icp.launch.py'
    )
    module = _load_launch_module(launch_path)

    ld = module.generate_launch_description()
    context = LaunchContext()
    for entity in ld.entities:
        if isinstance(entity, DeclareLaunchArgument):
            entity.execute(context)
    context.launch_configurations.update({
        'lidar_odom_frame': 'custom_odom',
        'publish_odom_tf': 'true',
        'invert_odom_tf': 'true',
        'lidar_topic': '/custom_scan',
    })

    node = next(
        entity for entity in ld.entities
        if isinstance(entity, Node) and entity._Node__node_name == 'kinematic_icp_online_node'
    )

    param_dict = next(
        item for item in evaluate_parameters(context, node._Node__parameters)
        if isinstance(item, dict)
    )

    assert param_dict['lidar_odom_frame'] == 'custom_odom'
    assert param_dict['publish_odom_tf'] is True
    assert param_dict['invert_odom_tf'] is True
    assert param_dict['lidar_topic'] == '/custom_scan'


def test_canonical_mapping_launch_forwards_kinematic_icp_arguments(monkeypatch):
    """Verify canonical mapping.launch.py forwards Kinematic-ICP arguments."""
    ws_root = _get_workspace_root()
    launch_path = (
        ws_root / 'src' / 'mobile_base_bringup' / 'launch' / 'mapping.launch.py'
    )
    module = _load_launch_module(launch_path)
    monkeypatch.setattr(
        module,
        'get_package_share_directory',
        lambda package: f'/opt/ros/share/{package}',
    )

    ld = module.generate_launch_description()
    args = {
        entity.name: entity.default_value[0].text
        for entity in ld.entities
        if isinstance(entity, DeclareLaunchArgument) and entity.default_value is not None
    }

    assert args.get('lidar_odom_frame') == 'odom'
    assert args.get('publish_odom_tf') == 'false'
    assert args.get('invert_odom_tf') == 'false'
    assert args.get('lidar_topic') == '/scan_front'
    assert args.get('wheel_odom_topic') == '/diff_drive_controller/odom'

    includes = [
        entity for entity in ld.entities
        if isinstance(entity, IncludeLaunchDescription)
    ]
    kicp_include = next(
        inc for inc in includes
        if _source_path(inc).endswith('kinematic_icp/launch/kinematic_icp.launch.py')
    )
    assert kicp_include.launch_arguments is not None
    forwarded = dict(kicp_include.launch_arguments)
    assert 'lidar_odom_frame' in forwarded
    assert 'publish_odom_tf' in forwarded
    assert 'invert_odom_tf' in forwarded
    assert 'lidar_topic' in forwarded
    assert 'wheel_odom_topic' in forwarded


def test_canonical_navigation_launch_forwards_kinematic_icp_arguments(monkeypatch):
    """Verify canonical navigation.launch.py forwards Kinematic-ICP arguments."""
    ws_root = _get_workspace_root()
    launch_path = (
        ws_root / 'src' / 'mobile_base_bringup' / 'launch' / 'navigation.launch.py'
    )
    module = _load_launch_module(launch_path)
    monkeypatch.setattr(
        module,
        'get_package_share_directory',
        lambda package: f'/opt/ros/share/{package}',
    )

    ld = module.generate_launch_description()
    args = {
        entity.name: entity.default_value[0].text
        for entity in ld.entities
        if isinstance(entity, DeclareLaunchArgument) and entity.default_value is not None
    }

    assert args.get('lidar_odom_frame') == 'odom'
    assert args.get('publish_odom_tf') == 'false'
    assert args.get('invert_odom_tf') == 'false'
    assert args.get('lidar_topic') == '/scan_front'
    assert args.get('wheel_odom_topic') == '/diff_drive_controller/odom'

    includes = [
        entity for entity in ld.entities
        if isinstance(entity, IncludeLaunchDescription)
    ]
    kicp_include = next(
        inc for inc in includes
        if _source_path(inc).endswith('kinematic_icp/launch/kinematic_icp.launch.py')
    )
    assert kicp_include.launch_arguments is not None
    forwarded = dict(kicp_include.launch_arguments)
    assert 'lidar_odom_frame' in forwarded
    assert 'publish_odom_tf' in forwarded
    assert 'invert_odom_tf' in forwarded
    assert 'lidar_topic' in forwarded
    assert 'wheel_odom_topic' in forwarded
