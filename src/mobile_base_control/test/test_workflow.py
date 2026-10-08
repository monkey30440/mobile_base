"""Public ROS workflow with a pseudo-terminal M1 peer; no physical device access."""
import os
import math
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
from ament_index_python.packages import get_package_share_directory
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_msgs.msg import TFMessage


def crc(data):
    value = 0xffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xa001 if value & 1 else 0)
    return struct.pack('<H', value)


class Peer:
    """External Modbus RTU peer: fixed authoritative example RPM feedback."""
    def __init__(self, require_enable=False, stale_target=0, ignore_istop=False, fail_enable=False, alarm_on_enable=False, enable_delay=0, ignore_svoff=False, response_delay=0, positions=None, position_format=0, encoder_pulses=2500):
        self.response_delay = response_delay
        self.require_enable = require_enable
        self.enabled = not require_enable
        self.targets = [stale_target, stale_target]
        self.ignore_istop = ignore_istop
        self.ignore_svoff = ignore_svoff
        self.fail_enable = fail_enable
        self.enable_delay = enable_delay
        self.enable_at = None
        self.alarm_on_enable = alarm_on_enable
        self.lifecycle_commands = []
        self.energized_with_stale_target = False
        self.alarm_reset_observed = False
        self.master, self.slave = pty.openpty()
        self.path = os.ttyname(self.slave)
        self.requests = []
        self.commands = []
        self.request_gaps = []
        self.last_response = None
        self.positions = positions or [(1, 0), (65535, 0)]
        self.position_format = position_format
        self.encoder_pulses = encoder_pulses
        self.fault = False
        self.inhibited = False
        self.silent = False
        self.bad_error_check = False
        self.one_shot_sto_fault = False
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
                self.requests.append(request)
                del buffer[:length]
                if self.last_response is not None:
                    self.request_gaps.append(time.monotonic() - self.last_response)
                if crc(request[:-2]) != request[-2:]:
                    continue
                if self.enable_at is not None and time.monotonic() >= self.enable_at:
                    self.enabled = True
                    self.enable_at = None
                if request[1] == 3:
                    address = struct.unpack('>H', request[2:4])[0]
                    if request[0] != 0x65:
                        value = {0x020d: self.position_format, 0x0105: self.encoder_pulses}[address]
                        response = bytes((request[0], 3, 2)) + struct.pack('>H', value)
                        if not self.silent:
                            os.write(self.master, response + crc(response))
                        continue
                    # status/alarm/rpm for IDs1 then2; right polarity reversed.
                    count = struct.unpack('>H', request[4:6])[0]
                    # Manual p38: each drive contributes n data words plus Error_Check.
                    # Independently written literal: status2/alarm0/RPM120/prefix-CRC94B5,
                    # then status2/alarm0/RPM-120/prefix-CRC80CA. Check words are distinct from speed.
                    response = bytes.fromhex('65 03 10 00 02 00 00 00 78 94 b5 00 02 00 00 ff 88 80 ca')
                    if self.fault:
                        response = bytes.fromhex('65 03 10 00 05 00 0d 00 78 97 91 00 02 00 00 ff 88 7c de')
                    if self.inhibited or (self.require_enable and not self.enabled):
                        response = bytes.fromhex('65 03 10 00 06 00 00 00 00 76 44 00 06 00 00 00 00 0e 19')
                    if self.one_shot_sto_fault and request[2] == 0xf0:
                        response = bytes((0x65, 3, 16))
                        for words in ((5, 13, 0), (9, 0, 0)):
                            response += struct.pack('>HHH', *words)
                            response += struct.pack('>H', struct.unpack('<H', crc(response))[0])
                        self.one_shot_sto_fault = False
                    if (struct.unpack('>H', request[2:4])[0] >> 8) & 15 == 12:
                        response = bytes((0x65, 3, 8))
                        for target in self.targets:
                            response += struct.pack('>H', target & 0xffff)
                            response += struct.pack('>H', struct.unpack('<H', crc(response))[0])
                    if count == 16:
                        original = response
                        response = bytes((0x65, 3, 32))
                        for slot, pair in enumerate(self.positions):
                            words = struct.unpack('>3H', original[3 + slot * 8:9 + slot * 8])
                            response += struct.pack('>7H', *words, 0, 0, *pair)
                            response += struct.pack('>H', struct.unpack('<H', crc(response))[0])
                    if count == 6:
                        # n=2: status/alarm/check, without the speed measurement.
                        response = bytes.fromhex('65 03 0c 00 02 00 00 a5 a5 00 02 00 00 5a 5a')
                elif request[1] == 16:
                    data = struct.unpack('>4H', request[7:15])
                    command = data[0]
                    self.lifecycle_commands.append(command)
                    if command == 0 and not self.ignore_istop:
                        self.targets = [0, 0]
                    elif command == 1 and self.enabled:
                        self.targets = [data[1], data[3]]
                    elif command == 6 and not self.fail_enable:
                        self.energized_with_stale_target |= any(self.targets)
                        if self.enable_delay:
                            self.enable_at = time.monotonic() + self.enable_delay
                        else:
                            self.enabled = True
                        self.fault = self.alarm_on_enable
                    elif command == 7 and not self.ignore_svoff:
                        self.alarm_reset_observed |= self.fault
                        self.enabled = False
                    self.commands.append((data[1] if data[1] < 32768 else data[1]-65536,
                                          data[3] if data[3] < 32768 else data[3]-65536))
                    response = request[:6]
                else:
                    continue
                if self.bad_error_check and request[1] == 3:
                    response = response[:-1] + bytes((response[-1] ^ 1,))
                if not self.silent:
                    time.sleep(self.response_delay)
                    self.last_response = time.monotonic()
                    os.write(self.master, response + crc(response))

    def close(self):
        self.running = False
        self.thread.join(timeout=1)
        os.close(self.master)
        os.close(self.slave)


