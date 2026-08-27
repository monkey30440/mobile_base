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

"""Automated tests for canonical mobile_base bringup launch entry and site resolution."""

import importlib.util
from pathlib import Path

from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
import pytest


def _load_module(file_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_path(include: IncludeLaunchDescription) -> str:
    source = include.launch_description_source
    substitutions = source._LaunchDescriptionSource__location
    return ''.join(getattr(part, 'text', str(part)) for part in substitutions)


@pytest.fixture
def bringup_module(monkeypatch):
    pkg_dir = Path(__file__).resolve().parent.parent
    mod = _load_module(
        pkg_dir / 'launch' / 'mobile_base.launch.py',
        'mobile_base_bringup_canonical_launch',
    )
    monkeypatch.setattr(
        mod,
        'get_package_share_directory',
        lambda package: f'/opt/ros/share/{package}',
    )
    return mod


@pytest.fixture
def site_res_module():
    pkg_dir = Path(__file__).resolve().parent.parent
    return _load_module(
        pkg_dir / 'launch' / 'site_resolution.py',
        'mobile_base_bringup_site_res_module',
    )


def test_site_resolution_find_maps_root_and_resolve_site(site_res_module, tmp_path, monkeypatch):
    """Verify site directory resolution across environment variables and file structure."""
    maps_root = tmp_path / 'maps'
    test_site = maps_root / 'site_alpha'
    test_site.mkdir(parents=True)
    (test_site / 'map.yaml').write_text('image: map.pgm\n', encoding='utf-8')
    (test_site / 'route_graph.geojson').write_text('{}', encoding='utf-8')

    monkeypatch.setenv('MOBILE_BASE_MAPS_DIR', str(maps_root))
    assert site_res_module.find_maps_root() == maps_root

    resolved = site_res_module.resolve_site_dir('site_alpha')
    assert resolved == test_site

    with pytest.raises(FileNotFoundError, match='not found'):
        site_res_module.resolve_site_dir('non_existent_site')

    with pytest.raises(ValueError, match='empty'):
        site_res_module.resolve_site_dir('   ')


def test_site_resolution_navigation_resources(site_res_module, tmp_path, monkeypatch):
    """Verify map and route_graph resolution with precedence rules."""
    maps_root = tmp_path / 'maps'
    test_site = maps_root / 'warehouse'
    test_site.mkdir(parents=True)
    site_map = test_site / 'map.yaml'
    site_rg = test_site / 'route_graph.geojson'
    site_map.write_text('image: map.pgm\n', encoding='utf-8')
    site_rg.write_text('{}', encoding='utf-8')

    monkeypatch.setenv('MOBILE_BASE_MAPS_DIR', str(maps_root))

    # 1. Site resolution without overrides
    m, rg = site_res_module.resolve_navigation_resources(site_name='warehouse')
    assert m == str(site_map)
    assert rg == str(site_rg)

    # 2. Explicit map override takes precedence over site
    custom_map = tmp_path / 'custom_map.yaml'
    custom_map.write_text('image: custom.pgm\n', encoding='utf-8')
    m, rg = site_res_module.resolve_navigation_resources(
        site_name='warehouse', map_override=str(custom_map)
    )
    assert m == str(custom_map)
    assert rg == str(site_rg)

    # 3. Explicit route_graph override takes precedence over site
    custom_rg = tmp_path / 'custom_rg.geojson'
    custom_rg.write_text('{}', encoding='utf-8')
    m, rg = site_res_module.resolve_navigation_resources(
        site_name='warehouse', route_graph_override=str(custom_rg)
    )
    assert m == str(site_map)
    assert rg == str(custom_rg)

    # 4. Map override without site
    m, rg = site_res_module.resolve_navigation_resources(map_override=str(custom_map))
    assert m == str(custom_map)
    assert rg == ''

    # 5. Missing site & missing map -> ValueError
    with pytest.raises(ValueError, match='Navigation mode requires'):
        site_res_module.resolve_navigation_resources(site_name='', map_override='')

    # 6. Non-existent explicit map -> FileNotFoundError
    with pytest.raises(FileNotFoundError, match='Explicit map file not found'):
        site_res_module.resolve_navigation_resources(map_override='/invalid/path/map.yaml')

    # 7. Non-existent explicit route_graph -> FileNotFoundError
    with pytest.raises(FileNotFoundError, match='Explicit route_graph file not found'):
        site_res_module.resolve_navigation_resources(
            site_name='warehouse', route_graph_override='/invalid/path/rg.geojson'
        )

    # 8. Site missing map.yaml -> FileNotFoundError
    empty_site = maps_root / 'empty_site'
    empty_site.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match='missing required map file'):
        site_res_module.resolve_navigation_resources(site_name='empty_site')


