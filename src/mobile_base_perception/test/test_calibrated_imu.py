"""Installed IMU entry, real PTY packets, public raw/corrected ROS sources."""
import os
import pty
import signal
import subprocess
import time

import pytest
import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from sensor_msgs.msg import Imu
import yaml
from test_packet import packet


@pytest.mark.parametrize('case', ['valid', 'missing', 'wrong_frame', 'nonfinite_bias'])
def test_fixed_calibration_preserves_raw_and_real_slow_rotation(tmp_path, monkeypatch, case):
    monkeypatch.setenv('ROS_DOMAIN_ID', '154')
    rclpy.init()
    master, slave = pty.openpty()
    calibration = {'frame_id': 'base_imu_link', 'units': 'rad/s', 'source_topic': '/imu/data_raw',
                   'calibrated_at_utc': '2026-10-08T00:00:00+00:00', 'sample_count': 100,
                   'duration_seconds': 1.0, 'first_sample_stamp': 1.0, 'last_sample_stamp': 2.0,
                   'angular_velocity_bias': [.01, -.02, .02],
                   'angular_velocity_variances': [1e-4, 4e-4, 9e-4]}
    if case == 'wrong_frame':
        calibration['frame_id'] = 'base_link'
    if case == 'nonfinite_bias':
        calibration['angular_velocity_bias'][2] = float('nan')
    if case != 'missing':
        (tmp_path / 'calibration.yaml').write_text(yaml.safe_dump(calibration))
    config = tmp_path / 'imu.yaml'
    config.write_text(yaml.safe_dump({'usb_imu': {'ros__parameters': {
        'port': os.ttyname(slave), 'baud': 115200, 'protocol_profile': 'handboard_v1',
        'acceleration_scale': 9.81, 'gyro_scale': 1.0, 'axes': [1,2,3],
        'sample_timeout': 1.0, 'calibration_file': 'calibration.yaml'}}}))
    observer = rclpy.create_node('calibrated_imu_observer')
    raw, corrected, diagnostics = [], [], []
    observer.create_subscription(Imu, '/imu/data_raw', raw.append, 10)
    observer.create_subscription(Imu, '/imu/data', corrected.append, 10)
    observer.create_subscription(DiagnosticArray, '/diagnostics', diagnostics.append, 10)
    log_path = tmp_path / 'imu.log'
    with log_path.open('w') as log:
        process = subprocess.Popen(['ros2','launch','mobile_base_perception','imu.launch.py',
                                    'imu_config:=' + str(config)], stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 6
            while not raw and time.monotonic() < deadline:
                assert process.poll() is None, log_path.read_text()
                os.write(master, packet([0,0,1,0,0,.04,-.01,.02]+[0]*6))
                rclpy.spin_once(observer, timeout_sec=.02)
            assert raw, log_path.read_text()
            if case != 'valid':
                deadline = time.monotonic() + .3
                while time.monotonic() < deadline:
                    os.write(master, packet([0,0,1,0,0,.04,-.01,.02]+[0]*6))
                    rclpy.spin_once(observer, timeout_sec=.02)
                assert not corrected, 'invalid/missing calibration must never fall back to raw or zero bias'
                assert any('corrected unavailable' in status.message
                           for array in diagnostics for status in array.status)
                return
            for source_rate, expected in [(.12,.10),(-.08,-.10),(.0201,.0001)]:
                raw.clear(); corrected.clear()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    os.write(master, packet([0,0,1,0,0,.04,-.01,source_rate]+[0]*6))
                    rclpy.spin_once(observer, timeout_sec=.02)
                    matched = [(original, compensated) for original in raw for compensated in corrected
                               if original.header.stamp == compensated.header.stamp
                               and abs(compensated.angular_velocity.z - expected) < 1e-7]
                    if matched:
                        break
                assert matched, log_path.read_text()
                original, m = matched[-1]
                assert original.angular_velocity.z == pytest.approx(source_rate, abs=1e-7)
                assert m.angular_velocity.x == pytest.approx(.03, abs=1e-7)
                assert m.angular_velocity.y == pytest.approx(.01, abs=1e-7)
                assert m.angular_velocity.z == pytest.approx(expected, abs=1e-7)
                assert m.header.frame_id == 'base_imu_link'
                assert m.orientation_covariance[0] == -1
                assert m.linear_acceleration.z == pytest.approx(9.81)
                assert list(m.angular_velocity_covariance) == [1e-4,0,0,0,4e-4,0,0,0,9e-4]
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT); process.wait(timeout=8)
            observer.destroy_node(); rclpy.shutdown()
            os.close(master); os.close(slave)
