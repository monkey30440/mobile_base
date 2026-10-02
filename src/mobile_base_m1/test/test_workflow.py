"""Public ROS workflow with a pseudo-terminal M1 peer; no physical device access."""
import os
import pty
import select
import signal
import struct
import subprocess
import threading
import time
from pathlib import Path

import pytest
import rclpy
import yaml
from diagnostic_msgs.msg import DiagnosticArray
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry


def crc(data):
    value = 0xffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xa001 if value & 1 else 0)
    return struct.pack('<H', value)


class Peer:
    """External Modbus RTU peer: fixed authoritative example RPM feedback."""
    def __init__(self):
        self.master, self.slave = pty.openpty()
        self.path = os.ttyname(self.slave)
        self.commands = []
        self.fault = False
        self.silent = False
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        buffer = bytearray()
        while self.running:
            if not select.select([self.master], [], [], 0.05)[0]:
                continue
            buffer.extend(os.read(self.master, 512))
            while len(buffer) >= 8:
                length = 8 if buffer[1] == 3 else 9 + buffer[6]
                if len(buffer) < length:
                    break
                request = bytes(buffer[:length])
                del buffer[:length]
                if crc(request[:-2]) != request[-2:]:
                    continue
                if request[1] == 3:
                    # status/alarm/rpm for IDs1 then2; right polarity reversed.
                    registers = (5 if self.fault else 2, 13 if self.fault else 0,
                                 120, 2, 0, 65416)
                    response = bytes((0x65, 3, 12)) + struct.pack('>6H', *registers)
                elif request[1] == 16:
                    data = struct.unpack('>4H', request[7:15])
                    self.commands.append((data[1] if data[1] < 32768 else data[1]-65536,
                                          data[3] if data[3] < 32768 else data[3]-65536))
                    response = request[:6]
                else:
                    continue
                if not self.silent:
                    os.write(self.master, response + crc(response))

    def close(self):
        self.running = False
        self.thread.join(timeout=1)
        os.close(self.master)
        os.close(self.slave)


@pytest.fixture
def workflow(tmp_path):
    os.environ['ROS_DOMAIN_ID'] = str(100 + os.getpid() % 100)
    peer = Peer()
    config = {'hardware': {'serial_port': peer.path, 'baud': 115200, 'parity': 'N',
                          'stop_bits': 1, 'response_timeout_seconds': 0.03,
                          'firmware': 'SOFTWARE_PEER_NOT_HARDWARE',
                          'verified_speed_mode': True, 'verified_multidrive2': True,
                          'pdo_mapping': 0},
              'controller': {'wheel_radius': 0.1, 'wheel_separation': 0.5,
                             'cmd_vel_timeout': 0.3, 'update_rate': 30,
                             'linear_velocity_limit': 0.5, 'angular_velocity_limit': 1.0}}
    for side, drive_id, direction in [('left_', 1, 1), ('right_', 2, -1)]:
        config['hardware'].update({side+'drive_id': drive_id, side+'gear_ratio': 10,
                                   side+'direction': direction,
                                   side+'feedback_rpm_per_count': 1,
                                   side+'max_motor_rpm': 3000})
    target = tmp_path / 'target.yaml'
    target.write_text(yaml.safe_dump(config))
    model = tmp_path / 'robot.urdf'
    model.write_text('''<robot name="software_fixture"><link name="base_footprint"/>
      <link name="left_wheel"/><link name="right_wheel"/>
      <joint name="left_wheel_joint" type="continuous"><parent link="base_footprint"/><child link="left_wheel"/><axis xyz="0 1 0"/></joint>
      <joint name="right_wheel_joint" type="continuous"><parent link="base_footprint"/><child link="right_wheel"/><axis xyz="0 1 0"/></joint></robot>''')
    output = open(tmp_path / 'launch.log', 'w+')
    process = subprocess.Popen(['ros2', 'launch', 'mobile_base_m1', 'm1.launch.py',
                                f'hardware_config:={target}', f'model_file:={model}'],
                               stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    rclpy.init()
    node = rclpy.create_node('m1_workflow_observer')
    odom, diagnostics = [], []
    node.create_subscription(Odometry, '/base_controller/odom', odom.append, 10)
    node.create_subscription(DiagnosticArray, '/diagnostics', diagnostics.append, 10)
    publisher = node.create_publisher(TwistStamped, '/base_controller/cmd_vel', 10)

    def wait(condition, seconds=15):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.03)
            if condition():
                return
        output.flush()
        raise AssertionError((tmp_path / 'launch.log').read_text() + '\nDIAGNOSTICS ' + str([(s.name, s.level, s.message) for msg in diagnostics[-3:] for s in msg.status]))

    try:
        wait(lambda: bool(odom) and publisher.get_subscription_count() > 0)
        yield peer, node, publisher, odom, diagnostics, wait
    finally:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        node.destroy_node()
        rclpy.shutdown()
        peer.close()
        output.close()


def test_native_controller_feedback_command_and_timeout(workflow):
    peer, node, publisher, odom, diagnostics, wait = workflow
    wait(lambda: odom[-1].twist.twist.linear.x == pytest.approx(0.125663706, abs=1e-6))
    assert odom[-1].twist.twist.linear.x == pytest.approx(0.125663706, abs=1e-6)
    assert odom[-1].twist.twist.angular.z == pytest.approx(0, abs=1e-6)
    command = TwistStamped()
    command.header.stamp = node.get_clock().now().to_msg()
    command.twist.linear.x = 0.1
    publisher.publish(command)
    wait(lambda: (95, -95) in peer.commands)
    wait(lambda: peer.commands[-1] == (0, 0), seconds=3)
    wait(lambda: any(s.level in (0, b'\x00') and 'left_wheel_joint' in s.name
                     for msg in diagnostics for s in msg.status), seconds=4)


def test_drive_alarm_invalidates_feedback_and_identifies_source(workflow):
    peer, _, _, _, diagnostics, wait = workflow
    diagnostics.clear()
    peer.commands.clear()
    peer.fault = True
    wait(lambda: any(s.level in (2, b'\x02') and 'left_wheel_joint' in s.name
                     and 'alarm=13' in s.message
                     and any(v.key == 'drive_id' and v.value == '1' for v in s.values)
                     for msg in diagnostics for s in msg.status), seconds=5)
    assert (0, 0) in peer.commands


def test_serial_response_timeout_is_not_healthy_stale_feedback(workflow):
    peer, _, _, _, diagnostics, wait = workflow
    diagnostics.clear()
    peer.commands.clear()
    peer.silent = True
    wait(lambda: any(s.level in (2, b'\x02') and 'left_wheel_joint' in s.name
                     and 'feedback read failed/timeout' in s.message
                     and any(v.key == 'feedback_valid' and v.value == 'False' for v in s.values)
                     for msg in diagnostics for s in msg.status), seconds=5)
    assert (0, 0) in peer.commands  # request observed; no stop acknowledgement inferred


def test_unresolved_target_profile_fails_before_hardware_start():
    template = Path(__file__).parents[1] / 'config' / 'target.template.yaml'
    result = subprocess.run(['ros2', 'launch', 'mobile_base_m1', 'm1.launch.py',
                             f'hardware_config:={template}', 'model_file:=/unused.urdf'],
                            capture_output=True, text=True, timeout=8)
    assert result.returncode != 0
    assert 'M1 target fact required:' in result.stdout + result.stderr