def test_canonical_launch_description_declared_arguments(bringup_module):
    """Verify all canonical high-level and low-level launch arguments are declared."""
    ld = bringup_module.generate_launch_description()
    assert isinstance(ld, LaunchDescription)

    args = {
        entity.name: entity
        for entity in ld.entities
        if isinstance(entity, DeclareLaunchArgument)
    }

    expected_args = {
        # High-level selections
        'variant',
        'platform',
        'mode',
        'site',
        # Low-level overrides
        'map',
        'route_graph',
        'localization_params_file',
        'nav2_params_file',
        'mapping_params_file',
        'bt_xml',
        # Common runtime
        'use_sim_time',
        'use_foxglove',
        'autostart',
        'log_level',
        # Hardware base control
        'serial_port',
        'baud_rate',
        'response_timeout_ms',
        'use_mock_hardware',
        # Kinematic-ICP / odometry
        'lidar_odom_frame',
        'publish_odom_tf',
        'invert_odom_tf',
        'lidar_topic',
        'wheel_odom_topic',
    }

    assert expected_args.issubset(set(args))
    assert args['variant'].default_value[0].text == 'default'
    assert args['platform'].default_value[0].text == 'real'
    assert args['mode'].default_value[0].text == 'mapping'
    assert args['use_foxglove'].default_value[0].text == 'false'
    assert args['use_sim_time'].default_value[0].text == 'false'


def test_canonical_launch_validation_rejects_invalid_arguments(bringup_module):
    """Verify fast failure on invalid variant, platform, or mode."""
    context = LaunchContext()

    # 1. Invalid variant
    context.launch_configurations.update({
        'variant': 'mb02',
        'platform': 'real',
        'mode': 'mapping',
        'site': '',
        'map': '',
        'route_graph': '',
        'use_sim_time': 'false',
    })
    with pytest.raises(ValueError, match="Unsupported variant 'mb02'"):
        bringup_module.launch_setup(context)

    # 2. Invalid platform (including sim)
    context.launch_configurations.update({
        'variant': 'default',
        'platform': 'sim',
        'mode': 'mapping',
    })
    with pytest.raises(ValueError, match="Unsupported platform 'sim'"):
        bringup_module.launch_setup(context)

    # 3. Invalid mode
    context.launch_configurations.update({
        'variant': 'default',
        'platform': 'real',
        'mode': 'invalid_mode',
    })
    with pytest.raises(ValueError, match="Invalid mode 'invalid_mode'"):
        bringup_module.launch_setup(context)


def test_canonical_mapping_composition(bringup_module):
    """Verify Mapping Mode composition includes common + mapping stack and excludes navigation."""
    context = LaunchContext()
    context.launch_configurations.update({
        'variant': 'default',
        'platform': 'real',
        'mode': 'mapping',
        'site': '',
        'map': '',
        'route_graph': '',
        'use_sim_time': 'false',
        'use_mock_hardware': 'false',
        'serial_port': '/dev/ttyUSB0',
        'baud_rate': '230400',
        'response_timeout_ms': '50',
        'lidar_odom_frame': 'odom',
        'publish_odom_tf': 'false',
        'invert_odom_tf': 'false',
        'lidar_topic': '/scan_front',
        'wheel_odom_topic': '/diff_drive_controller/odom',
        'mapping_params_file': '/opt/ros/share/mobile_base_mapping/config/slam_toolbox.yaml',
        'use_foxglove': 'false',
    })

    entities = bringup_module.launch_setup(context)
    includes = [e for e in entities if isinstance(e, IncludeLaunchDescription)]
    paths = [_source_path(inc) for inc in includes]

    expected_includes = {
        'mobile_base_control/launch/base_control.launch.py',
        'mobile_base_perception/launch/tdk_imu.launch.py',
        'mobile_base_perception/launch/sick_dual_lidar.launch.py',
        'kinematic_icp/launch/kinematic_icp.launch.py',
        'mobile_base_state_estimation/launch/ekf.launch.py',
        'mobile_base_mapping/launch/mapping.launch.py',
        'foxglove_bridge/launch/foxglove_bridge_launch.xml',
    }
    assert len(includes) == len(expected_includes)
    assert all(any(path.endswith(suffix) for path in paths) for suffix in expected_includes)

    # Prohibited subsystems in mapping mode
    assert not any('mobile_base_localization' in p for p in paths)
    assert not any('mobile_base_navigation' in p for p in paths)
    assert not any('amcl' in p for p in paths)

    # Foxglove condition check
    foxglove = next(inc for inc, p in zip(includes, paths) if 'foxglove' in p)
    assert isinstance(foxglove.condition, IfCondition)


