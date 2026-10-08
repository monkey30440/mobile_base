"""Public native Mapping workflow using a synthetic room, never hardware."""
import math
import os
from pathlib import Path
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import OccupancyGrid
from lifecycle_msgs.srv import GetState, ChangeState
from lifecycle_msgs.msg import State, Transition
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from sensor_msgs.msg import LaserScan
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformBroadcaster, TransformListener
import yaml
import pytest


@pytest.fixture(autouse=True)
def isolated_ros_domain(monkeypatch):
    # Observer and every native subprocess share a software-only domain.
    monkeypatch.setenv("ROS_DOMAIN_ID", "150")


def occupied_cells(grid):
    return [(grid.info.origin.position.x + (col + 0.5) * grid.info.resolution,
             grid.info.origin.position.y + (row + 0.5) * grid.info.resolution)
            for row in range(grid.info.height) for col in range(grid.info.width)
            if grid.data[row * grid.info.width + col] >= 65]


def endpoint_distance(scan, index, transform, occupied):
    q = transform.rotation
    angle = scan.angle_min + index * scan.angle_increment
    dx, dy = scan.ranges[index] * math.cos(angle), scan.ranges[index] * math.sin(angle)
    px = transform.translation.x + (1 - 2*(q.y*q.y + q.z*q.z))*dx + 2*(q.x*q.y - q.z*q.w)*dy
    py = transform.translation.y + 2*(q.x*q.y + q.z*q.w)*dx + (1 - 2*(q.x*q.x + q.z*q.z))*dy
    return min(math.hypot(px-x, py-y) for x, y in occupied)


