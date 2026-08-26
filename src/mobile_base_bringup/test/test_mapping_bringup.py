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

"""Narrow structural tests for the project-owned Mapping bringup."""

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition


def _load_launch_module(launch_file_path: Path):
    spec = importlib.util.spec_from_file_location(
        'mobile_base_bringup_mapping_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_path(include: IncludeLaunchDescription) -> str:
    source = include.launch_description_source
    substitutions = source._LaunchDescriptionSource__location
    return ''.join(getattr(part, 'text', str(part)) for part in substitutions)


def test_mapping_launch_composes_mapping_mode_without_duplicate_description(monkeypatch):
    """Catch missing child launches or duplicate/prohibited mode composition."""
    pkg_dir = Path(__file__).resolve().parent.parent
    module = _load_launch_module(pkg_dir / 'launch' / 'mapping.launch.py')
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
    assert set(arguments) == {
        'use_foxglove',
        'lidar_odom_frame',
        'publish_odom_tf',
        'invert_odom_tf',
        'lidar_topic',
        'wheel_odom_topic',
    }
    assert arguments['use_foxglove'].default_value[0].text == 'false'

    includes = [
        entity for entity in launch_description.entities
        if isinstance(entity, IncludeLaunchDescription)
    ]
    paths = [_source_path(include) for include in includes]
    expected_suffixes = {
        'mobile_base_control/launch/base_control.launch.py',
        'mobile_base_perception/launch/tdk_imu.launch.py',
        'mobile_base_perception/launch/sick_dual_lidar.launch.py',
        'mobile_base_perception/launch/dual_laser_merger.launch.py',
        'kinematic_icp/launch/kinematic_icp.launch.py',
        'mobile_base_state_estimation/launch/ekf.launch.py',
        'mobile_base_mapping/launch/mapping.launch.py',
        'foxglove_bridge/launch/foxglove_bridge_launch.xml',
    }
    assert len(includes) == len(expected_suffixes)
    assert all(any(path.endswith(suffix) for path in paths) for suffix in expected_suffixes)

    assert not any('mobile_base_description' in path for path in paths)
    assert not any('mobile_base_localization' in path for path in paths)
    assert not any('nav2_bringup' in path for path in paths)
    assert not any('rf2o' in path.lower() for path in paths)

    foxglove = next(include for include, path in zip(includes, paths) if 'foxglove' in path)
    assert isinstance(foxglove.condition, IfCondition)
    assert all(include.condition is None for include in includes if include is not foxglove)


def test_package_declares_direct_launch_import_dependencies():
    """Catch a clean installation missing a directly imported runtime package."""
    package_dir = Path(__file__).resolve().parent.parent
    root = ET.parse(package_dir / 'package.xml').getroot()
    runtime_dependencies = {
        element.text for element in root.findall('exec_depend')
    }
    assert 'ament_index_python' in runtime_dependencies
    assert 'mobile_base_description' in runtime_dependencies
    assert 'kinematic_icp' in runtime_dependencies
    assert 'rf2o_laser_odometry' not in runtime_dependencies
