"""Installed Bringup seam with OS serial peers and real native TF/EKF nodes."""
import math
import os
import pty
import signal
import socket
import struct
import subprocess
import threading
import time

import pytest
import rclpy
import yaml
from diagnostic_msgs.msg import DiagnosticArray
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu, JointState
from tf2_ros import Buffer, TransformListener
from test_control_workflow import Peer


def write_profiles(tmp_path, peer, imu_port):
    hardware = dict(serial_port=peer.path, baud=115200, parity='N', stop_bits=1,
                    response_timeout_seconds=.03, enable_timeout_seconds=.3,
                    firmware='SOFTWARE_PEER_NOT_HARDWARE', verified_speed_mode=True,
                    verified_multidrive2=True, pdo_mapping=0, drive_enable_setting=1,
                    position_format=0)
    for side, drive, direction in [('left', 2, -1), ('right', 1, 1)]:
        for key, value in dict(drive_id=drive, direction=direction, gear_ratio=10,
                               feedback_rpm_per_count=1, max_motor_rpm=3000,
                               position_steps_per_motor_revolution=10000,
                               encoder_pulses_per_motor_revolution=2500).items():
            hardware[side+'_'+key] = value
    controller = dict(update_rate=30, wheel_radius=.1, wheel_separation=.5,
                      cmd_vel_timeout=.3, linear_velocity_limit=.5, angular_velocity_limit=1.,
                      pose_covariance_diagonal=[.01]*6, twist_covariance_diagonal=[.01]*6)
    profiles = {
        'hardware': dict(hardware=hardware, controller=controller),
        'imu': {'usb_imu': {'ros__parameters': dict(port=imu_port, baud=115200,
                 protocol_profile='handboard_v1', acceleration_scale=9.81, gyro_scale=1.,
                 axes=[1,2,3], sample_timeout=.3, angular_velocity_variances=[.01]*3)}},
        'filter': {'ekf_filter_node': {'ros__parameters': dict(frequency=30.,
                   sensor_timeout=.3, two_d_mode=True, publish_tf=True,
                   odom_frame='odom', base_link_frame='base_footprint', world_frame='odom',
                   odom0='/base_controller/odom', odom0_config=[False]*6+[True,True]+[False]*7,
                   imu0='/imu/data_raw', imu0_config=[False]*11+[True]+[False]*3)}}}
    for name, profile in profiles.items():
        (tmp_path/(name+'.yaml')).write_text(yaml.safe_dump(profile))


