"""Native EKF public odom/TF seam; synthetic measurements, no hardware."""
import os
import signal
import subprocess
import time

import pytest
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from tf2_ros import Buffer, TransformListener
from tf2_msgs.msg import TFMessage
import yaml


@pytest.mark.parametrize('installed_profile', [False, True])
def test_native_wheel_imu_fusion_and_single_odom_tf_owner(tmp_path, installed_profile):
    # Declared synthetic uncertainties are fixtures, never deployment calibration.
    config = {'ekf_filter_node': {'ros__parameters': {
        'frequency': 30.0, 'sensor_timeout': 0.2, 'two_d_mode': True,
        'publish_tf': True, 'print_diagnostics': True,
        'odom_frame': 'odom', 'base_link_frame': 'base_footprint', 'world_frame': 'odom',
        'odom0': '/fixture/wheel_odom',
        'odom0_config': [False]*6 + [True, True, False, False, False, False] + [False]*3,
        'imu0': '/fixture/imu',
        'imu0_config': [False]*11 + [True] + [False]*3,
    }}}
    if installed_profile:
        from pathlib import Path
        from ament_index_python.packages import get_package_share_directory
        packaged = Path(get_package_share_directory('mobile_base_odometry')) / 'config/ekf.yaml'
        config = yaml.safe_load(packaged.read_text())
        wheel_topic, imu_topic = '/base_controller/odom', '/imu/data_raw'
    else:
        wheel_topic, imu_topic = '/fixture/wheel_odom', '/fixture/imu'
    profile = tmp_path / 'synthetic-ekf.yaml'
    profile.write_text(yaml.safe_dump(config))
    # The physical IMU origin follows the authoritative CAD URDF; no scan aliases.
    model = '<robot name="estimation_fixture"><link name="base_footprint"/><link name="base_link"/><link name="base_imu_link"/><joint name="base" type="fixed"><parent link="base_footprint"/><child link="base_link"/><origin xyz="0 0 0.256"/></joint><joint name="imu" type="fixed"><parent link="base_link"/><child link="base_imu_link"/><origin xyz="0.04375 -0.008 -0.01459"/></joint></robot>'
    rsp_config = tmp_path / 'model.yaml'
    rsp_config.write_text(yaml.safe_dump({'robot_state_publisher': {'ros__parameters': {'robot_description': model}}}))
    rclpy.init()
    observer = Node('estimation_fixture_observer')
    buffer = Buffer()
    listener = TransformListener(buffer, observer)
    wheel = observer.create_publisher(Odometry, wheel_topic, 10)
    gyro = observer.create_publisher(Imu, imu_topic, 10)
    samples = []
    odom_transforms = []
    def observe_tf(message):
        odom_transforms.extend(t for t in message.transforms
                               if t.header.frame_id == 'odom' and t.child_frame_id == 'base_footprint')
    observer.create_subscription(TFMessage, '/tf', observe_tf, 100)
    observer.create_subscription(Odometry, '/odometry/filtered', samples.append, 10)
    processes = []
    logs = []
    try:
        for args, name in [
            (['ros2', 'run', 'robot_state_publisher', 'robot_state_publisher', '--ros-args', '--params-file', str(rsp_config)], 'model'),
            (['ros2', 'launch', 'mobile_base_odometry', 'odometry.launch.py', f'filter_config:={packaged if installed_profile else profile}'], 'ekf'),
        ]:
            log = open(tmp_path / (name + '.log'), 'w')
            logs.append(log)
            processes.append(subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            assert all(p.poll() is None for p in processes), (tmp_path / 'ekf.log').read_text()
            stamp = observer.get_clock().now().to_msg()
            odom = Odometry()
            odom.header.stamp = stamp
            odom.header.frame_id = 'odom'
            odom.child_frame_id = 'base_footprint'
            odom.twist.twist.linear.x = 0.2
            odom.twist.covariance[0] = odom.twist.covariance[7] = 0.01
            wheel.publish(odom)
            imu = Imu()
            imu.header.stamp = stamp
            imu.header.frame_id = 'base_imu_link'
            imu.orientation_covariance[0] = -1.0
            imu.angular_velocity.z = 0.5
            imu.angular_velocity_covariance = [0.01, 0.0, 0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.01]
            gyro.publish(imu)
            rclpy.spin_once(observer, timeout_sec=0.03)
            if (samples and samples[-1].pose.pose.position.x > 0.03
                    and samples[-1].pose.pose.orientation.z > 0.03
                    and abs(samples[-1].twist.twist.linear.x - 0.2) < 0.03
                    and abs(samples[-1].twist.twist.angular.z - 0.5) < 0.03
                    and buffer.can_transform('odom', 'base_imu_link', rclpy.time.Time())):
                break
        assert samples, (tmp_path / 'ekf.log').read_text()
        result = samples[-1]
        assert result.header.frame_id == 'odom'
        assert result.child_frame_id == 'base_footprint'
        assert result.twist.twist.linear.x == pytest.approx(0.2, abs=0.03)
        assert result.twist.twist.angular.z == pytest.approx(0.5, abs=0.03)
        assert result.pose.pose.position.x > 0.03
        assert result.pose.pose.orientation.z > 0.03
        buffer.lookup_transform('odom', 'base_imu_link', rclpy.time.Time())
        # RSP advertises /tf even with no moving joints. Topic publisher count
        # alone cannot establish ownership of a particular transform.
        assert {i.node_name for i in observer.get_publishers_info_by_topic('/tf')} == {
            'robot_state_publisher', 'ekf_filter_node'}
        assert odom_transforms
        assert [i.node_name for i in observer.get_publishers_info_by_topic('/tf_static')] == ['robot_state_publisher']
        os.killpg(processes[1].pid, signal.SIGINT)
        processes[1].wait(timeout=5)
        # Drain queued messages, then show the odom edge stops with EKF while
        # the separate model publisher stays alive and its static TF remains.
        deadline = time.monotonic() + 0.3
        while time.monotonic() < deadline:
            rclpy.spin_once(observer, timeout_sec=0.01)
        odom_transforms.clear()
        deadline = time.monotonic() + 0.3
        while time.monotonic() < deadline:
            rclpy.spin_once(observer, timeout_sec=0.01)
        assert not odom_transforms
        assert processes[0].poll() is None
        buffer.lookup_transform('base_footprint', 'base_imu_link', rclpy.time.Time())
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for log in logs:
            log.close()
        observer.destroy_node()
        rclpy.shutdown()
