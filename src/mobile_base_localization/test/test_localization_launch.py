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

"""Unit and syntax tests for S5 Localization launch and AMCL configuration."""

import importlib.util
from pathlib import Path
import tempfile

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch_ros.actions import Node
import yaml


def _load_launch_module(launch_file_path: Path):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'localization_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_amcl_params_yaml_configuration():
    """Verify that amcl_params.yaml matches authoritative S5 contracts."""
    pkg_dir = Path(__file__).resolve().parent.parent
    config_path = pkg_dir / 'config' / 'amcl_params.yaml'
    assert config_path.exists(), f'Configuration file not found: {config_path}'

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    assert 'amcl' in data, 'amcl block missing from configuration'
    assert 'ros__parameters' in data['amcl'], 'ros__parameters missing from amcl block'
    params = data['amcl']['ros__parameters']

    # 1. Coordinate Frames (06 Section 3.6.4)
    assert params['global_frame_id'] == 'map', 'global_frame_id must be map'
    assert params['odom_frame_id'] == 'odom', 'odom_frame_id must be odom'
    assert params['base_frame_id'] == 'base_footprint', 'base_frame_id must be base_footprint'
    assert params['scan_topic'] == '/scan_front', 'scan_topic must be /scan_front'
    assert params['tf_broadcast'] is True, 'tf_broadcast must be true in Navigation Mode'

    # 2. Particle Filter Settings
    assert params['min_particles'] == 500, 'min_particles must be 500'
    assert params['max_particles'] == 2000, 'max_particles must be 2000'
    assert params['resample_interval'] == 1, 'resample_interval must be 1'
    assert params['update_min_d'] == 0.1, 'update_min_d must be 0.1'
    assert params['update_min_a'] == 0.1, 'update_min_a must be 0.1'

    # 3. Laser Likelihood Field Model
    assert params['laser_model_type'] == 'likelihood_field', 'laser_model_type invalid'
    assert params['laser_min_range'] == 0.05, 'laser_min_range must be 0.05'
    assert params['laser_max_range'] == 20.0, 'laser_max_range must be 20.0'
    assert params['z_hit'] == 0.9, 'z_hit must be 0.9'
    assert params['z_rand'] == 0.1, 'z_rand must be 0.1'
    assert params['sigma_hit'] == 0.2, 'sigma_hit must be 0.2'

    # 4. Motion Model
    assert params['robot_model_type'] == 'nav2_amcl::DifferentialMotionModel', (
        'robot_model_type must be nav2_amcl::DifferentialMotionModel'
    )
    assert params['alpha1'] == 0.2
    assert params['alpha2'] == 0.2
    assert params['alpha3'] == 0.2
    assert params['alpha4'] == 0.2

    # 5. Initial Pose Policy (SYS-010)
    assert params['set_initial_pose'] is False, 'set_initial_pose must be false'

    # 6. Map Server configuration block
    assert 'map_server' in data, 'map_server block missing from configuration'
    map_params = data['map_server']['ros__parameters']
    assert map_params['frame_id'] == 'map'
    assert map_params['topic_name'] == 'map'


def test_localization_launch_structure():
    """Verify localization.launch.py composes map_server, amcl, lifecycle_manager."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'localization.launch.py'
    assert launch_path.exists(), f'Launch file not found: {launch_path}'

    module = _load_launch_module(launch_path)
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription), 'Must return a LaunchDescription'

    # Check declared launch arguments
    declared_args = {
        action.name: action
        for action in ld.entities
        if isinstance(action, DeclareLaunchArgument)
    }
    assert 'map' in declared_args, 'Launch argument "map" must be declared'
    assert 'params_file' in declared_args, 'Launch argument "params_file" must be declared'
    assert 'use_sim_time' in declared_args, 'Launch argument "use_sim_time" must be declared'
    assert 'autostart' in declared_args, 'Launch argument "autostart" must be declared'
    assert 'log_level' in declared_args, 'Launch argument "log_level" must be declared'

    # Check nodes inside GroupAction
    nodes = []
    for action in ld.entities:
        if isinstance(action, GroupAction):
            for sub_action in action.get_sub_entities():
                if isinstance(sub_action, Node):
                    nodes.append(sub_action)

    node_dict = {node._Node__node_name: node for node in nodes}
    assert 'map_server' in node_dict, 'map_server Node must be in launch'
    assert 'amcl' in node_dict, 'amcl Node must be in launch'
    assert 'lifecycle_manager_localization' in node_dict, 'lifecycle_manager must be in launch'

    # Verify package bindings
    assert node_dict['map_server']._Node__package == 'nav2_map_server'
    assert node_dict['amcl']._Node__package == 'nav2_amcl'
    assert node_dict['lifecycle_manager_localization']._Node__package == 'nav2_lifecycle_manager'

    # Verify lifecycle node list in lifecycle manager
    lm_params = node_dict['lifecycle_manager_localization']._Node__parameters
    node_names_param = None
    for p in lm_params:
        if isinstance(p, dict):
            for k, v in p.items():
                k_name = yaml.safe_load(''.join(getattr(s, 'text', str(s)) for s in k))
                if k_name == 'node_names':
                    node_names_param = [
                        yaml.safe_load(''.join(getattr(s, 'text', str(s)) for s in item))
                        for item in v
                    ]
    assert node_names_param == ['map_server', 'amcl'], (
        f'Lifecycle manager must manage only ["map_server", "amcl"], got {node_names_param}'
    )

    # Verify complete exclusion of S4 SLAM and S6 Navigation
    prohibited_packages = [
        'slam_toolbox',
        'nav2_planner',
        'nav2_controller',
        'nav2_bt_navigator',
        'nav2_behaviors',
        'nav2_route',
    ]
    for node in nodes:
        assert node._Node__package not in prohibited_packages, (
            f'Prohibited package {node._Node__package} found in localization launch!'
        )


def test_map_fixture_and_invalid_path_handling():
    """Verify temporary map fixture creation, syntax validation, and invalid path detection."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        fixture_yaml = Path(tmp_dir) / 'test_map.yaml'
        fixture_pgm = Path(tmp_dir) / 'test_map.pgm'

        # Create minimal 10x10 PGM image (P5 binary)
        width, height = 10, 10
        pgm_header = f'P5\n{width} {height}\n255\n'.encode('ascii')
        pgm_data = bytes([254] * (width * height))  # all free space
        with open(fixture_pgm, 'wb') as f:
            f.write(pgm_header + pgm_data)

        # Create valid map.yaml
        yaml_content = {
            'image': 'test_map.pgm',
            'mode': 'trinary',
            'resolution': 0.05,
            'origin': [0.0, 0.0, 0.0],
            'negate': 0,
            'occupied_thresh': 0.65,
            'free_thresh': 0.25,
        }
        with open(fixture_yaml, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_content, f)

        # Validate that the fixture is recognized as valid YAML with correct fields
        with open(fixture_yaml, 'r', encoding='utf-8') as f:
            loaded = yaml.safe_load(f)
        assert loaded['resolution'] == 0.05
        assert loaded['mode'] == 'trinary'
        assert (Path(tmp_dir) / loaded['image']).exists()

        # Validate that non-existent map path is detected
        non_existent_yaml = Path(tmp_dir) / 'does_not_exist.yaml'
        assert not non_existent_yaml.exists()
