# Copyright 2026 FIH
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

"""Unit tests for TdkImuNode lifecycle, error handling, and publication."""

import struct
from unittest.mock import MagicMock, patch

import pytest
import rclpy
from rclpy.parameter import Parameter
import serial

from tdk_ros2_imu.tdk_imu_node import TdkImuNode


@pytest.fixture(autouse=True)
def rclpy_context():
    """Initialize and teardown rclpy for each test."""
    rclpy.init()
    yield
    if rclpy.ok():
        rclpy.shutdown()


def _make_packet():
    values = (
        0.1, -0.2, 1.0,
        1.0, 2.0,
        3.0, -4.0, 5.0,
        6.0, 7.0, 8.0,
        9.0, -10.0, 11.0,
    )
    packet_without_checksum = b'\xaa\x55' + struct.pack('<14f', *values)
    checksum = 0
    for byte in packet_without_checksum:
        checksum ^= byte
    return packet_without_checksum + bytes((checksum,))


def test_serial_open_failure_raises_runtime_error():
    """Verify serial open exception raises RuntimeError and terminates node."""
    with patch('serial.Serial', side_effect=serial.SerialException('Port not found')):
        with pytest.raises(RuntimeError, match='failed to open IMU serial port'):
            TdkImuNode()


def test_parameter_validation():
    """Verify invalid parameters are rejected during initialization."""
    mock_serial = MagicMock()
    with patch('serial.Serial', return_value=mock_serial):
        # Empty port
        with pytest.raises(ValueError, match='port parameter must not be empty'):
            node = TdkImuNode.__new__(TdkImuNode)
            rclpy.node.Node.__init__(
                node,
                'test_imu_invalid_port',
                parameter_overrides=[
                    Parameter('port', Parameter.Type.STRING, '')
                ]
            )
            node.declare_parameter('port', '/dev/ttyACM0')
            node.declare_parameter('baud_rate', 115200)
            node.declare_parameter('frame_id', 'base_imu_link')
            node._port = node.get_parameter('port').get_parameter_value().string_value
            node._baud_rate = (
                node.get_parameter('baud_rate').get_parameter_value().integer_value
            )
            node._frame_id = (
                node.get_parameter('frame_id').get_parameter_value().string_value
            )
            node._validate_parameters()

        # Non-positive baud rate
        with pytest.raises(ValueError, match='baud_rate parameter must be greater than zero'):
            node = TdkImuNode.__new__(TdkImuNode)
            rclpy.node.Node.__init__(
                node,
                'test_imu_invalid_baud',
                parameter_overrides=[
                    Parameter('baud_rate', Parameter.Type.INTEGER, 0)
                ]
            )
            node.declare_parameter('port', '/dev/ttyACM0')
            node.declare_parameter('baud_rate', 115200)
            node.declare_parameter('frame_id', 'base_imu_link')
            node._port = node.get_parameter('port').get_parameter_value().string_value
            node._baud_rate = (
                node.get_parameter('baud_rate').get_parameter_value().integer_value
            )
            node._frame_id = (
                node.get_parameter('frame_id').get_parameter_value().string_value
            )
            node._validate_parameters()


def test_poll_serial_disconnect_raises_runtime_error():
    """Verify runtime serial disconnect/error triggers RuntimeError."""
    mock_serial = MagicMock()
    mock_serial.in_waiting = 10
    mock_serial.read.side_effect = serial.SerialException('USB device disconnected')

    with patch('serial.Serial', return_value=mock_serial):
        node = TdkImuNode()
        try:
            with pytest.raises(RuntimeError, match='IMU serial connection failed'):
                node._poll_serial()
        finally:
            node.destroy_node()


def test_poll_serial_publishes_valid_imu_message():
    """Verify valid serial bytes are polled and published with correct fields and units."""
    mock_serial = MagicMock()
    packet = _make_packet()
    mock_serial.in_waiting = len(packet)
    mock_serial.read.return_value = packet

    with patch('serial.Serial', return_value=mock_serial):
        node = TdkImuNode()
        try:
            node._publisher = MagicMock()
            node._poll_serial()

            assert node._publisher.publish.call_count == 1
            msg = node._publisher.publish.call_args[0][0]

            assert msg.header.frame_id == 'base_imu_link'
            assert msg.linear_acceleration.x == pytest.approx(0.1 * 9.80665)
            assert msg.linear_acceleration.y == pytest.approx(-0.2 * 9.80665)
            assert msg.linear_acceleration.z == pytest.approx(1.0 * 9.80665)
            assert tuple(msg.linear_acceleration_covariance) == (0.0,) * 9
            assert tuple(msg.angular_velocity_covariance) == (0.0,) * 9
            assert tuple(msg.orientation_covariance) == (0.0,) * 9
        finally:
            node.destroy_node()
