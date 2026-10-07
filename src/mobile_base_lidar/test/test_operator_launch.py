"""Public Operator launch workflow; no sensor connection is attempted."""
import subprocess
import os


def test_missing_network_facts_prevent_device_start():
    result = subprocess.run(
        ['ros2', 'launch', 'mobile_base_lidar', 'dual_picoscan.launch.py'],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0
    assert 'fl_hostname' in result.stdout + result.stderr


def test_operator_can_inspect_required_device_arguments():
    result = subprocess.run(
        ['ros2', 'launch', 'mobile_base_lidar', 'dual_picoscan.launch.py', '--show-args'],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for name in ('fl_hostname', 'br_hostname', 'udp_receiver_ip', 'fl_udp_port', 'br_udp_port'):
        assert name in result.stdout


def test_native_sources_are_independently_visible_without_sensor_traffic():
    import signal
    import time
    import rclpy
    from rclpy.qos import ReliabilityPolicy

    command = ['ros2', 'launch', 'mobile_base_lidar', 'dual_picoscan.launch.py',
               'fl_hostname:=127.0.0.2', 'br_hostname:=127.0.0.3',
               'udp_receiver_ip:=127.0.0.1', 'fl_udp_port:=32115', 'br_udp_port:=32116',
               'fl_check_udp_port:=32117', 'br_check_udp_port:=32118',
               'ros_qos:=4', 'listen_only_mode:=True', 'set_echo_filter:=True']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, start_new_session=True)
    rclpy.init()
    observer = rclpy.create_node('lidar_workflow_test')
    try:
        deadline = time.monotonic() + 15
        visible = {}
        while time.monotonic() < deadline:
            rclpy.spin_once(observer, timeout_sec=0.2)
            visible = {topic: observer.get_publishers_info_by_topic(topic)
                       for topic in ('/lidar/fl/scan', '/lidar/br/scan')}
            if all(items and items[0].node_name.startswith('picoscan_') for items in visible.values()):
                break
        for topic, name, namespace in (
            ('/lidar/fl/scan', 'picoscan_fl', '/lidar/fl'),
            ('/lidar/br/scan', 'picoscan_br', '/lidar/br'),
        ):
            assert len(visible[topic]) == 1, (topic, visible)
            publisher = visible[topic][0]
            assert (publisher.node_name, publisher.node_namespace) == (name, namespace)
            assert publisher.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
            # Check the native driver's public parameter service, not launch text.
            from rclpy.parameter_client import AsyncParameterClient
            client = AsyncParameterClient(observer, namespace + '/' + name)
            assert client.wait_for_services(timeout_sec=3)
            future = client.get_parameters(['listen_only_mode', 'host_set_FREchoFilter', 'imu_enable'])
            rclpy.spin_until_future_complete(observer, future, timeout_sec=3)
            assert future.done()
            values = future.result().values
            # sick_scan_xd's native XML/CLI interface exposes string overrides;
            # its bool conversion requires numeric strings, not True/False.
            assert [v.string_value for v in values] == ['1', '1', '0']
    finally:
        observer.destroy_node()
        rclpy.shutdown()
        os.killpg(process.pid, signal.SIGINT)
        try:
            output, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()

    assert '[picoscan_fl-' in output and '[picoscan_br-' in output
