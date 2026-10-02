"""Public topic/diagnostic seam over an OS pseudo terminal, never physical USB."""
import os
import pty
import time
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from diagnostic_msgs.msg import DiagnosticArray
from mobile_base_imu.node import UsbImu
from test_packet import packet


def test_real_serial_topic_invalidity_and_timeout():
    rclpy.init()
    master, slave = pty.openpty()
    path = os.ttyname(slave)
    parameters = ['--ros-args', '-p', f'port:={path}', '-p', 'baud:=115200',
                  '-p', 'protocol_profile:=handboard_v1', '-p', 'acceleration_scale:=9.81',
                  '-p', f'gyro_scale:={math.pi/180}', '-p', 'axes:=[1,2,3]',
                  '-p', 'sample_timeout:=0.25']
    driver = UsbImu(parameters)
    observer = Node('imu_observer')
    samples, diagnostics = [], []
    observer.create_subscription(Imu, 'imu/data_raw', samples.append, 10)
    observer.create_subscription(DiagnosticArray, '/diagnostics', diagnostics.append, 10)
    def spin(seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(driver, timeout_sec=0.005)
            rclpy.spin_once(observer, timeout_sec=0.005)
    try:
        spin(0.4)
        os.write(master, packet([0,0,1,0,0,0,0,90]+[0]*6))
        spin(0.1)
        assert len(samples) == 1
        assert samples[0].header.frame_id == 'base_imu_link'
        assert samples[0].linear_acceleration.z == 9.81
        assert abs(samples[0].angular_velocity.z - math.pi/2) < 1e-6
        assert samples[0].orientation_covariance[0] == -1
        assert list(samples[0].angular_velocity_covariance) == [0.0]*9
        os.write(master, packet([float('nan')]+[0]*13))
        spin(0.1)
        assert len(samples) == 1
        assert any('nonfinite' in status.message for array in diagnostics for status in array.status)
        spin(0.4)
        assert any('timeout' in status.message for array in diagnostics for status in array.status)
        os.close(master)
        master = None
        spin(0.2)
        assert any('communication' in status.message for array in diagnostics for status in array.status)
    finally:
        if master is not None:
            os.close(master)
        os.close(slave)
        driver.destroy_node()
        observer.destroy_node()
        rclpy.shutdown()
