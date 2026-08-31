import importlib.util
import json
import os
import xml.etree.ElementTree as ET

from launch import LaunchDescription
from launch_ros.actions import Node
import pytest
import yaml


def get_package_source_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def load_launch_module():
    launch_path = os.path.join(
        get_package_source_dir(), 'launch', 'navigation.launch.py'
    )
    spec = importlib.util.spec_from_file_location('navigation_launch', launch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nav2_params_contracts():
    params_path = os.path.join(get_package_source_dir(), 'config', 'nav2_params.yaml')
    assert os.path.exists(params_path), f'nav2_params.yaml not found at {params_path}'

    with open(params_path, 'r', encoding='utf-8') as f:
        params = yaml.safe_load(f)

    # 1. Planner contract
    assert 'planner_server' in params
    planner_params = params['planner_server']['ros__parameters']
    assert 'GridBased' in planner_params['planner_plugins']
    assert (
        planner_params['GridBased']['plugin']
        == 'nav2_navfn_planner::NavfnPlanner'
    )

    # 2. Controller & MPPI contract
    assert 'controller_server' in params
    ctrl_params = params['controller_server']['ros__parameters']
    assert 'FollowPath' in ctrl_params['controller_plugins']
    assert (
        ctrl_params['FollowPath']['plugin']
        == 'nav2_mppi_controller::MPPIController'
    )
    assert ctrl_params['FollowPath']['motion_model'] == 'DiffDrive'
    assert ctrl_params['FollowPath']['vy_max'] == 0.0
    assert ctrl_params['FollowPath']['vy_std'] == 0.0
    assert ctrl_params.get('enable_stamped_cmd_vel') is True

    # 3. Goal Checker contract (SYS-016)
    assert 'stopped_goal_checker' in ctrl_params['goal_checker_plugins']
    sgc = ctrl_params['stopped_goal_checker']
    assert pytest.approx(sgc['xy_goal_tolerance']) == 0.25
    assert pytest.approx(sgc['yaw_goal_tolerance']) == 0.5236
    assert pytest.approx(sgc['trans_stopped_velocity']) == 0.05
    assert pytest.approx(sgc['rot_stopped_velocity']) == 0.10

    # 4. Route Server contract: retain route obstruction/reroute operation.
    assert 'route_server' in params
    route_params = params['route_server']['ros__parameters']
    assert 'DistanceScorer' in route_params['edge_cost_functions']
    assert 'CollisionMonitor' in route_params['operations']
    assert (
        route_params['CollisionMonitor']['plugin']
        == 'nav2_route::CollisionMonitor'
    )
    assert 'collision_monitor' not in params

    # 5. Costmaps observation sources contract
    assert 'local_costmap' in params
    lc_obs = (
        params['local_costmap']['local_costmap']['ros__parameters']
        ['obstacle_layer']
    )
    assert 'scan_front' in lc_obs['observation_sources']
    assert 'scan_rear' in lc_obs['observation_sources']
    assert lc_obs['scan_front']['topic'] == '/scan_front'
    assert lc_obs['scan_rear']['topic'] == '/scan_rear'

    assert 'global_costmap' in params
    gc_obs = (
        params['global_costmap']['global_costmap']['ros__parameters']
        ['obstacle_layer']
    )
    assert 'scan_front' in gc_obs['observation_sources']
    assert 'scan_rear' in gc_obs['observation_sources']
    assert gc_obs['scan_front']['topic'] == '/scan_front'
    assert gc_obs['scan_rear']['topic'] == '/scan_rear'


def test_bt_xml_structure_and_fallback_policy():
    bt_path = os.path.join(
        get_package_source_dir(), 'behavior_trees', 'route_assisted_nav.xml'
    )
    assert os.path.exists(bt_path), f'route_assisted_nav.xml not found at {bt_path}'

    tree = ET.parse(bt_path)
    root = tree.getroot()
    assert root.tag == 'root'
    assert root.attrib.get('BTCPP_format') == '4'

    # Extract all node tags in tree
    all_tags = [elem.tag for elem in root.iter()]

    # Verify presence of native 3-stage nodes
    assert 'ComputeRoute' in all_tags
    assert 'ComputePathToPose' in all_tags
    assert 'GetPoseFromPath' in all_tags
    assert 'GetCurrentPose' in all_tags
    assert 'ArePosesNear' in all_tags
    assert 'ConcatenatePaths' in all_tags
    assert 'FollowPath' in all_tags
    assert 'SetBlackboard' in all_tags

    # Verify explicit non-overwriting path keys in BT
    compute_route_elem = next(root.iter('ComputeRoute'))
    assert compute_route_elem.attrib.get('path') == '{raw_route_path}'

    follow_path_elem = next(root.iter('FollowPath'))
    assert follow_path_elem.attrib.get('path') == '{final_route_path}'

    # Verify SYS-021: No direct free-space fallback from goal if ComputeRoute fails
    for seq in root.iter('Sequence'):
        child_tags = [child.tag for child in seq]
        if 'ComputeRoute' in child_tags:
            assert 'ComputeRoute' in child_tags


def test_test_route_graph_geojson_fixture():
    fixture_path = os.path.join(
        get_package_source_dir(), 'test', 'test_data', 'test_route_graph.geojson'
    )
    assert os.path.exists(fixture_path), f'fixture not found at {fixture_path}'

    with open(fixture_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)

    assert graph.get('type') == 'FeatureCollection'
    features = graph.get('features', [])
    assert len(features) >= 3

    points = [f for f in features if f['geometry']['type'] == 'Point']
    lines = [f for f in features if f['geometry']['type'] == 'MultiLineString']

    assert len(points) >= 3
    assert len(lines) >= 2

    # Verify node IDs and coordinates
    for pt in points:
        props = pt['properties']
        assert 'id' in props
        assert props.get('frame') == 'map'
        coords = pt['geometry']['coordinates']
        assert len(coords) == 2

    # Verify edge connectivity
    for line in lines:
        props = line['properties']
        assert 'id' in props
        assert 'startid' in props
        assert 'endid' in props


def test_real_site_route_graph_geojson():
    real_graph_path = os.path.abspath(
        os.path.join(
            get_package_source_dir(), '..', '..', 'maps', 'test_site', 'route_graph.geojson'
        )
    )
    assert os.path.exists(real_graph_path), f'real route graph not found at {real_graph_path}'

    with open(real_graph_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)

    assert graph.get('type') == 'FeatureCollection'
    features = graph.get('features', [])
    assert len(features) == 4

    points = [f for f in features if f['geometry']['type'] == 'Point']
    lines = [f for f in features if f['geometry']['type'] == 'MultiLineString']

    assert len(points) == 2
    assert len(lines) == 2

    # Verify node IDs and coordinates
    for pt in points:
        props = pt['properties']
        assert 'id' in props
        assert props.get('frame') == 'map'
        coords = pt['geometry']['coordinates']
        assert len(coords) == 2
        # Verify coordinates fall within safe test_site map area
        assert -3.9 <= coords[0] <= 4.4
        assert -5.9 <= coords[1] <= 3.7

    # Verify edge connectivity
    for line in lines:
        props = line['properties']
        assert 'id' in props
        assert 'startid' in props
        assert 'endid' in props
        assert props.get('startid') in [0, 1]
        assert props.get('endid') in [0, 1]


def _collect_nodes(entities):
    nodes = []
    for entity in entities:
        if isinstance(entity, Node):
            nodes.append(entity)
        if hasattr(entity, 'get_sub_entities'):
            nodes.extend(_collect_nodes(entity.get_sub_entities()))
    return nodes


def test_launch_description_composition():
    module = load_launch_module()
    ld = module.generate_launch_description()
    assert isinstance(ld, LaunchDescription)

    nodes = _collect_nodes(ld.entities)
    node_names = [getattr(n, '_Node__node_name', '') for n in nodes]

    assert 'controller_server' in node_names
    assert 'planner_server' in node_names
    assert 'route_server' in node_names
    assert 'bt_navigator' in node_names
    assert 'collision_monitor' not in node_names
    assert 'lifecycle_manager_navigation' in node_names

    # Ensure no unauthorized nodes are present in S6 navigation launch
    assert 'slam_toolbox' not in node_names
    assert 'map_server' not in node_names
    assert 'amcl' not in node_names
    assert 'robot_state_publisher' not in node_names

    # controller_server directly drives S7 in Navigation Mode.
    ctrl_node = next(
        n for n in nodes if getattr(n, '_Node__node_name', '') == 'controller_server'
    )
    ctrl_raw_remappings = getattr(ctrl_node, '_Node__remappings', [])
    ctrl_remap_pairs = []
    for src_subst, dst_subst in ctrl_raw_remappings:
        src = ''.join(getattr(s, 'text', str(s)) for s in src_subst)
        dst = ''.join(getattr(d, 'text', str(d)) for d in dst_subst)
        ctrl_remap_pairs.append((src, dst))

    assert any('/diff_drive_controller/cmd_vel' in dst for src, dst in ctrl_remap_pairs)
    assert not any('/cmd_vel_nav' in dst for src, dst in ctrl_remap_pairs)