@pytest.fixture
def workflow(tmp_path, request):
    os.environ['ROS_DOMAIN_ID'] = str(100 + os.getpid() % 100)
    options = getattr(request, 'param', {})
    peer = Peer(**{k: v for k, v in options.items() if k not in ('expect_failure', 'native_budget', 'cmd_vel_timeout', 'covariance')})
    config = {'hardware': {'serial_port': peer.path, 'baud': 115200, 'parity': 'N',
                          'stop_bits': 1, 'response_timeout_seconds': 0.03, 'enable_timeout_seconds': 0.3,
                          'firmware': 'SOFTWARE_PEER_NOT_HARDWARE',
                          'verified_speed_mode': True, 'verified_multidrive2': True,
                          'pdo_mapping': 0, 'drive_enable_setting': 1, 'position_format': 0},
              'controller': {'wheel_radius': 0.1, 'wheel_separation': 0.5,
                             'cmd_vel_timeout': options.get('cmd_vel_timeout', 0.3), 'update_rate': 30,
                             'linear_velocity_limit': 0.5, 'angular_velocity_limit': 1.0,
                             'native_hardware_execution_budget_us': {'mean_warn':15000.0, 'mean_error':20000.0,
                                                                     'stddev_warn':3000.0, 'stddev_error':5000.0}}}
    if 'covariance' in options:
        config['controller']['pose_covariance_diagonal'] = options['covariance']
        config['controller']['twist_covariance_diagonal'] = options['covariance']
    if not options.get('native_budget', False):
        config['controller'].pop('native_hardware_execution_budget_us')
    for side, drive_id, direction in [('left_', 2, -1), ('right_', 1, 1)]:
        config['hardware'].update({side+'drive_id': drive_id, side+'gear_ratio': 10,
                                   side+'direction': direction,
                                   side+'feedback_rpm_per_count': 1,
                                   side+'max_motor_rpm': 3000,
                                   side+'position_steps_per_motor_revolution': 10000,
                                   side+'encoder_pulses_per_motor_revolution': 2500})
    target = tmp_path / 'target.yaml'
    target.write_text(yaml.safe_dump(config))
    model = tmp_path / 'robot.urdf'
    model.write_text('''<robot name="software_fixture"><link name="base_footprint"/>
      <link name="left_wheel"/><link name="right_wheel"/>
      <joint name="left_wheel_joint" type="continuous"><parent link="base_footprint"/><child link="left_wheel"/><axis xyz="0 1 0"/></joint>
      <joint name="right_wheel_joint" type="continuous"><parent link="base_footprint"/><child link="right_wheel"/><axis xyz="0 1 0"/></joint></robot>''')
    output = open(tmp_path / 'launch.log', 'w+')
    model_output = open(tmp_path / 'description.log', 'w+')
    model_process = subprocess.Popen(
        ['ros2', 'launch', 'mobile_base_description', 'description.launch.py',
         f'hardware_config:={target}', f'model_file:={model}'],
        stdout=model_output, stderr=subprocess.STDOUT, start_new_session=True)
    process = subprocess.Popen(['ros2', 'launch', 'mobile_base_control', 'm1.launch.py',
                                f'hardware_config:={target}'],
                               stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    peer.process = process
    peer.launch_log = tmp_path / "launch.log"
    rclpy.init()
    node = rclpy.create_node('m1_workflow_observer')
    odom, diagnostics, joint_feedback = [], [], []
    node.create_subscription(Odometry, '/base_controller/odom', odom.append, 10)
    node.create_subscription(DiagnosticArray, '/diagnostics', diagnostics.append, 10)
    node.create_subscription(JointState, '/joint_states', joint_feedback.append, 10)
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
        if not options.get('expect_failure'):
            if options.get('cmd_vel_timeout', 0.3) > 1:
                wait(lambda: publisher.get_subscription_count() > 0)
                def initialize_zero():
                    zero = TwistStamped()
                    zero.header.stamp = node.get_clock().now().to_msg()
                    publisher.publish(zero)
                    return bool(odom)
                wait(initialize_zero)
            wait(lambda: bool(odom) and publisher.get_subscription_count() > 0 and joint_feedback
                 and len(joint_feedback[-1].position) == 2
                 and all(math.isfinite(value) for value in joint_feedback[-1].position))
        yield peer, node, publisher, odom, diagnostics, wait
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        node.destroy_node()
        rclpy.shutdown()
        if model_process.poll() is None:
            os.killpg(model_process.pid, signal.SIGINT)
        try:
            model_process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(model_process.pid, signal.SIGKILL); model_process.wait()
        model_output.close()
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
    wait(lambda: any(s.level in (2, b'\x02') and 'right_wheel_joint' in s.name
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
                     and 'failed/timeout' in s.message
                     and any(v.key == 'feedback_valid' and v.value == 'False' for v in s.values)
                     for msg in diagnostics for s in msg.status), seconds=5)
    assert (0, 0) in peer.commands  # request observed; no stop acknowledgement inferred


def test_unresolved_target_profile_fails_before_hardware_start(tmp_path):
    profile = yaml.safe_load((Path(get_package_share_directory('mobile_base_control')) / 'config/m1.yaml').read_text())
    profile['hardware']['firmware'] = None
    template = tmp_path / 'incomplete.yaml'
    template.write_text(yaml.safe_dump(profile))
    result = subprocess.run(['ros2', 'launch', 'mobile_base_control', 'm1.launch.py',
                             f'hardware_config:={template}'],
                            capture_output=True, text=True, timeout=8)
    assert result.returncode != 0
    assert 'M1 target fact required:' in result.stdout + result.stderr


def test_invalid_per_drive_check_is_rejected_despite_valid_final_frame_crc(workflow):
    peer, _, _, _, diagnostics, wait = workflow
    diagnostics.clear()
    peer.commands.clear()
    peer.bad_error_check = True
    wait(lambda: any(s.level in (2, b'\x02') and 'left_wheel_joint' in s.name
                     and 'Error_Check prefix CRC mismatch' in s.message
                     for msg in diagnostics for s in msg.status), seconds=5)
    assert (0, 0) in peer.commands


def test_modbus_transactions_respect_documented_rtu_silence(workflow):
    peer, _, _, _, _, wait = workflow
    wait(lambda: len(peer.request_gaps) >= 20)
    # Manual p2: at baud >19200, C3.5 must be at least1.75ms (09-21=0).
    assert min(peer.request_gaps) >= 0.00175


def test_inhibited_drive_feedback_is_valid_but_motion_is_unavailable(workflow):
    peer, node, publisher, odom, diagnostics, wait = workflow
    diagnostics.clear()
    peer.inhibited = True
    wait(lambda: any(s.level in (1, b'\x01') and 'left_wheel_joint' in s.name
                     and 'WAIT/INHIBIT' in s.message
                     and any(v.key == 'feedback_valid' and v.value == 'True' for v in s.values)
                     for msg in diagnostics for s in msg.status), seconds=5)
    wait(lambda: abs(odom[-1].twist.twist.linear.x) < 1e-6)
    diagnostics.clear()
    command = TwistStamped()
    command.header.stamp = node.get_clock().now().to_msg()
    command.twist.linear.x = 0.1
    publisher.publish(command)
    wait(lambda: any(s.level in (2, b'\x02') and 'inhibited' in s.message
                     for msg in diagnostics for s in msg.status), seconds=5)


@pytest.mark.parametrize('workflow', [{'require_enable': True, 'stale_target': 120}], indirect=True)
def test_activation_clears_stale_target_before_servo_enable(workflow):
    peer, _, _, _, _, wait = workflow
    wait(lambda: peer.enabled)
    assert not peer.energized_with_stale_target


@pytest.mark.parametrize('workflow', [{'require_enable': True, 'enable_delay': 0.1}], indirect=True)
def test_activation_waits_for_bounded_servo_readiness_transition(workflow):
    peer, _, _, _, _, _ = workflow
    assert peer.enabled
    assert peer.lifecycle_commands.count(6) == 1


@pytest.mark.parametrize('workflow', [{'require_enable': True, 'stale_target': 120,
                                      'ignore_istop': True, 'expect_failure': True}], indirect=True)
def test_ignored_stop_never_energizes_stale_motor_target(workflow):
    peer, _, _, _, _, wait = workflow
    wait(lambda: 'stale target remains nonzero' in peer.launch_log.read_text(), seconds=4)
    assert 6 not in peer.lifecycle_commands
    assert not peer.enabled


@pytest.mark.parametrize('workflow', [{'require_enable': True, 'fail_enable': True,
                                      'expect_failure': True}], indirect=True)
def test_unavailable_enable_transition_attempts_no_alarm_safe_off(workflow):
    peer, _, _, _, _, wait = workflow
    wait(lambda: 7 in peer.lifecycle_commands, seconds=4)
    assert not peer.enabled
    assert peer.lifecycle_commands.count(6) == 1


@pytest.mark.parametrize('workflow', [{'require_enable': True}], indirect=True)
def test_native_hardware_deactivation_stops_and_deenergizes_without_reset(workflow):
    peer, _, _, _, _, wait = workflow
    result = subprocess.run(['ros2', 'control', 'set_hardware_component_state', 'M1', 'inactive'],
                            capture_output=True, text=True, timeout=8)
    assert result.returncode == 0, result.stdout + result.stderr
    wait(lambda: not peer.enabled, seconds=4)
    assert 7 in peer.lifecycle_commands
    assert not peer.alarm_reset_observed


@pytest.mark.parametrize('workflow', [{'require_enable': True, 'alarm_on_enable': True,
                                      'expect_failure': True}], indirect=True)
def test_alarm_during_enable_is_preserved_without_servo_off_reset(workflow):
    peer, _, _, _, _, wait = workflow
    wait(lambda: 'alarm=13' in peer.launch_log.read_text(), seconds=4)
    assert 7 not in peer.lifecycle_commands
    assert not peer.alarm_reset_observed


@pytest.mark.parametrize('workflow', [{'require_enable': True, 'ignore_svoff': True}], indirect=True)
def test_failed_servo_off_deactivation_reports_native_transition_failure(workflow):
    peer, _, _, _, _, _ = workflow
    result = subprocess.run(['ros2', 'control', 'set_hardware_component_state', 'M1', 'inactive'],
                            capture_output=True, text=True, timeout=8)
    assert result.returncode != 0, result.stdout + result.stderr
    assert peer.enabled


@pytest.mark.parametrize('workflow', [{'require_enable': True}], indirect=True)
def test_native_launch_shutdown_stops_and_deenergizes(workflow):
    peer, _, _, _, _, wait = workflow
    os.killpg(peer.process.pid, signal.SIGINT)
    wait(lambda: not peer.enabled, seconds=5)
    assert 7 in peer.lifecycle_commands
    assert not peer.alarm_reset_observed


@pytest.mark.parametrize('workflow,expected_level', [
    ({'response_delay': .006, 'native_budget': False}, 2),
    ({'response_delay': .006, 'native_budget': True}, 0),
    ({'response_delay': .0205, 'native_budget': True}, 2),
], indirect=['workflow'])
def test_native_hardware_execution_budget_preserves_timing_errors(workflow, expected_level):
    _, _, _, _, diagnostics, wait = workflow
    wait(lambda: any(s.level in (expected_level, bytes([expected_level]))
                     and s.name == 'controller_manager: Hardware Components Activity'
                     and any(v.key == 'M1.read_cycle.execution_time' for v in s.values)
                     for msg in diagnostics for s in msg.status), seconds=5)


@pytest.mark.parametrize('rate', [.5, True, 0, -1])
def test_invalid_controller_update_rate_fails_before_serial_requests(tmp_path, rate):
    peer = Peer()
    profile = yaml.safe_load((Path(get_package_share_directory('mobile_base_control')) / 'config' / 'm1.yaml').read_text())
    profile['hardware']['serial_port'] = peer.path
    profile['controller']['update_rate'] = rate
    target = tmp_path / 'invalid-rate.yaml'
    target.write_text(yaml.safe_dump(profile))
    model = tmp_path / 'model.urdf'
    model.write_text('<robot name="software_rate_fixture"><link name="base_footprint"/><link name="left"/><link name="right"/>'
                     '<joint name="left_wheel_joint" type="continuous"><parent link="base_footprint"/><child link="left"/><axis xyz="0 1 0"/></joint>'
                     '<joint name="right_wheel_joint" type="continuous"><parent link="base_footprint"/><child link="right"/><axis xyz="0 1 0"/></joint></robot>')
    process = subprocess.Popen(['ros2', 'launch', 'mobile_base_control', 'm1.launch.py',
                                f'hardware_config:={target}'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        output, _ = process.communicate(timeout=5)
        assert process.returncode != 0
        assert 'positive integer update_rate required' in output
        assert not peer.requests
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            process.wait(timeout=8)
        peer.close()


def test_other_drive_alarm_is_latched_before_first_wheel_invalidity_and_shutdown(workflow):
    peer, _, _, _, _, wait = workflow
    peer.lifecycle_commands.clear()
    peer.one_shot_sto_fault = True
    wait(lambda: 'status=9' in peer.launch_log.read_text(), seconds=4)
    # Subsequent peer replies are healthy; the captured other-drive alarm must
    # still prevent SVOFF, whose documented effect can implicitly reset alarms.
    os.killpg(peer.process.pid, signal.SIGINT)
    peer.process.wait(timeout=8)
    assert 7 not in peer.lifecycle_commands


def test_real_position_feedback_reaches_native_joint_states(workflow):
    peer, node, _, _, _, wait = workflow
    joints = []
    node.create_subscription(JointState, '/joint_states', joints.append, 10)
    wait(lambda: joints and len(joints[-1].position) == 2 and
         all(abs(p - 0.628318530718) < 1e-9 for p in joints[-1].position))
    assert set(joints[-1].name) == {'left_wheel_joint', 'right_wheel_joint'}
    assert len(joints[-1].position) == 2


@pytest.mark.parametrize('workflow', [
    {'positions': [(1, 9800), (65534, 200)]},
    {'positions': [(32767, 9800), (32768, 200)]},
], indirect=True)
def test_native_joint_states_and_model_tf_follow_real_position_carry(workflow):
    peer, node, _, _, _, wait = workflow
    joints, transforms = [], []
    node.create_subscription(JointState, '/joint_states', joints.append, 10)
    node.create_subscription(TFMessage, '/tf', transforms.append, 20)
    wait(lambda: joints and len(joints[-1].position) == 2)
    before = dict(zip(joints[-1].name, joints[-1].position))
    index = peer.positions[0][0]
    peer.positions = [((index + 1) & 65535, 200), ((peer.positions[1][0] - 1) & 65535, 9800)]
    # Independent fixture: each motor advances signed0.04 turns, gearing10:1.
    wait(lambda: all(p == pytest.approx(before[n] + 0.0251327412287, abs=1e-8)
                     for n, p in zip(joints[-1].name, joints[-1].position)))
    import math
    wait(lambda: {'left_wheel', 'right_wheel'} <=
         {t.child_frame_id for m in transforms for t in m.transforms})
    def model_follows_measured_position():
        latest = {t.child_frame_id: t for m in transforms for t in m.transforms}
        for child, joint in [('left_wheel', 'left_wheel_joint'), ('right_wheel', 'right_wheel_joint')]:
            if child not in latest:
                return False
            q = latest[child].transform.rotation
            half_angle = (before[joint] + 0.0251327412287) / 2
            # q and -q describe the same rotation; compare orientation equivalence.
            if abs(q.y * math.sin(half_angle) + q.w * math.cos(half_angle)) < 1 - 1e-8:
                return False
        return True
    wait(model_follows_measured_position)
    for m in transforms:
        for t in m.transforms:
            q = t.transform.rotation
            assert all(math.isfinite(v) for v in (q.x, q.y, q.z, q.w))


@pytest.mark.parametrize('workflow', [
    {'position_format': 1, 'expect_failure': True},
    {'encoder_pulses': 1024, 'expect_failure': True},
], indirect=True)
def test_wrong_actual_position_configuration_never_requests_servo_on(workflow):
    peer, _, _, _, _, wait = workflow
    wait(lambda: 'position format/encoder verification failed' in peer.launch_log.read_text())
    assert 6 not in peer.lifecycle_commands


@pytest.mark.parametrize('bad_position, reason', [
    ((1, 10000), 'invalid residual position pulse'),
    ((1000, 0), 'position jump/reset exceeds'),
])
def test_bad_position_invalidates_feedback_and_requests_stop(workflow, bad_position, reason):
    peer, _, _, _, diagnostics, wait = workflow
    diagnostics.clear()
    peer.commands.clear()
    peer.positions = [bad_position, peer.positions[1]]
    wait(lambda: any(s.level in (2, b'\x02') and reason in s.message and
                     any(v.key == 'feedback_valid' and v.value == 'False' for v in s.values)
                     for m in diagnostics for s in m.status))
    assert 0 in peer.lifecycle_commands
    assert (0, 0) in peer.commands


def test_transient_position_fault_requires_reconfigure_before_new_reference(workflow):
    peer, node, _, _, diagnostics, wait = workflow
    peer.positions = [(1, 10000), peer.positions[1]]
    wait(lambda: any('invalid residual position pulse' in s.message and s.level in (2, b'\x02')
                     for m in diagnostics for s in m.status))
    enables = peer.lifecycle_commands.count(6)
    peer.positions = [(5, 0), (65531, 0)]
    diagnostics.clear()
    wait(lambda: any('invalid residual position pulse' in s.message and
                     any(v.key == 'feedback_valid' and v.value == 'False' for v in s.values)
                     for m in diagnostics for s in m.status))
    assert peer.lifecycle_commands.count(6) == enables
    for state in ('inactive', 'active'):
        result = subprocess.run(['ros2', 'control', 'set_hardware_component_state', 'M1', state],
                                capture_output=True, text=True, timeout=8)
        assert result.returncode == 0, result.stdout + result.stderr
    client = node.create_client(ListControllers, '/controller_manager/list_controllers')
    assert client.wait_for_service(timeout_sec=5)
    future = client.call_async(ListControllers.Request())
    rclpy.spin_until_future_complete(node, future, timeout_sec=5)
    assert future.done() and future.result() is not None
    states = {controller.name: controller.state for controller in future.result().controller}
    node.destroy_client(client)
    for controller in ('joint_state_broadcaster', 'base_controller'):
        if states[controller] == 'unconfigured':
            configured = subprocess.run(['ros2','control','set_controller_state',controller,'inactive'],
                capture_output=True,text=True,timeout=8)
            assert configured.returncode == 0, configured.stdout + configured.stderr
        else:
            assert states[controller] == 'inactive', states
        result = subprocess.run(['ros2', 'control', 'set_controller_state', controller, 'active'],
                                capture_output=True, text=True, timeout=8)
        assert result.returncode == 0, result.stdout + result.stderr
    joints = []
    node.create_subscription(JointState, '/joint_states', joints.append, 10)
    wait(lambda: joints and len(joints[-1].position) == 2 and
         all(p == pytest.approx(3.14159265359, abs=1e-9) for p in joints[-1].position))


def test_independent_description_and_control_have_one_model_owner(workflow):
    from std_msgs.msg import String
    from rclpy.qos import QoSProfile, DurabilityPolicy
    import xml.etree.ElementTree as ET
    peer, node, _, _, _, wait = workflow
    descriptions = []
    node.create_subscription(String, '/robot_description', lambda m: descriptions.append(m.data),
                             QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    wait(lambda: bool(descriptions))
    assert len(node.get_publishers_info_by_topic('/robot_description')) == 1
    assert len(node.get_publishers_info_by_topic('/tf_static')) == 1
    assert ET.fromstring(descriptions[-1]).find("ros2_control/hardware/plugin").text == 'mobile_base_control/M1System'
    os.killpg(peer.process.pid, signal.SIGINT)
    peer.process.wait(timeout=8)
    # Model ownership persists when only the independently launched Control exits.
    assert len(node.get_publishers_info_by_topic('/robot_description')) == 1


def test_description_with_hardware_profile_does_not_start_control(tmp_path):
    from std_msgs.msg import String
    from rclpy.qos import QoSProfile, DurabilityPolicy
    import xml.etree.ElementTree as ET
    peer = Peer()
    profile = yaml.safe_load((Path(get_package_share_directory('mobile_base_control')) /
                              'config/m1.yaml').read_text())
    profile['hardware']['serial_port'] = peer.path
    target = tmp_path / 'hardware.yaml'
    target.write_text(yaml.safe_dump(profile))
    process = subprocess.Popen(
        ['ros2', 'launch', 'mobile_base_description', 'description.launch.py',
         f'hardware_config:={target}'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        start_new_session=True)
    rclpy.init(); node = rclpy.create_node('model_profile_observer')
    descriptions = []
    node.create_subscription(String, '/robot_description', lambda m: descriptions.append(m.data),
                             QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and not descriptions:
            rclpy.spin_once(node, timeout_sec=.05)
        assert descriptions
        assert ET.fromstring(descriptions[-1]).find('ros2_control/hardware/plugin').text == 'mobile_base_control/M1System'
        assert not peer.requests
        assert 'controller_manager' not in [name for name, _ in node.get_node_names_and_namespaces()]
    finally:
        node.destroy_node(); rclpy.shutdown()
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
        try:
            process.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); process.communicate()
        peer.close()


@pytest.mark.parametrize('workflow', [{'require_enable': True, 'cmd_vel_timeout': 3600}], indirect=True)
def test_long_timeout_explicit_zero_and_shutdown(workflow):
    peer, node, publisher, _, _, wait = workflow
    command = TwistStamped()
    command.header.stamp = node.get_clock().now().to_msg()
    command.twist.linear.x = 0.1
    publisher.publish(command)
    wait(lambda: peer.commands and peer.commands[-1] == (95, -95))
    deadline = time.monotonic() + 0.7
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.03)
        assert peer.commands[-1] == (95, -95)
    command.header.stamp = node.get_clock().now().to_msg()
    command.twist.linear.x = 0.0
    publisher.publish(command)
    wait(lambda: peer.commands[-1] == (0, 0), seconds=3)
    command.header.stamp = node.get_clock().now().to_msg()
    command.twist.linear.x = 0.1
    publisher.publish(command)
    wait(lambda: peer.commands[-1] == (95, -95))
    os.killpg(peer.process.pid, signal.SIGINT)
    wait(lambda: not peer.enabled, seconds=5)
    assert peer.targets == [0, 0]
    assert 7 in peer.lifecycle_commands
    assert not peer.alarm_reset_observed


@pytest.mark.parametrize('workflow', [{'require_enable': True, 'cmd_vel_timeout': 3600}], indirect=True)
def test_3600_second_command_age_boundary(workflow):
    from rclpy.duration import Duration
    peer, node, publisher, _, _, wait = workflow
    command = TwistStamped()
    # Exercise the native age calculation without advancing the hardware clock.
    command.header.stamp = (node.get_clock().now() - Duration(seconds=3598.0)).to_msg()
    command.twist.linear.x = 0.1
    published_at = time.monotonic()
    publisher.publish(command)
    wait(lambda: peer.commands and peer.commands[-1] == (95, -95), seconds=1)
    while time.monotonic() - published_at < 1.0:
        rclpy.spin_once(node, timeout_sec=0.03)
        assert peer.commands[-1] == (95, -95)
    wait(lambda: peer.commands[-1] == (0, 0), seconds=3)
    elapsed = time.monotonic() - published_at
    assert 1.8 < elapsed < 3.0


@pytest.mark.parametrize('workflow', [{'covariance': [0.012, 0.023, 0.034, 0.045, 0.056, 0.067]}], indirect=True)
def test_native_odometry_carries_configured_measurement_uncertainty(workflow):
    peer, node, publisher, odom, diagnostics, wait = workflow
    expected = [0.0] * 36
    for index, value in zip((0, 7, 14, 21, 28, 35), (0.012, 0.023, 0.034, 0.045, 0.056, 0.067)):
        expected[index] = value
    assert list(odom[-1].pose.covariance) == expected
    assert list(odom[-1].twist.covariance) == expected
