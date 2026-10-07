"""Public Operator launch workflow; no sensor connection is attempted."""
import subprocess
import os
import pytest


def test_missing_network_facts_prevent_device_start():
    result = subprocess.run(
        ['ros2', 'launch', 'mobile_base_perception', 'dual_picoscan.launch.py'],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0
    assert 'fl_hostname' in result.stdout + result.stderr


def test_operator_can_inspect_required_device_arguments():
    result = subprocess.run(
        ['ros2', 'launch', 'mobile_base_perception', 'dual_picoscan.launch.py', '--show-args'],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for name in ('fl_hostname', 'br_hostname', 'udp_receiver_ip', 'fl_udp_port', 'br_udp_port'):
        assert name in result.stdout


@pytest.mark.parametrize("use_config", [False, True])
def test_native_sources_are_independently_visible_without_sensor_traffic(tmp_path, use_config):
    import signal
    import time
    import rclpy
    from rclpy.qos import ReliabilityPolicy

    command = ['ros2', 'launch', 'mobile_base_perception', 'dual_picoscan.launch.py',
               'fl_hostname:=127.0.0.2', 'br_hostname:=127.0.0.3',
               'udp_receiver_ip:=127.0.0.1', 'fl_udp_port:=32115', 'br_udp_port:=32116',
               'fl_check_udp_port:=32117', 'br_check_udp_port:=32118',
               'ros_qos:=4', 'listen_only_mode:=True', 'set_echo_filter:=True']
    if use_config:
        import yaml
        config = tmp_path / 'lidar.yaml'
        config.write_text(yaml.safe_dump({
            'fl_hostname': '127.0.0.2', 'br_hostname': '127.0.0.3',
            'udp_receiver_ip': '127.0.0.1', 'fl_udp_port': 32115, 'br_udp_port': 32116,
            'fl_check_udp_port': 32117, 'br_check_udp_port': 32118,
            'ros_qos': 0, 'listen_only_mode': False, 'set_echo_filter': False}))
        command = ['ros2', 'launch', 'mobile_base_perception', 'dual_picoscan.launch.py',
                   f'lidar_config:={config}', 'ros_qos:=4', 'listen_only_mode:=True',
                   'set_echo_filter:=True']
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


def test_imu_config_launch_publishes_converted_serial_samples(tmp_path):
    import math
    import pty
    import signal
    import time
    import yaml
    import rclpy
    from sensor_msgs.msg import Imu
    from test_packet import packet

    master, slave = pty.openpty()
    config = tmp_path / 'imu.yaml'
    config.write_text(yaml.safe_dump({'usb_imu': {'ros__parameters': {
        'port': os.ttyname(slave), 'baud': 115200, 'protocol_profile': 'handboard_v1',
        'acceleration_scale': 9.81, 'gyro_scale': math.pi / 180,
        'axes': [1, 2, 3], 'sample_timeout': 0.3}}}))
    process = subprocess.Popen(
        ['ros2', 'launch', 'mobile_base_perception', 'imu.launch.py', f'imu_config:={config}'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    rclpy.init()
    observer = rclpy.create_node('imu_launch_observer')
    samples = []
    observer.create_subscription(Imu, '/imu/data_raw', samples.append, 10)
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and not samples and process.poll() is None:
            os.write(master, packet([0, 0, 1, 0, 0, 0, 0, 90] + [0]*6))
            rclpy.spin_once(observer, timeout_sec=.05)
        assert samples, 'installed IMU launch must publish from explicit serial configuration'
        assert samples[-1].header.frame_id == 'base_imu_link'
        assert samples[-1].linear_acceleration.z == 9.81
        assert abs(samples[-1].angular_velocity.z - math.pi/2) < 1e-6
        assert list(samples[-1].angular_velocity_covariance) == [0.0]*9
    finally:
        observer.destroy_node(); rclpy.shutdown()
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); process.communicate()
        os.close(master); os.close(slave)


@pytest.mark.parametrize('entry,argument', [
    ('imu.launch.py', 'imu_config'), ('dual_picoscan.launch.py', 'lidar_config')])
def test_selected_missing_sensor_config_fails_launch(tmp_path, entry, argument):
    missing = tmp_path / 'missing.yaml'
    result = subprocess.run(
        ['ros2', 'launch', 'mobile_base_perception', entry, f'{argument}:={missing}'],
        capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert str(missing) in result.stdout + result.stderr
    assert 'configuration file missing' in result.stdout + result.stderr
