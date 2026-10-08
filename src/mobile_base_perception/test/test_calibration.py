"""Operator calibration CLI at the public raw ROS topic seam; no hardware."""
import os
import signal
import subprocess
import time

import pytest
import rclpy
from sensor_msgs.msg import Imu
import yaml


def test_operator_can_save_reviewable_stationary_calibration(tmp_path, monkeypatch):
    monkeypatch.setenv('ROS_DOMAIN_ID', '153')
    rclpy.init()
    node = rclpy.create_node('calibration_fixture')
    publisher = node.create_publisher(Imu, '/imu/data_raw', 10)
    output = tmp_path / 'calibration.yaml'
    log_path = tmp_path / 'calibration.log'
    with log_path.open('w') as log:
        process = subprocess.Popen([
            'ros2', 'run', 'mobile_base_perception', 'calibrate_imu',
            '--stationary', '--duration', '0.6', '--min-samples', '20',
            '--output', str(output), '--wait-timeout', '3.0',
        ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 8
            count = 0
            while process.poll() is None and time.monotonic() < deadline:
                sample = Imu()
                sample.header.stamp = node.get_clock().now().to_msg()
                sample.header.frame_id = 'base_imu_link'
                noise = 1 if count % 2 else -1
                sample.angular_velocity.x = 0.01 + noise * 0.001
                sample.angular_velocity.y = -0.02 + noise * 0.002
                sample.angular_velocity.z = 0.03 + noise * 0.003
                publisher.publish(sample)
                count += 1
                rclpy.spin_once(node, timeout_sec=0.02)
            assert process.wait(timeout=1) == 0, log_path.read_text()
            result = yaml.safe_load(output.read_text())
            assert result['frame_id'] == 'base_imu_link'
            assert result['units'] == 'rad/s'
            assert result['source_topic'] == '/imu/data_raw'
            assert result['sample_count'] >= 20
            assert result['duration_seconds'] >= 0.6
            assert result['angular_velocity_bias'] == pytest.approx([.01, -.02, .03], abs=.0002)
            assert result['angular_velocity_variances'] == pytest.approx([1e-6, 4e-6, 9e-6], rel=.1)
            assert result['calibrated_at_utc']
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=5)
            node.destroy_node()
            rclpy.shutdown()


@pytest.mark.parametrize('case', ['no_confirmation', 'existing_output', 'no_data'])
def test_calibration_refuses_invalid_operator_workflow(tmp_path, monkeypatch, case):
    monkeypatch.setenv('ROS_DOMAIN_ID', '155')
    output = tmp_path / 'calibration.yaml'
    if case == 'existing_output':
        output.write_text('preserve this calibration\n')
    args = ['ros2','run','mobile_base_perception','calibrate_imu',
            '--output', str(output), '--wait-timeout', '0.3', '--duration', '0.2']
    if case != 'no_confirmation':
        args.append('--stationary')
    result = subprocess.run(args, capture_output=True, text=True, timeout=5)
    assert result.returncode != 0
    if case == 'existing_output':
        assert output.read_text() == 'preserve this calibration\n'
    else:
        assert not output.exists()
    reason = {'no_confirmation':'--stationary', 'existing_output':'new file', 'no_data':'no raw IMU samples'}[case]
    assert reason in result.stdout + result.stderr


@pytest.mark.parametrize('invalid', ['frame', 'nonfinite', 'timestamp', 'interrupted'])
def test_calibration_rejects_invalid_raw_capture_without_saved_result(tmp_path, monkeypatch, invalid):
    monkeypatch.setenv('ROS_DOMAIN_ID', str(160 + ['frame', 'nonfinite', 'timestamp', 'interrupted'].index(invalid)))
    rclpy.init()
    node = rclpy.create_node('invalid_calibration_fixture')
    publisher = node.create_publisher(Imu, '/imu/data_raw', 10)
    output = tmp_path / 'rejected.yaml'
    log_path = tmp_path / 'capture.log'
    with log_path.open('w') as log:
        process = subprocess.Popen([
            'ros2', 'run', 'mobile_base_perception', 'calibrate_imu',
            '--stationary', '--duration', '1.0', '--min-samples', '2',
            '--output', str(output), '--wait-timeout', '3.0',
        ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 6
            sent_at = None
            fixed_stamp = node.get_clock().now().to_msg()
            while process.poll() is None and time.monotonic() < deadline:
                # Wait for the actual CLI subscriber before injecting the fault.
                if publisher.get_subscription_count() and (sent_at is None or invalid != 'interrupted'):
                    sample = Imu()
                    sample.header.stamp = fixed_stamp if invalid == 'timestamp' else node.get_clock().now().to_msg()
                    sample.header.frame_id = 'wrong_frame' if invalid == 'frame' else 'base_imu_link'
                    sample.angular_velocity.z = float('nan') if invalid == 'nonfinite' else .01
                    publisher.publish(sample)
                    sent_at = time.monotonic()
                rclpy.spin_once(node, timeout_sec=.02)
            assert process.wait(timeout=1) != 0, log_path.read_text()
            assert not output.exists()
            reason = {'frame': 'frame/rate', 'nonfinite': 'frame/rate',
                      'timestamp': 'timestamp discontinuity',
                      'interrupted': 'stream stopped'}[invalid]
            assert reason in log_path.read_text()
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=5)
            node.destroy_node()
            rclpy.shutdown()