def test_inverted_front_scan_map_tf_save_and_reload(tmp_path):
    rclpy.init()
    node = Node('mapping_fixture')
    maps, edges, latest_scan, first_observed_max = [], [], [], []
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(OccupancyGrid, '/map', maps.append, qos)
    node.create_subscription(TFMessage, '/tf', lambda m: edges.extend(
        t for t in m.transforms if t.header.frame_id == 'map' and t.child_frame_id == 'odom'), 100)
    scan_pub = node.create_publisher(LaserScan, '/lidar/fl/scan', 10)
    broadcaster = TransformBroadcaster(node)
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    # Use the actual packaged sensor geometry, not a made-up scan frame.
    model_path = Path(get_package_share_directory('mobile_base_description')) / 'urdf/mobile_base.urdf'
    model = ET.parse(model_path).getroot()
    joint = next(j for j in model.findall('joint')
                 if j.find('child').get('link') == 'base_lidar_link_FL')
    origin = joint.find('origin')
    offset = [float(v) for v in origin.get('xyz').split()]
    roll, pitch, sensor_yaw = [float(v) for v in origin.get('rpy').split()]
    assert abs(roll - math.pi) < 1e-5 and abs(pitch) < 1e-5
    model_config = tmp_path / 'model.yaml'
    model_config.write_text(yaml.safe_dump({'robot_state_publisher': {'ros__parameters': {
        'robot_description': model_path.read_text()}}}))
    logs, processes = [], []

    def start(args, name):
        log = open(tmp_path / (name + '.log'), 'w')
        logs.append(log)
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(process)
        return process

    def publish_room(x, y, yaw):
        stamp = node.get_clock().now().to_msg()
        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'base_footprint'
        transform.transform.translation.x = x
        transform.transform.translation.y = y
        transform.transform.rotation.z = math.sin(yaw / 2)
        transform.transform.rotation.w = math.cos(yaw / 2)
        broadcaster.sendTransform(transform)
        scan = LaserScan()
        scan.header.stamp = stamp
        scan.header.frame_id = 'base_lidar_link_FL_1'
        scan.angle_min = -2.4086289405822754
        scan.angle_increment = 0.00436333566904068
        scan.angle_max = scan.angle_min + 1199 * scan.angle_increment
        scan.range_min, scan.range_max = 0.05, 25.0
        scan.scan_time = 0.05
        room_yaw = 0.15
        sx = x + math.cos(yaw) * offset[0] - math.sin(yaw) * offset[1]
        sy = y + math.sin(yaw) * offset[0] + math.cos(yaw) * offset[1]
        sx, sy = (math.cos(room_yaw) * sx + math.sin(room_yaw) * sy,
                  -math.sin(room_yaw) * sx + math.cos(room_yaw) * sy)
        for i in range(1200):
            # Roll pi reverses angular direction in the base XY plane.
            angle = yaw + sensor_yaw - (scan.angle_min + i * scan.angle_increment) - room_yaw
            dx, dy = math.cos(angle), math.sin(angle)
            distances = []
            if abs(dx) > 1e-8:
                distances.append(((4.0 if dx > 0 else -8.0) - sx) / dx)
            if abs(dy) > 1e-8:
                distances.append(((2.0 if dy > 0 else -8.0) - sy) / dy)
            scan.ranges.append(min(distances))
        if not first_observed_max:
            first_observed_max.append(max(scan.ranges))
        latest_scan[:] = [scan]
        scan_pub.publish(scan)
        deadline = time.monotonic() + 0.05
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.005)

    try:
        start(['ros2', 'run', 'robot_state_publisher', 'robot_state_publisher',
               '--ros-args', '--params-file', str(model_config)], 'model')
        mapping = start(['ros2', 'launch', 'mobile_base_mapping', 'mapping.launch.py'], 'mapping')
        # Translation, rotation and revisit exercise the native inverted scan path.
        for step, pose in enumerate([(0.0, 0.0, 0.0), (0.0, 0.0, 2.6), (0.65, 0.0, 0.0),
                                     (0.65, 0.0, 0.65), (0.0, -0.65, -0.65), (0.0, 0.0, 0.0)]):
            pose_start = time.monotonic()
            deadline = pose_start + (12 if step == 1 else 6)
            while time.monotonic() < deadline:
                assert mapping.poll() is None, (tmp_path / 'mapping.log').read_text()
                if step == 1:
                    # Continuous turning provides overlapping views and repeated
                    # evidence for the native occupancy pass-through threshold.
                    publish_room(pose[0], pose[1], pose[2] * min(1.0, (time.monotonic() - pose_start) / 6))
                else:
                    publish_room(*pose)
            if step == 1:
                # Rotation reveals valid farther points before closer translated
                # views can fill these cells. Bounds must not cache scene extrema.
                assert maps
                grid = maps[-1]
                occupied = occupied_cells(grid)
                transform = buffer.lookup_transform('map', 'base_lidar_link_FL_1', rclpy.time.Time()).transform
                scan = latest_scan[0]
                distances = []
                for i in range(0, len(scan.ranges), 10):
                    if scan.ranges[i] <= first_observed_max[0] + 0.10:
                        continue
                    distances.append(endpoint_distance(scan, i, transform, occupied))
                assert distances, 'fixture must expose later valid points beyond first-frame extrema'
                fraction = sum(d < 0.20 for d in distances) / len(distances)
                (tmp_path / 'later-range-alignment.yaml').write_text(yaml.safe_dump({
                    'first_observed_max_m': first_observed_max[0], 'later_observed_max_m': max(scan.ranges),
                    'farther_point_count': len(distances), 'farther_point_alignment_fraction': fraction,
                    'map_stamp_s': grid.header.stamp.sec + grid.header.stamp.nanosec / 1e9,
                    'scan_stamp_s': scan.header.stamp.sec + scan.header.stamp.nanosec / 1e9,
                    'occupied_cells': len(occupied)}))
                assert fraction > 0.95, 'later valid farther points must enter the native occupancy map'
        assert maps, (tmp_path / 'mapping.log').read_text()
        assert edges, 'slam_toolbox must own map -> odom'
        state = node.create_client(GetState, '/slam_toolbox/get_state')
        assert state.wait_for_service(timeout_sec=5)
        active = state.call_async(GetState.Request())
        rclpy.spin_until_future_complete(node, active, timeout_sec=5)
        assert active.done() and active.result().current_state.id == State.PRIMARY_STATE_ACTIVE
        assert [i.node_name for i in node.get_subscriptions_info_by_topic('/lidar/fl/scan')] == ['slam_toolbox']
        assert not node.get_subscriptions_info_by_topic('/lidar/br/scan')
        assert {i.node_name for i in node.get_publishers_info_by_topic('/map')} == {'slam_toolbox'}
        assert not any(i.node_name == 'amcl' for i in node.get_publishers_info_by_topic('/tf'))
        sensor_tf = buffer.lookup_transform('map', 'base_lidar_link_FL_1', rclpy.time.Time()).transform
        grid = maps[-1]
        assert grid.header.frame_id == 'map'
        occupied = occupied_cells(grid)
        (tmp_path / 'occupied.yaml').write_text(yaml.safe_dump(occupied))
        assert len(occupied) > 100
        # The initial fixture pose defines map origin. A rotated/mirrored scan
        # would place these asymmetric walls elsewhere. Tolerance is fixture-only.
        room_yaw = 0.15
        room_cells = [(math.cos(room_yaw) * x + math.sin(room_yaw) * y,
                       -math.sin(room_yaw) * x + math.cos(room_yaw) * y) for x, y in occupied]
        aligned = [min(abs(x + 8), abs(x - 4), abs(y + 8), abs(y - 2)) < 0.15
                   for x, y in room_cells]
        assert sum(aligned) / len(aligned) > 0.95
        for x, y in [(-8, 0), (4, 0), (0, -8), (0, 2)]:
            assert min(math.hypot(px-x, py-y) for px, py in room_cells) < 0.20
        # Compare actual scan endpoints transformed through the complete model TF
        # against occupied cells, in the same map frame used by Foxglove.
        scan = latest_scan[0]
        distances = []
        for i in range(0, len(scan.ranges), 30):
            distances.append(endpoint_distance(scan, i, sensor_tf, occupied))
        assert sum(distance < 0.20 for distance in distances) / len(distances) > 0.95
        (tmp_path / 'alignment.yaml').write_text(yaml.safe_dump({
            'occupied_cells': len(occupied), 'wall_alignment_fraction': sum(aligned) / len(aligned),
            'scan_alignment_fraction': sum(d < 0.20 for d in distances) / len(distances),
            'scan_max_nearest_cell_m': max(distances)}))
        failed = subprocess.run(['ros2', 'run', 'nav2_map_server', 'map_saver_cli',
                                 '-f', str(tmp_path / 'missing-directory/map'), '--fmt', 'pgm'],
                                capture_output=True, text=True, timeout=15)
        assert failed.returncode != 0, failed.stdout + failed.stderr
        (tmp_path / 'save-failure.log').write_text(failed.stdout + failed.stderr)
        saved = subprocess.run(['ros2', 'run', 'nav2_map_server', 'map_saver_cli',
                                '-f', str(tmp_path / 'map'), '--fmt', 'pgm',
                                '--ros-args', '-p', 'save_map_timeout:=10.0'],
                               capture_output=True, text=True, timeout=20)
        (tmp_path / 'save.log').write_text(saved.stdout + saved.stderr)
        assert saved.returncode == 0, saved.stdout + saved.stderr
        metadata = yaml.safe_load((tmp_path / 'map.yaml').read_text())
        assert metadata['image'] == 'map.pgm'
        assert (tmp_path / 'map.pgm').is_file()
        os.killpg(mapping.pid, signal.SIGINT)
        mapping.wait(timeout=8)
        maps.clear()
        start(['ros2', 'run', 'nav2_map_server', 'map_server', '--ros-args',
               '-p', 'yaml_filename:=' + str(tmp_path / 'map.yaml')], 'reload')
        change = node.create_client(ChangeState, '/map_server/change_state')
        assert change.wait_for_service(timeout_sec=10), (tmp_path / 'reload.log').read_text()
        for transition in [Transition.TRANSITION_CONFIGURE, Transition.TRANSITION_ACTIVATE]:
            request = ChangeState.Request()
            request.transition.id = transition
            future = change.call_async(request)
            rclpy.spin_until_future_complete(node, future, timeout_sec=10)
            assert future.done() and future.result().success, (tmp_path / 'reload.log').read_text()
        deadline = time.monotonic() + 5
        while not maps and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        assert maps
        loaded = maps[-1]
        assert loaded.header.frame_id == 'map'
        assert loaded.info.width == grid.info.width and loaded.info.height == grid.info.height
        assert loaded.info.resolution == grid.info.resolution
        # Nav2 1.3.13 intentionally serializes origin X/Y to three decimals.
        assert abs(loaded.info.origin.position.x - grid.info.origin.position.x) <= 0.000500001
        assert abs(loaded.info.origin.position.y - grid.info.origin.position.y) <= 0.000500001
        assert loaded.info.origin.orientation == grid.info.origin.orientation
        assert sum(v >= 65 for v in loaded.data) == len(occupied)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for log in logs:
            log.close()
        node.destroy_node()
        rclpy.shutdown()


def test_missing_selected_config_fails_without_fallback(tmp_path):
    missing = tmp_path / 'missing-slam.yaml'
    result = subprocess.run(['ros2', 'launch', 'mobile_base_mapping', 'mapping.launch.py',
                             'mapping_config:=' + str(missing)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'Mapping configuration file missing: ' + str(missing) in result.stdout + result.stderr


def test_native_save_without_map_reports_failure(tmp_path):
    result = subprocess.run(['ros2', 'run', 'nav2_map_server', 'map_saver_cli',
                             '-f', str(tmp_path / 'map'), '--fmt', 'pgm',
                             '--ros-args', '-p', 'save_map_timeout:=1.0'],
                            capture_output=True, text=True, timeout=10)
    (tmp_path / 'save-no-map.log').write_text(result.stdout + result.stderr)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not (tmp_path / 'map.pgm').exists()
