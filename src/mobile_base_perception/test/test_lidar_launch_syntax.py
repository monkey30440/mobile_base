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

"""Unit and syntax tests for S2 dual SICK picoScan150 LiDAR launch and configuration."""

import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters
import pytest
import yaml


def _load_launch_module(launch_file_path: str):
    """Dynamically load launch python module from file path."""
    spec = importlib.util.spec_from_file_location(
        'sick_dual_lidar_launch', launch_file_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launch_description_generation():
    """Verify dual drivers feed handedness normalizers and box filters to public topics."""
    pkg_share = get_package_share_directory('mobile_base_perception')
    launch_file = os.path.join(pkg_share, 'launch', 'sick_dual_lidar.launch.py')

    module = _load_launch_module(launch_file)
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription), 'Generated object is not a LaunchDescription'

    node_actions = [a for a in ld.entities if isinstance(a, Node)]
    assert len(node_actions) == 6, f'Expected 6 Node actions, found {len(node_actions)}'

    node_names = {node._Node__node_name for node in node_actions}
    assert node_names == {
        'front_lidar_node',
        'rear_lidar_node',
        'front_scan_handedness_normalizer',
        'rear_scan_handedness_normalizer',
        'front_box_filter',
        'rear_box_filter',
    }, f'Bad nodes: {node_names}'

    # 1. Driver nodes
    driver_nodes = [n for n in node_actions if n._Node__package == 'sick_scan_xd']
    assert len(driver_nodes) == 2
    for node in driver_nodes:
        assert node._Node__package == 'sick_scan_xd', f'Node not sick_scan_xd: {node}'
        assert node._Node__node_executable == 'sick_generic_caller', f'Node not generic: {node}'

        argument_text = str(node._Node__arguments)
        assert 'imu_enable:=' in argument_text
        assert 'False' in argument_text
        assert 'start_sopas_service:=' in argument_text
        assert 'publish_laserscan_segment_topic:=' in argument_text
        assert 'custom_pointclouds:=' in argument_text
        assert '/sick_internal/' in argument_text
        assert "custom_pointclouds:=', 'none'" in argument_text
        assert 'tf_publish_rate:=' in argument_text
        assert '0.0' in argument_text
        assert 'tick_to_timestamp_mode:=' in argument_text
        assert "tick_to_timestamp_mode:=', '1'" in argument_text

    # 2. Normalizer nodes
    normalizer_nodes = {
        n._Node__node_name: n
        for n in node_actions
        if n._Node__package == 'mobile_base_perception'
    }
    assert len(normalizer_nodes) == 2
    context = LaunchContext()
    context.launch_configurations['front_topic'] = '/scan_front'
    context.launch_configurations['rear_topic'] = '/scan_rear'

    front_norm = normalizer_nodes['front_scan_handedness_normalizer']
    assert front_norm._Node__node_executable == 'scan_handedness_normalizer.py'
    front_norm_params = evaluate_parameters(context, front_norm._Node__parameters)[0]
    assert front_norm_params['input_topic'] == '/sick_internal/front_scan_raw'
    assert front_norm_params['output_topic'] == '/sick_internal/front_scan_normalized'
    assert front_norm_params['diagnostic_name'] == 'Front LiDAR'
    assert front_norm_params['hardware_id'] == 'front_lidar'

    rear_norm = normalizer_nodes['rear_scan_handedness_normalizer']
    assert rear_norm._Node__node_executable == 'scan_handedness_normalizer.py'
    rear_norm_params = evaluate_parameters(context, rear_norm._Node__parameters)[0]
    assert rear_norm_params['input_topic'] == '/sick_internal/rear_scan_raw'
    assert rear_norm_params['output_topic'] == '/sick_internal/rear_scan_normalized'
    assert rear_norm_params['diagnostic_name'] == 'Rear LiDAR'
    assert rear_norm_params['hardware_id'] == 'rear_lidar'

    # 3. Filter nodes
    filter_nodes = {
        n._Node__node_name: n
        for n in node_actions
        if n._Node__package == 'laser_filters'
    }
    assert len(filter_nodes) == 2

    def _resolve_remapping(node, context):
        resolved = {}
        for src, dst in node._Node__remappings:
            src_str = ''.join(
                s.perform(context) if hasattr(s, 'perform') else str(s) for s in src
            )
            dst_str = ''.join(
                s.perform(context) if hasattr(s, 'perform') else str(s) for s in dst
            )
            resolved[src_str] = dst_str
        return resolved

    front_filter = filter_nodes['front_box_filter']
    assert front_filter._Node__node_executable == 'scan_to_scan_filter_chain'
    front_remap = _resolve_remapping(front_filter, context)
    assert front_remap.get('scan') == '/sick_internal/front_scan_normalized'
    assert front_remap.get('scan_filtered') == '/scan_front'

    rear_filter = filter_nodes['rear_box_filter']
    assert rear_filter._Node__node_executable == 'scan_to_scan_filter_chain'
    rear_remap = _resolve_remapping(rear_filter, context)
    assert rear_remap.get('scan') == '/sick_internal/rear_scan_normalized'
    assert rear_remap.get('scan_filtered') == '/scan_rear'

    # 4. Feedback loop prevention
    assert front_norm_params['input_topic'] != front_norm_params['output_topic']
    assert rear_norm_params['input_topic'] != rear_norm_params['output_topic']
    assert front_remap['scan'] != front_remap['scan_filtered']
    assert rear_remap['scan'] != rear_remap['scan_filtered']
    assert front_remap['scan_filtered'] != '/sick_internal/front_scan_normalized'
    assert rear_remap['scan_filtered'] != '/sick_internal/rear_scan_normalized'

    # 5. Verify no production /scan or /scan_collision
    for remap in (front_remap, rear_remap):
        assert '/scan' not in remap.values()
        assert '/scan_collision' not in remap.values()

    # 6. Verify no forbidden packages
    forbidden_packages = {'dual_laser_merger', 'tf2_ros'}
    for node in node_actions:
        assert node._Node__package not in forbidden_packages


def test_laser_box_filter_config_syntax_and_parameters():
    """Verify laser_box_filter.yaml syntax and parameter values."""
    pkg_share = get_package_share_directory('mobile_base_perception')
    config_file = os.path.join(pkg_share, 'config', 'laser_box_filter.yaml')
    assert os.path.exists(config_file), f'Config file missing: {config_file}'

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # ROS 2 parameter root semantics: either wildcard /** or specific node names
    if '/**' in config:
        params = config['/**']['ros__parameters']
    elif 'front_box_filter' in config:
        params = config['front_box_filter']['ros__parameters']
    else:
        pytest.fail(f'Unsupported parameter root key in {config.keys()}')

    assert 'filter1' in params, 'filter1 definition missing'
    filter1 = params['filter1']
    assert filter1['type'] == 'laser_filters/LaserScanBoxFilter'
    assert filter1['name'] == 'box_filter'

    filter_params = filter1['params']
    assert filter_params['box_frame'] == 'base_link'
    assert filter_params['max_x'] == pytest.approx(0.35)
    assert filter_params['min_x'] == pytest.approx(-0.35)
    assert filter_params['max_y'] == pytest.approx(0.35)
    assert filter_params['min_y'] == pytest.approx(-0.35)
    assert filter_params['max_z'] == pytest.approx(0.60)
    assert filter_params['min_z'] == pytest.approx(-0.60)
    assert filter_params['invert'] is False


if __name__ == '__main__':
    pytest.main(['-v', __file__])
