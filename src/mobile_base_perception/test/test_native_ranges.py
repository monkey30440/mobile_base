"""Native UDP compact parser -> LaserScan seam; loopback only, no hardware."""
from pathlib import Path
import os
import signal
import socket
import struct
import subprocess
import threading
import time
import zlib

from ament_index_python.packages import get_package_share_directory, get_package_prefix
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def test_native_scan_bounds_are_stable_and_measurements_unchanged(tmp_path):
    # Upstream compact v4: metadata ends at 132, then 30 beams x 2 layers
    # x (distance:u16, RSSI:u16, property:u8, azimuth:u16). Only the
    # documented distances/counter and CRC are changed in this software fixture.
    original = bytes.fromhex((Path(__file__).parent / 'fixtures/compact-v4.hex').read_text())
    stop = threading.Event()
    distance_mm = [2000]

    def replay():
        counter = 1
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            while not stop.is_set():
                packet = bytearray(original)
                struct.pack_into('<Q', packet, 8, counter)
                for offset in range(132, len(packet) - 4, 7):
                    struct.pack_into('<H', packet, offset, distance_mm[0])
                struct.pack_into('<I', packet, len(packet) - 4, zlib.crc32(packet[:-4]))
                for _ in range(4):
                    sender.sendto(packet, ('127.0.0.1', 32215))
                counter += 1
                stop.wait(0.02)

    thread = threading.Thread(target=replay)
    env = {**os.environ, 'ROS_DOMAIN_ID': '148'}
    native = Path(get_package_share_directory('sick_scan_xd')) / 'launch/sick_picoscan.launch'
    executable = Path(get_package_prefix('sick_scan_xd')) / 'lib/sick_scan_xd/sick_generic_caller'
    log_path = tmp_path / 'native.log'
    context = rclpy.context.Context()
    rclpy.init(context=context, domain_id=148)
    observer = rclpy.create_node('native_range_observer', context=context)
    executor = rclpy.executors.SingleThreadedExecutor(context=context)
    executor.add_node(observer)
    scans = []
    observer.create_subscription(LaserScan, '/range_fixture/segment', scans.append, qos_profile_sensor_data)
    with log_path.open('w') as log:
        process = subprocess.Popen([
            str(executable), str(native),
            'hostname:=127.0.0.2', 'udp_receiver_ip:=127.0.0.1',
            'udp_port:=32215', 'check_udp_receiver_port:=32216',
            'listen_only_mode:=1', 'imu_enable:=0', 'custom_pointclouds:=',
            'host_set_FREchoFilter:=1', 'host_FREchoFilter:=0', 'ros_qos:=4',
            'publish_frame_id:=range_fixture',
            'publish_laserscan_segment_topic:=/range_fixture/segment',
            'publish_laserscan_fullframe_topic:=/range_fixture/full',
            'laserscan_range_min:=0.05', 'laserscan_range_max:=25.0',
        ], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            thread.start()
            received = []
            for mm in (2000, 10000):
                distance_mm[0] = mm
                deadline = time.monotonic() + 15
                selected = None
                while time.monotonic() < deadline:
                    assert process.poll() is None, log_path.read_text()
                    executor.spin_once(timeout_sec=0.1)
                    if (scans and scans[-1].ranges and
                            (not received or scans[-1].header.frame_id == received[0].header.frame_id) and
                            all(abs(r - mm / 1000) < 1e-4 for r in scans[-1].ranges)):
                        selected = scans[-1]
                        break
                assert selected is not None, log_path.read_text()
                received.append(selected)
            for scan in received:
                assert abs(scan.range_min - 0.05) < 1e-6 and scan.range_max == 25.0, (
                    scan.range_min, scan.range_max)
                assert scan.header.frame_id in {'range_fixture_1', 'range_fixture_2'}
            first, second = received
            assert first.header.frame_id == second.header.frame_id
            assert len(first.ranges) == len(second.ranges) > 1
            assert first.intensities == second.intensities
            assert (first.angle_min, first.angle_max, first.angle_increment) == (
                second.angle_min, second.angle_max, second.angle_increment)
            (tmp_path / 'result.txt').write_text(
                f'samples={len(first.ranges)}; bounds=0.05,25; near=2; far=10; angles/intensities unchanged\n')
        finally:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            stop.set()
            thread.join()
            executor.shutdown()
            observer.destroy_node()
            rclpy.shutdown(context=context)
    assert process.returncode == 0, log_path.read_text()