@pytest.mark.parametrize('entry', ['local_base.launch.py','base.launch.py'])
def test_operator_gets_real_adapter_data_and_one_model_estimation_chain(tmp_path, entry):
    peer = Peer()
    master, slave = pty.openpty()
    running = threading.Event()
    running.set()
    data = b'\xaa\x55' + struct.pack('<14f', *([0, 0, 1, 0, 0, 0, 0, 0] + [0]*6))
    checksum = 0
    for byte in data:
        checksum ^= byte
    packet = data + bytes([checksum])
    def send_imu():
        while running.is_set():
            os.write(master, packet)
            time.sleep(.02)
    sender = threading.Thread(target=send_imu, daemon=True)
    sender.start()
    write_profiles(tmp_path, peer, os.ttyname(slave))
    os.environ['ROS_DOMAIN_ID'] = str(100 + os.getpid() % 100)
    rclpy.init()
    node = rclpy.create_node('local_base_observer')
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    samples, joints, imus, diagnostics = [], [], [], []
    node.create_subscription(Odometry, '/odometry/filtered', samples.append, 10)
    node.create_subscription(JointState, '/joint_states', joints.append, 10)
    node.create_subscription(Imu, '/imu/data_raw', imus.append, 10)
    node.create_subscription(DiagnosticArray, '/diagnostics', diagnostics.append, 10)
    log_path = tmp_path/'local-base.log'
    log = log_path.open('w')
    command = ['ros2','launch','mobile_base_bringup',entry,
        f'hardware_config:={tmp_path}/hardware.yaml', f'imu_config:={tmp_path}/imu.yaml',
        f'filter_config:={tmp_path}/filter.yaml']
    if entry == 'base.launch.py':
        command += ['fl_hostname:=127.0.0.2','br_hostname:=127.0.0.3',
                    'udp_receiver_ip:=127.0.0.1','fl_udp_port:=33115','br_udp_port:=33117',
                    'fl_check_udp_port:=33116','br_check_udp_port:=33118','ros_qos:=4',
                    'listen_only_mode:=True','foxglove:=True','foxglove_port:=39076']
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True)
    try:
        deadline = time.monotonic()+20
        while time.monotonic()<deadline:
            assert process.poll() is None, log_path.read_text()
            rclpy.spin_once(node, timeout_sec=.02)
            if samples and joints and imus and all(buffer.can_transform('odom', frame, rclpy.time.Time())
                    for frame in ('base_imu_link','driving_wheel_link_L','driving_wheel_link_R')):
                break
        assert samples and joints and imus, log_path.read_text()
        for frame in ('base_imu_link','driving_wheel_link_L','driving_wheel_link_R'):
            buffer.lookup_transform('odom',frame,rclpy.time.Time())
        assert all(math.isfinite(x) for x in joints[-1].position)
        assert samples[-1].child_frame_id == 'base_footprint'
        assert imus[-1].header.frame_id == 'base_imu_link'
        assert [i.node_name for i in node.get_publishers_info_by_topic('/tf_static')] == ['robot_state_publisher']
        assert [i.node_name for i in node.get_publishers_info_by_topic('/robot_description')] == ['robot_state_publisher']
        assert [i.node_name for i in node.get_publishers_info_by_topic('/odometry/filtered')] == ['ekf_filter_node']
        # Advertising /tf is not publication of the odom edge; native controller
        # discovery may lag the first filtered sample. Verify its public setting.
        from rclpy.parameter_client import AsyncParameterClient
        client = AsyncParameterClient(node, '/base_controller')
        assert client.wait_for_services(timeout_sec=5)
        future = client.get_parameters(['enable_odom_tf','twist_covariance_diagonal'])
        rclpy.spin_until_future_complete(node, future, timeout_sec=5)
        assert future.done() and future.result() is not None
        assert future.result().values[0].bool_value is False
        assert list(future.result().values[1].double_array_value) == [.01]*6
        assert {i.node_name for i in node.get_publishers_info_by_topic('/tf')} <= {'robot_state_publisher','base_controller','ekf_filter_node'}
        assert {'m1: left_wheel_joint','m1: right_wheel_joint','usb_imu: USB IMU'} <= {
            status.name for array in diagnostics for status in array.status}
        assert not node.get_publishers_info_by_topic('/base_controller/cmd_vel')
        if entry == 'base.launch.py':
            # Native bridge's public WebSocket handshake, not a node-name proxy.
            deadline = time.monotonic()+10
            response = b''
            while time.monotonic()<deadline:
                try:
                    with socket.create_connection(('127.0.0.1',39076),timeout=.5) as connection:
                        connection.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: foxglove.sdk.v1, foxglove.websocket.v1\r\n\r\n')
                        response = connection.recv(4096)
                    break
                except OSError:
                    rclpy.spin_once(node,timeout_sec=.05)
            assert b'101 Switching Protocols' in response, (response, log_path.read_text())
            from rclpy.qos import ReliabilityPolicy
            for side, frame in [('fl','FL'),('br','BR')]:
                deadline = time.monotonic()+10
                while time.monotonic()<deadline:
                    rclpy.spin_once(node,timeout_sec=.02)
                    publishers = node.get_publishers_info_by_topic('/lidar/'+side+'/scan')
                    if publishers and all(p.node_name == 'picoscan_'+side for p in publishers):
                        break
                assert len(publishers) == 1
                assert publishers[0].node_name == 'picoscan_'+side
                assert publishers[0].qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
                buffer.lookup_transform('odom','base_lidar_link_'+frame+'_1',rclpy.time.Time())
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            process.wait()
        log.close()
        node.destroy_node()
        rclpy.shutdown()
        running.clear()
        sender.join(timeout=2)
        os.close(master)
        os.close(slave)
        peer.close()


def test_missing_filter_file_fails_before_touching_control_device(tmp_path):
    peer = Peer(require_enable=True)
    master, slave = pty.openpty()
    try:
        write_profiles(tmp_path, peer, os.ttyname(slave))
        missing = tmp_path/'filter.yaml'
        missing.unlink()
        result = subprocess.run(['ros2','launch','mobile_base_bringup','local_base.launch.py',
            f'hardware_config:={tmp_path}/hardware.yaml', f'imu_config:={tmp_path}/imu.yaml',
            f'filter_config:={missing}'], capture_output=True, text=True, timeout=15)
        assert result.returncode != 0
        assert str(missing) in result.stdout + result.stderr
        assert not peer.requests
        assert not peer.lifecycle_commands
    finally:
        os.close(master)
        os.close(slave)
        peer.close()
