"""Operator launch and actual native lifecycle/map interfaces; no ROS mocks."""
import os
import signal
import subprocess
import pytest


def launch_dataset(directory, log):
    return subprocess.Popen(['ros2', 'launch', 'mobile_base_bringup', 'dataset.launch.py',
                             f'dataset:={directory}'], stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


@pytest.mark.parametrize('missing', ['map.pgm', 'map.yaml', 'route_graph.geojson'])
def test_missing_required_file_fails_launch_with_selected_path(tmp_path, missing):
    dataset(tmp_path)
    (tmp_path / missing).unlink()
    log_path = tmp_path / 'launch.log'
    with log_path.open('w') as log:
        process = launch_dataset(tmp_path, log)
        try:
            assert process.wait(timeout=8) != 0
        finally:
            stop(process)
    assert str(tmp_path / missing) in log_path.read_text()


def dataset(directory):
    (directory / 'map.pgm').write_bytes(b'P5\n10 10\n255\n' + bytes([254])*100)
    (directory / 'map.yaml').write_text('image: map.pgm\nresolution: 1.0\norigin: [0.0, 0.0, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
    (directory / 'route_graph.geojson').write_text('''{
      "type":"FeatureCollection", "features":[
        {"type":"Feature","properties":{"id":0,"frame":"map"},"geometry":{"type":"Point","coordinates":[1,1]}},
        {"type":"Feature","properties":{"id":1,"frame":"map"},"geometry":{"type":"Point","coordinates":[2,1]}},
        {"type":"Feature","properties":{"id":2,"startid":0,"endid":1,"cost":1.0,"overridable":false},"geometry":{"type":"LineString","coordinates":[[1,1],[2,1]]}}
      ]}''')


class NativeWorkflow:
    def __init__(self):
        import rclpy
        self.rclpy = rclpy
        rclpy.init()
        self.node = rclpy.create_node('dataset_test_operator')

    def call(self, name, service_type, request):
        client = self.node.create_client(service_type, name)
        assert client.wait_for_service(timeout_sec=12), f'native service unavailable: {name}'
        future = client.call_async(request)
        self.rclpy.spin_until_future_complete(self.node, future, timeout_sec=12)
        assert future.done(), f'native service did not complete: {name}'
        response = future.result()
        self.node.destroy_client(client)
        return response

    def change(self, name, transition):
        from lifecycle_msgs.srv import ChangeState
        request = ChangeState.Request()
        request.transition.id = transition
        return self.call(f'/{name}/change_state', ChangeState, request).success

    def state(self, name):
        from lifecycle_msgs.srv import GetState
        return self.call(f'/{name}/get_state', GetState, GetState.Request()).current_state.id

    def close(self):
        self.node.destroy_node()
        self.rclpy.shutdown()


def test_dataset_loads_real_native_map_and_graph_and_leaves_route_inactive(tmp_path):
    import time
    from nav_msgs.msg import OccupancyGrid
    from rclpy.qos import QoSProfile, DurabilityPolicy
    dataset(tmp_path)
    workflow = NativeWorkflow()
    maps = []
    workflow.node.create_subscription(OccupancyGrid, '/map', maps.append,
                                     QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    with (tmp_path / 'launch.log').open('w') as log:
        process = launch_dataset(tmp_path, log)
        try:
            assert workflow.change('map_server', 1)
            assert workflow.change('route_server', 1)
            assert workflow.state('route_server') == 2
            assert workflow.change('map_server', 3)
            deadline = time.monotonic() + 5
            while not maps and time.monotonic() < deadline:
                workflow.rclpy.spin_once(workflow.node, timeout_sec=0.1)
            assert maps and maps[0].info.width == 10 and maps[0].info.height == 10
            assert list(maps[0].data) == [0]*100
            assert workflow.state('map_server') == 3
        finally:
            stop(process)
            workflow.close()
    assert str(tmp_path / 'route_graph.geojson') in (tmp_path / 'launch.log').read_text()


@pytest.mark.parametrize('invalid,target', [('map.yaml', 'map_server'),
                                           ('map.pgm', 'map_server'),
                                           ('route_graph.geojson', 'route_server'),
                                           ('empty_graph', 'route_server'),
                                           ('missing_graph_tf', 'route_server')])
def test_native_parse_failure_cannot_configure_selected_dataset(tmp_path, invalid, target):
    dataset(tmp_path)
    if invalid == 'empty_graph':
        invalid = 'route_graph.geojson'
        (tmp_path / invalid).write_text('{\"type\":\"FeatureCollection\",\"features\":[]}')
    elif invalid == 'missing_graph_tf':
        invalid = 'route_graph.geojson'
        graph_path = tmp_path / invalid
        graph_path.write_text(graph_path.read_text().replace('\"frame\":\"map\"', '\"frame\":\"missing_fixture_frame\"'))
    else:
        (tmp_path / invalid).write_text('invalid native input')
    workflow = NativeWorkflow()
    with (tmp_path / 'launch.log').open('w') as log:
        process = launch_dataset(tmp_path, log)
        try:
            assert not workflow.change(target, 1)
            assert workflow.state(target) not in (2, 3)
        finally:
            stop(process)
            workflow.close()
    # Native process owns the reason; launch preserves its screen output.
    output = (tmp_path / 'launch.log').read_text()
    assert str(tmp_path / invalid) in output
    assert 'ERROR' in output or 'FATAL' in output or 'Failed to transform' in output
