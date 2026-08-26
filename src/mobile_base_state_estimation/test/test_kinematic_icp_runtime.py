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

"""Software-only runtime verification for Kinematic-ICP PoC (Section 15)."""

import math
import os
from pathlib import Path
import signal
import subprocess
import time

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Imu, LaserScan
from tf2_msgs.msg import TFMessage
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster


WHEEL_PERIOD = 1.0 / 50.0   # 50 Hz
LIDAR_PERIOD = 1.0 / 25.0   # 25 Hz
IMU_PERIOD = 1.0 / 100.0    # 100 Hz
TEST_DURATION = 5.0

ODOM_POSE_COVARIANCE = [0.0] * 36
ODOM_POSE_COVARIANCE[0] = 0.01
ODOM_POSE_COVARIANCE[7] = 0.01
ODOM_POSE_COVARIANCE[35] = 0.01

IMU_ANGULAR_VELOCITY_COVARIANCE = [0.0] * 9
IMU_ANGULAR_VELOCITY_COVARIANCE[8] = 0.0025


def _yaw_from_quaternion(q):
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y ** 2 + q.z ** 2),
    )


class KinematicIcpTestHarness(Node):
    """Test harness node publishing synthetic sensor streams and capturing outputs."""

    def __init__(self, scan_noise=0.0, time_offset_sec=0.0):
        super().__init__('kinematic_icp_test_harness')
        self.scan_noise = scan_noise
        self.time_offset_sec = time_offset_sec
        self.lidar_odom_messages = []
        self.ekf_odom_messages = []

        self.wheel_pub = self.create_publisher(
            Odometry, '/diff_drive_controller/odom', 10
        )
        self.scan_pub = self.create_publisher(
            LaserScan, '/scan_front', 10
        )
        self.imu_pub = self.create_publisher(
            Imu, '/imu/data_raw', 10
        )

        self.create_subscription(
            Odometry, '/lidar_odometry', self.lidar_odom_messages.append, 50
        )
        self.create_subscription(
            Odometry, '/odometry/filtered', self.ekf_odom_messages.append, 50
        )
        self.tf_messages = []
        self.create_subscription(
            TFMessage, '/tf', self.tf_messages.append, 50
        )

        self.tf_broadcaster = StaticTransformBroadcaster(self)
        self._publish_static_transforms()

    def _publish_static_transforms(self):
        stamp = self.get_clock().now().to_msg()

        # 1. base_footprint -> base_link
        t_base = TransformStamped()
        t_base.header.stamp = stamp
        t_base.header.frame_id = 'base_footprint'
        t_base.child_frame_id = 'base_link'
        t_base.transform.translation.z = 0.2560
        t_base.transform.rotation.w = 1.0

        # 2. base_link -> base_lidar_link_FL (roll=pi, pitch=0, yaw=pi/4)
        t_lidar = TransformStamped()
        t_lidar.header.stamp = stamp
        t_lidar.header.frame_id = 'base_link'
        t_lidar.child_frame_id = 'base_lidar_link_FL'
        t_lidar.transform.translation.x = 0.28771
        t_lidar.transform.translation.y = 0.26721
        t_lidar.transform.translation.z = -0.06011
        # RPY: (pi, 0, pi/4)
        cy = math.cos(math.pi / 8.0)
        sy = math.sin(math.pi / 8.0)
        t_lidar.transform.rotation.x = cy
        t_lidar.transform.rotation.y = -sy
        t_lidar.transform.rotation.z = 0.0
        t_lidar.transform.rotation.w = 0.0

        # 3. base_link -> base_imu_link (roll=0, pitch=0, yaw=pi/2)
        t_imu = TransformStamped()
        t_imu.header.stamp = stamp
        t_imu.header.frame_id = 'base_link'
        t_imu.child_frame_id = 'base_imu_link'
        t_imu.transform.translation.x = 0.04375
        t_imu.transform.translation.y = -0.00800
        t_imu.transform.translation.z = -0.01459
        t_imu.transform.rotation.z = math.sin(math.pi / 4.0)
        t_imu.transform.rotation.w = math.cos(math.pi / 4.0)

        self.tf_broadcaster.sendTransform([t_base, t_lidar, t_imu])

    def publish_wheel(self, x=0.0, y=0.0, yaw=0.0):
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_footprint'
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
        msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
        msg.pose.covariance = ODOM_POSE_COVARIANCE
        self.wheel_pub.publish(msg)

    def publish_laserscan(self):
        msg = LaserScan()
        now = self.get_clock().now()
        if self.time_offset_sec != 0.0:
            now = now + rclpy.duration.Duration(seconds=self.time_offset_sec)
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = 'base_lidar_link_FL'
        msg.angle_min = -math.pi * 0.75
        msg.angle_max = math.pi * 0.75
        msg.angle_increment = math.radians(0.5)
        msg.time_increment = 0.00004
        msg.scan_time = LIDAR_PERIOD
        msg.range_min = 0.1
        msg.range_max = 25.0

        num_readings = int((msg.angle_max - msg.angle_min) / msg.angle_increment) + 1
        ranges = []
        for i in range(num_readings):
            base_range = 4.0
            if self.scan_noise > 0.0:
                base_range += self.scan_noise * math.sin(i * 0.2)
            ranges.append(base_range)

        msg.ranges = ranges
        msg.intensities = [100.0] * num_readings
        self.scan_pub.publish(msg)

    def publish_imu(self):
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_imu_link'
        msg.angular_velocity.z = 0.0
        msg.angular_velocity_covariance = IMU_ANGULAR_VELOCITY_COVARIANCE
        msg.linear_acceleration.z = 9.80665
        msg.orientation_covariance[0] = -1.0
        self.imu_pub.publish(msg)


