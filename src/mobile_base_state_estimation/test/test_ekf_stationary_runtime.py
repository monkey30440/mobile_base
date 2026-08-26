# Copyright 2026 Antigravity Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Software-only runtime regressions for the production EKF configuration."""

import math
import os
from pathlib import Path
import signal
import subprocess
import time

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Imu
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster


WHEEL_PERIOD = 1.0 / 50.0
RF2O_PERIOD = 1.0 / 25.0
IMU_PERIOD = 1.0 / 100.0
RUN_DURATION = 6.0

# Explicit test-only covariance diagonals. Unobserved 3D axes are deliberately
# loose; the configured planar twist and yaw-rate channels have finite noise.
ODOM_POSE_DIAGONAL = (0.05, 0.05, 1000.0, 1000.0, 1000.0, 0.1)
WHEEL_TWIST_DIAGONAL = (0.0025, 0.0025, 1000.0, 1000.0, 1000.0, 0.0025)
RF2O_TWIST_DIAGONAL = (0.01, 0.01, 1000.0, 1000.0, 1000.0, 0.01)
IMU_ANGULAR_VELOCITY_DIAGONAL = (0.01, 0.01, 0.0025)
IMU_LINEAR_ACCELERATION_DIAGONAL = (0.04, 0.04, 0.04)


def _diagonal_covariance(size, diagonal):
    covariance = [0.0] * (size * size)
    for index, value in enumerate(diagonal):
        covariance[index * size + index] = value
    return covariance


def _yaw_from_quaternion(quaternion):
    return math.atan2(
        2.0 * (quaternion.w * quaternion.z + quaternion.x * quaternion.y),
        1.0 - 2.0 * (quaternion.y ** 2 + quaternion.z ** 2),
    )


class StationaryEkfHarness(Node):
    """Publish deterministic stationary inputs and collect filtered odometry."""

    def __init__(self, acceleration_bias):
        super().__init__('ekf_stationary_runtime_harness')
        self.acceleration_bias = acceleration_bias
        self.filtered_messages = []
        self.wheel_publisher = self.create_publisher(
            Odometry, '/diff_drive_controller/odom', 10
        )
        self.rf2o_publisher = self.create_publisher(Odometry, '/rf2o/odom', 10)
        self.imu_publisher = self.create_publisher(Imu, '/imu/data_raw', 10)
        self.create_subscription(
            Odometry, '/odometry/filtered', self.filtered_messages.append, 50
        )
        self.tf_broadcaster = StaticTransformBroadcaster(self)
        self._publish_test_transforms()

    def _publish_test_transforms(self):
        stamp = self.get_clock().now().to_msg()

        base_transform = TransformStamped()
        base_transform.header.stamp = stamp
        base_transform.header.frame_id = 'base_footprint'
        base_transform.child_frame_id = 'base_link'
        base_transform.transform.translation.z = 0.2560
        base_transform.transform.rotation.w = 1.0

        imu_transform = TransformStamped()
        imu_transform.header.stamp = stamp
        imu_transform.header.frame_id = 'base_link'
        imu_transform.child_frame_id = 'base_imu_link'
        imu_transform.transform.translation.x = 0.04375
        imu_transform.transform.translation.y = -0.00800
        imu_transform.transform.translation.z = -0.01459
        imu_transform.transform.rotation.z = math.sin(math.pi / 4.0)
        imu_transform.transform.rotation.w = math.cos(math.pi / 4.0)

        self.tf_broadcaster.sendTransform([base_transform, imu_transform])

    def publish_wheel(self):
        self.wheel_publisher.publish(self._stationary_odometry(WHEEL_TWIST_DIAGONAL))

    def publish_rf2o(self):
        self.rf2o_publisher.publish(self._stationary_odometry(RF2O_TWIST_DIAGONAL))

    def _stationary_odometry(self, twist_diagonal):
        message = Odometry()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'odom'
        message.child_frame_id = 'base_footprint'
        message.pose.pose.orientation.w = 1.0
        message.pose.covariance = _diagonal_covariance(6, ODOM_POSE_DIAGONAL)
        message.twist.covariance = _diagonal_covariance(6, twist_diagonal)
        return message

    def publish_imu(self):
        message = Imu()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'base_imu_link'
        message.orientation_covariance[0] = -1.0
        message.angular_velocity_covariance = _diagonal_covariance(
            3, IMU_ANGULAR_VELOCITY_DIAGONAL
        )
        message.linear_acceleration.x = self.acceleration_bias
        message.linear_acceleration.z = 9.80665
        message.linear_acceleration_covariance = _diagonal_covariance(
            3, IMU_LINEAR_ACCELERATION_DIAGONAL
        )
        self.imu_publisher.publish(message)


