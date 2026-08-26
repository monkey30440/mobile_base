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

"""Unit and contract tests for Collision Scan Self-Filter in Perception subsystem."""

import importlib.util
from pathlib import Path

from launch import LaunchContext, LaunchDescription
from launch_ros.actions import Node
import yaml


def _load_launch_module(launch_file_path: Path):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'dual_laser_merger_launch', str(launch_file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collision_scan_filter_yaml_contract():
    """Verify that collision_scan_filter.yaml defines LaserScanBoxFilter with valid bounds."""
    pkg_dir = Path(__file__).resolve().parent.parent
    config_path = pkg_dir / 'config' / 'collision_scan_filter.yaml'
    assert config_path.exists(), f'Filter config not found: {config_path}'

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    assert 'collision_scan_filter' in data or 'scan_to_scan_filter_chain' in data
    node_key = 'collision_scan_filter' if 'collision_scan_filter' in data else 'scan_to_scan_filter_chain'
    params = data[node_key]['ros__parameters']
    assert 'filter1' in params
    f1 = params['filter1']

    assert f1['type'] == 'laser_filters/LaserScanBoxFilter'
    assert f1['name'] == 'robot_self_box_filter'

    box_params = f1['params']
    assert box_params['box_frame'] == 'base_link'
    assert box_params['min_x'] == -0.36
    assert box_params['max_x'] == 0.36
    assert box_params['min_y'] == -0.31
    assert box_params['max_y'] == 0.31
    assert box_params['min_z'] == -0.50
    assert box_params['max_z'] == 1.00
    assert box_params['invert'] is False


def test_dual_laser_merger_launch_includes_collision_scan_filter():
    """Verify that dual_laser_merger.launch.py launches both merger and collision_scan_filter."""
    pkg_dir = Path(__file__).resolve().parent.parent
    launch_path = pkg_dir / 'launch' / 'dual_laser_merger.launch.py'
    assert launch_path.exists(), f'Launch file not found: {launch_path}'

    module = _load_launch_module(launch_path)
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription)

    node_actions = [
        action for action in ld.entities
        if isinstance(action, Node)
    ]
    node_names = {node._Node__node_name for node in node_actions}
    assert 'dual_laser_merger_node' in node_names
    assert 'collision_scan_filter' in node_names

    filter_node = next(n for n in node_actions if n._Node__node_name == 'collision_scan_filter')
    assert filter_node._Node__package == 'laser_filters'
    assert filter_node._Node__node_executable == 'scan_to_scan_filter_chain'

    # Check topic remappings
    context = LaunchContext()
    context.launch_configurations['merged_scan_topic'] = '/scan'
    context.launch_configurations['collision_scan_topic'] = '/scan_collision'

    remap_dict = {}
    for src, dst in filter_node._Node__remappings:
        src_str = ''.join(p.perform(context) for p in src)
        dst_str = ''.join(p.perform(context) for p in dst)
        remap_dict[src_str] = dst_str

    assert remap_dict.get('scan') == '/scan'
    assert remap_dict.get('scan_filtered') == '/scan_collision'


def test_nav2_collision_monitor_source_topic_contract():
    """Verify that nav2_params.yaml connects collision_monitor to /scan_collision."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    nav2_params_path = repo_root / 'src' / 'mobile_base_navigation' / 'config' / 'nav2_params.yaml'
    assert nav2_params_path.exists(), f'Nav2 params not found: {nav2_params_path}'

    with open(nav2_params_path, 'r', encoding='utf-8') as f:
        nav2_data = yaml.safe_load(f)

    cm_params = nav2_data['collision_monitor']['ros__parameters']
    assert cm_params['scan']['topic'] == '/scan_collision'
    assert cm_params['source_timeout'] == 3.0

    # Verify authoritative /scan consumers remain untouched
    gc_params = nav2_data['global_costmap']['global_costmap']['ros__parameters']
    assert gc_params['obstacle_layer']['scan']['topic'] == '/scan'

    lc_params = nav2_data['local_costmap']['local_costmap']['ros__parameters']
    assert lc_params['obstacle_layer']['scan']['topic'] == '/scan'