def _run_test_pipeline(scan_noise=0.0, time_offset_sec=0.0):
    kicp_config_path = (
        Path(get_package_share_directory('kinematic_icp'))
        / 'config'
        / 'kinematic_icp_ros.yaml'
    )
    ekf_config_path = (
        Path(get_package_share_directory('mobile_base_state_estimation'))
        / 'config'
        / 'ekf_kinematic_icp.yaml'
    )

    env = os.environ.copy()

    kicp_proc = subprocess.Popen(
        [
            'ros2', 'run', 'kinematic_icp', 'kinematic_icp_online_node',
            '--ros-args', '--params-file', str(kicp_config_path),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    ekf_proc = subprocess.Popen(
        [
            'ros2', 'run', 'robot_localization', 'ekf_node',
            '--ros-args', '--params-file', str(ekf_config_path),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    rclpy.init()
    harness = KinematicIcpTestHarness(scan_noise=scan_noise, time_offset_sec=time_offset_sec)
    executor = SingleThreadedExecutor()
    executor.add_node(harness)

    started = time.monotonic()
    next_wheel = started
    next_lidar = started + 0.1
    next_imu = started

    try:
        while time.monotonic() - started < TEST_DURATION:
            now = time.monotonic()
            if now >= next_wheel:
                harness.publish_wheel()
                next_wheel += WHEEL_PERIOD
            if now >= next_lidar:
                harness.publish_laserscan()
                next_lidar += LIDAR_PERIOD
            if now >= next_imu:
                harness.publish_imu()
                next_imu += IMU_PERIOD
            executor.spin_once(timeout_sec=0.005)

        assert kicp_proc.poll() is None, 'kinematic_icp_online_node exited unexpectedly'
        assert ekf_proc.poll() is None, 'ekf_node exited unexpectedly'

        return (
            list(harness.lidar_odom_messages),
            list(harness.ekf_odom_messages),
            list(harness.tf_messages),
        )
    finally:
        executor.remove_node(harness)
        harness.destroy_node()
        rclpy.shutdown()

        for proc in (kicp_proc, ekf_proc):
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.communicate(timeout=3.0)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate(timeout=3.0)


def test_runtime_a_stationary_kinematic_icp_and_ekf():
    """Test A: Stationary robot with constant wheel pose, stationary lidar, zero IMU yaw rate."""
    lidar_msgs, ekf_msgs, tf_msgs = _run_test_pipeline(scan_noise=0.0, time_offset_sec=0.0)

    assert len(lidar_msgs) >= 20, (
        f'Kinematic-ICP produced insufficient messages: {len(lidar_msgs)}'
    )
    assert len(ekf_msgs) >= 50, f'EKF produced insufficient messages: {len(ekf_msgs)}'

    # Frame semantics verification: /lidar_odometry frame is odom, child is base_footprint
    for msg in lidar_msgs:
        assert msg.header.frame_id == 'odom', (
            f"Expected lidar_odom header.frame_id 'odom', got '{msg.header.frame_id}'"
        )
        assert msg.child_frame_id == 'base_footprint', (
            f"Expected lidar_odom child_frame_id 'base_footprint', got '{msg.child_frame_id}'"
        )

    # Frame semantics verification: /odometry/filtered frame is odom, child is base_footprint
    for msg in ekf_msgs:
        assert msg.header.frame_id == 'odom', (
            f"Expected EKF header.frame_id 'odom', got '{msg.header.frame_id}'"
        )
        assert msg.child_frame_id == 'base_footprint', (
            f"Expected EKF child_frame_id 'base_footprint', got '{msg.child_frame_id}'"
        )

    # TF authority verification: EKF is sole dynamic broadcaster for odom -> base_footprint
    assert len(tf_msgs) > 0, 'No transforms captured on /tf'
    for tf_batch in tf_msgs:
        for t in tf_batch.transforms:
            assert t.header.frame_id == 'odom', f'Unexpected TF parent frame: {t.header.frame_id}'
            assert t.child_frame_id == 'base_footprint', (
                f'Unexpected TF child frame: {t.child_frame_id}'
            )
            assert 'odom_lidar' not in t.header.frame_id
            assert 'odom_lidar' not in t.child_frame_id

    # Check finite output and bounded drift for Kinematic-ICP
    for msg in lidar_msgs[len(lidar_msgs) // 2:]:
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        yaw = _yaw_from_quaternion(msg.pose.pose.orientation)
        assert math.isfinite(x) and math.isfinite(y) and math.isfinite(yaw)
        assert abs(x) < 0.05, f'Stationary Kinematic-ICP X drift exceeded: {x}'
        assert abs(y) < 0.05, f'Stationary Kinematic-ICP Y drift exceeded: {y}'
        assert abs(yaw) < 0.05, f'Stationary Kinematic-ICP Yaw drift exceeded: {yaw}'

    # Check finite output and bounded drift for EKF
    for msg in ekf_msgs[len(ekf_msgs) // 2:]:
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        yaw = _yaw_from_quaternion(msg.pose.pose.orientation)
        assert math.isfinite(x) and math.isfinite(y) and math.isfinite(yaw)
        assert abs(x) < 0.05, f'Stationary EKF X drift exceeded: {x}'
        assert abs(y) < 0.05, f'Stationary EKF Y drift exceeded: {y}'
        assert abs(yaw) < 0.05, f'Stationary EKF Yaw drift exceeded: {yaw}'


def test_runtime_b_interpolation_non_identical_frequencies():
    """Test B: Wheel at 50Hz, LaserScan at 25Hz with non-identical interleaved timestamps."""
    lidar_msgs, _, _ = _run_test_pipeline(scan_noise=0.0, time_offset_sec=0.005)

    assert len(lidar_msgs) >= 20, (
        f'Kinematic-ICP failed to process interpolated timestamps: got {len(lidar_msgs)} msgs'
    )
    for msg in lidar_msgs:
        assert math.isfinite(msg.pose.pose.position.x)
        assert math.isfinite(msg.pose.pose.position.y)


def test_runtime_c_small_scan_noise_while_wheel_stationary():
    """Test C: Small scan noise perturbations while wheel is strictly stationary."""
    lidar_msgs, ekf_msgs, _ = _run_test_pipeline(scan_noise=0.01, time_offset_sec=0.0)

    assert len(lidar_msgs) >= 20
    assert len(ekf_msgs) >= 50

    for msg in lidar_msgs[len(lidar_msgs) // 2:]:
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        assert math.isfinite(x) and math.isfinite(y)
        assert abs(x) < 0.10, f'Scan noise caused excessive drift in X: {x}'
        assert abs(y) < 0.10, f'Scan noise caused excessive drift in Y: {y}'


class DeterministicEkfFusionHarness(Node):
    """Harness to feed deterministic /lidar_odometry displacements directly into EKF."""

    def __init__(self):
        super().__init__('deterministic_ekf_fusion_harness')
        self.ekf_odom_messages = []
        self.tf_messages = []

        self.lidar_pub = self.create_publisher(
            Odometry, '/lidar_odometry', 10
        )
        self.imu_pub = self.create_publisher(
            Imu, '/imu/data_raw', 10
        )
        self.create_subscription(
            Odometry, '/odometry/filtered', self.ekf_odom_messages.append, 50
        )
        self.create_subscription(
            TFMessage, '/tf', self.tf_messages.append, 50
        )

        self.tf_broadcaster = StaticTransformBroadcaster(self)
        self._publish_static_transforms()

    def _publish_static_transforms(self):
        stamp = self.get_clock().now().to_msg()

        t_base = TransformStamped()
        t_base.header.stamp = stamp
        t_base.header.frame_id = 'base_footprint'
        t_base.child_frame_id = 'base_link'
        t_base.transform.translation.z = 0.2560
        t_base.transform.rotation.w = 1.0

        t_imu = TransformStamped()
        t_imu.header.stamp = stamp
        t_imu.header.frame_id = 'base_link'
        t_imu.child_frame_id = 'base_imu_link'
        t_imu.transform.translation.x = 0.04375
        t_imu.transform.translation.y = -0.00800
        t_imu.transform.translation.z = -0.01459
        t_imu.transform.rotation.z = math.sin(math.pi / 4.0)
        t_imu.transform.rotation.w = math.cos(math.pi / 4.0)

        self.tf_broadcaster.sendTransform([t_base, t_imu])

    def publish_lidar_odom(self, x=0.0, y=0.0, yaw=0.0):
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_footprint'
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
        msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
        msg.pose.covariance = ODOM_POSE_COVARIANCE
        self.lidar_pub.publish(msg)

    def publish_imu(self):
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_imu_link'
        msg.angular_velocity.z = 0.0
        msg.angular_velocity_covariance = IMU_ANGULAR_VELOCITY_COVARIANCE
        msg.linear_acceleration.z = 9.80665
        msg.orientation_covariance[0] = -1.0
        self.imu_pub.publish(msg)


def test_runtime_d_ekf_accepts_and_fuses_kinematic_icp_pose():
    """Test D: Verify EKF accepts and fuses Kinematic-ICP x/y/yaw pose displacement."""
    ekf_config_path = (
        Path(get_package_share_directory('mobile_base_state_estimation'))
        / 'config'
        / 'ekf_kinematic_icp.yaml'
    )
    env = os.environ.copy()
    ekf_proc = subprocess.Popen(
        [
            'ros2', 'run', 'robot_localization', 'ekf_node',
            '--ros-args', '--params-file', str(ekf_config_path),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    rclpy.init()
    harness = DeterministicEkfFusionHarness()
    executor = SingleThreadedExecutor()
    executor.add_node(harness)

    started = time.monotonic()
    next_lidar = started
    next_imu = started

    target_x = 1.0
    target_y = 0.5
    target_yaw = 0.4

    try:
        while time.monotonic() - started < 5.0:
            elapsed = time.monotonic() - started
            now = time.monotonic()
            if now >= next_lidar:
                # Step after 1.0s to target_x, target_y, target_yaw
                if elapsed > 1.0:
                    harness.publish_lidar_odom(target_x, target_y, target_yaw)
                else:
                    harness.publish_lidar_odom(0.0, 0.0, 0.0)
                next_lidar += LIDAR_PERIOD
            if now >= next_imu:
                harness.publish_imu()
                next_imu += IMU_PERIOD
            executor.spin_once(timeout_sec=0.005)

        assert ekf_proc.poll() is None, 'ekf_node exited unexpectedly'
        ekf_msgs = list(harness.ekf_odom_messages)
        assert len(ekf_msgs) >= 50, f'Insufficient EKF messages: {len(ekf_msgs)}'

        # Filtered output in late phase must have responded to target_x, target_y, target_yaw
        late_msgs = ekf_msgs[len(ekf_msgs) * 3 // 4:]
        assert len(late_msgs) > 0

        latest = late_msgs[-1]
        fused_x = latest.pose.pose.position.x
        fused_y = latest.pose.pose.position.y
        fused_yaw = _yaw_from_quaternion(latest.pose.pose.orientation)

        assert math.isfinite(fused_x) and math.isfinite(fused_y) and math.isfinite(fused_yaw)
        assert fused_x > 0.5, f'EKF failed to fuse /lidar_odometry X: {fused_x}'
        assert fused_y > 0.2, f'EKF failed to fuse /lidar_odometry Y: {fused_y}'
        assert fused_yaw > 0.15, f'EKF failed to fuse /lidar_odometry Yaw: {fused_yaw}'

        assert latest.header.frame_id == 'odom'
        assert latest.child_frame_id == 'base_footprint'
    finally:
        executor.remove_node(harness)
        harness.destroy_node()
        rclpy.shutdown()
        if ekf_proc.poll() is None:
            os.killpg(ekf_proc.pid, signal.SIGINT)
        try:
            ekf_proc.communicate(timeout=3.0)
        except subprocess.TimeoutExpired:
            os.killpg(ekf_proc.pid, signal.SIGKILL)
            ekf_proc.communicate(timeout=3.0)