def _run_stationary_case(acceleration_bias):
    config_path = (
        Path(get_package_share_directory('mobile_base_state_estimation'))
        / 'config'
        / 'ekf.yaml'
    )
    environment = os.environ.copy()
    process = subprocess.Popen(
        [
            'ros2', 'run', 'robot_localization', 'ekf_node',
            '--ros-args', '--params-file', str(config_path),
        ],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    rclpy.init()
    harness = StationaryEkfHarness(acceleration_bias)
    executor = SingleThreadedExecutor()
    executor.add_node(harness)
    started = time.monotonic()
    next_wheel = started
    next_rf2o = started
    next_imu = started

    try:
        while time.monotonic() - started < RUN_DURATION:
            now = time.monotonic()
            if now >= next_wheel:
                harness.publish_wheel()
                next_wheel += WHEEL_PERIOD
            if now >= next_rf2o:
                harness.publish_rf2o()
                next_rf2o += RF2O_PERIOD
            if now >= next_imu:
                harness.publish_imu()
                next_imu += IMU_PERIOD
            executor.spin_once(timeout_sec=0.005)

        assert process.poll() is None, 'ekf_node exited during the runtime test'
        return list(harness.filtered_messages)
    finally:
        executor.remove_node(harness)
        harness.destroy_node()
        rclpy.shutdown()
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
        try:
            output, _ = process.communicate(timeout=5.0)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate(timeout=5.0)
        if process.returncode not in (0, -signal.SIGINT):
            pytest.fail(
                f'ekf_node exited with {process.returncode}:\n{output}',
                pytrace=False,
            )


def _assert_stationary_bounded(messages):
    assert len(messages) >= 100, 'EKF did not produce sustained filtered output'
    samples = messages[len(messages) // 2:]
    values = [
        (
            message.pose.pose.position.x,
            message.pose.pose.position.y,
            _yaw_from_quaternion(message.pose.pose.orientation),
            message.twist.twist.linear.x,
            message.twist.twist.linear.y,
            message.twist.twist.angular.z,
        )
        for message in samples
    ]
    assert all(math.isfinite(value) for sample in values for value in sample)

    for index, bound in enumerate((0.05, 0.05, 0.05, 0.03, 0.03, 0.03)):
        channel = [sample[index] for sample in values]
        assert max(abs(value) for value in channel) < bound
        quarter = max(1, len(channel) // 4)
        early_mean = sum(channel[:quarter]) / quarter
        late_mean = sum(channel[-quarter:]) / quarter
        assert abs(late_mean - early_mean) < bound / 2.0


def test_zero_stationary_inputs_remain_bounded():
    """Catch loss of stable output for zero-valued production EKF inputs."""
    messages = _run_stationary_case(acceleration_bias=0.0)
    _assert_stationary_bounded(messages)


def test_unfused_imu_acceleration_bias_does_not_drive_state():
    """Catch accidental reintroduction of IMU acceleration into fusion."""
    messages = _run_stationary_case(acceleration_bias=0.04)
    _assert_stationary_bounded(messages)