def test_canonical_navigation_composition(bringup_module, monkeypatch, tmp_path):
    """Verify Navigation Mode composition includes common + localization + navigation stack."""
    maps_root = tmp_path / 'maps'
    test_site = maps_root / 'test_site'
    test_site.mkdir(parents=True)
    (test_site / 'map.yaml').write_text('image: map.pgm\n', encoding='utf-8')
    (test_site / 'route_graph.geojson').write_text('{}', encoding='utf-8')

    monkeypatch.setenv('MOBILE_BASE_MAPS_DIR', str(maps_root))

    loc_params = '/opt/ros/share/mobile_base_localization/config/amcl_params.yaml'
    nav_params = '/opt/ros/share/mobile_base_navigation/config/nav2_params.yaml'
    bt_xml = '/opt/ros/share/mobile_base_navigation/behavior_trees/route_assisted_nav.xml'

    context = LaunchContext()
    context.launch_configurations.update({
        'variant': 'default',
        'platform': 'real',
        'mode': 'navigation',
        'site': 'test_site',
        'map': '',
        'route_graph': '',
        'use_sim_time': 'false',
        'use_mock_hardware': 'false',
        'serial_port': '/dev/ttyUSB0',
        'baud_rate': '230400',
        'response_timeout_ms': '50',
        'lidar_odom_frame': 'odom',
        'publish_odom_tf': 'false',
        'invert_odom_tf': 'false',
        'lidar_topic': '/scan_front',
        'wheel_odom_topic': '/diff_drive_controller/odom',
        'localization_params_file': loc_params,
        'nav2_params_file': nav_params,
        'bt_xml': bt_xml,
        'autostart': 'true',
        'log_level': 'info',
        'use_foxglove': 'false',
    })

    entities = bringup_module.launch_setup(context)
    includes = [e for e in entities if isinstance(e, IncludeLaunchDescription)]
    paths = [_source_path(inc) for inc in includes]

    expected_includes = {
        'mobile_base_control/launch/base_control.launch.py',
        'mobile_base_perception/launch/tdk_imu.launch.py',
        'mobile_base_perception/launch/sick_dual_lidar.launch.py',
        'kinematic_icp/launch/kinematic_icp.launch.py',
        'mobile_base_state_estimation/launch/ekf.launch.py',
        'mobile_base_localization/launch/localization.launch.py',
        'mobile_base_navigation/launch/navigation.launch.py',
        'foxglove_bridge/launch/foxglove_bridge_launch.xml',
    }
    assert len(includes) == len(expected_includes)
    assert all(any(path.endswith(suffix) for path in paths) for suffix in expected_includes)

    # Prohibited subsystems in navigation mode
    assert not any('mobile_base_mapping' in p for p in paths)
    assert not any('slam_toolbox' in p for p in paths)

    # Verify site resource forwarding
    loc_inc = next(inc for inc, p in zip(includes, paths) if 'localization' in p)
    loc_args = dict(loc_inc.launch_arguments)
    assert loc_args['map'] == str(test_site / 'map.yaml')

    nav_inc = next(inc for inc, p in zip(includes, paths) if 'mobile_base_navigation' in p)
    nav_args = dict(nav_inc.launch_arguments)
    assert nav_args['route_graph'] == str(test_site / 'route_graph.geojson')
