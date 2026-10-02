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

from diagnostic_msgs.msg import DiagnosticStatus
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


def test_serial_open_failure_keeps_diagnostics_alive():
    """Verify an open failure returns a live node reporting ERROR."""
    with patch('serial.Serial', side_effect=serial.SerialException('Port not found')):
        node = TdkImuNode()
        try:
            node._diagnostic_publisher = MagicMock()
            node._publish_diagnostics()

            status = node._diagnostic_publisher.publish.call_args[0][0].status[0]
            assert status.level == DiagnosticStatus.ERROR
            assert node._communication == 'SERIAL_OPEN_FAILED'
            assert node._poll_timer is None
            assert node._diagnostic_timer is not None
        finally:
            node.destroy_node()


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


@pytest.mark.parametrize(
    'serial_error',
    [serial.SerialException('USB device disconnected'), OSError('I/O error')],
)
def test_poll_serial_failure_stops_polling_and_keeps_error_diagnostics(
        serial_error):
    """Verify failed serial I/O is closed and never polled again."""
    mock_serial = MagicMock()
    mock_serial.is_open = True
    mock_serial.in_waiting = 10
    mock_serial.read.side_effect = serial_error

    with patch('serial.Serial', return_value=mock_serial):
        node = TdkImuNode()
        try:
            poll_timer = MagicMock()
            diagnostic_timer = node._diagnostic_timer
            node._poll_timer = poll_timer

            node._poll_serial()

            poll_timer.cancel.assert_called_once_with()
            mock_serial.close.assert_called_once_with()
            assert node._poll_timer is None
            assert node._diagnostic_timer is diagnostic_timer
            assert node._communication == 'SERIAL_EXCEPTION'
            assert node._make_diagnostic_status().level == DiagnosticStatus.ERROR
        finally:
            node.destroy_node()


def test_serial_close_failure_does_not_terminate_error_diagnostics():
    """Verify a secondary close failure cannot escape the timer callback."""
    mock_serial = MagicMock()
    mock_serial.is_open = True
    mock_serial.in_waiting = 10
    mock_serial.read.side_effect = serial.SerialException('Read failed')
    mock_serial.close.side_effect = OSError('Close failed')

    with patch('serial.Serial', return_value=mock_serial):
        node = TdkImuNode()
        try:
            node._poll_serial()

            assert node._serial is None
            assert node._poll_timer is None
            assert node._make_diagnostic_status().level == DiagnosticStatus.ERROR
        finally:
            node.destroy_node()


def test_destroy_node_cancels_timers_and_closes_serial():
    """Verify shutdown releases both timers and the serial device."""
    mock_serial = MagicMock()
    mock_serial.is_open = True

    with patch('serial.Serial', return_value=mock_serial):
        node = TdkImuNode()
        poll_timer = MagicMock()
        diagnostic_timer = MagicMock()
        node._poll_timer = poll_timer
        node._diagnostic_timer = diagnostic_timer

        node.destroy_node()

        poll_timer.cancel.assert_called_once_with()
        diagnostic_timer.cancel.assert_called_once_with()
        mock_serial.close.assert_called_once_with()
        assert node._poll_timer is None
        assert node._diagnostic_timer is None


def test_poll_serial_publishes_valid_imu_message():
    """Verify valid serial bytes are polled and published with correct fields and units."""
    mock_serial = MagicMock()
    packet = _make_packet()
    mock_serial.in_waiting = len(packet)
    mock_serial.read.return_value = packet

    with patch('serial.Serial', return_value=mock_serial):
        node = TdkImuNode()
        try:
            assert node._communication == 'OK'
            assert node._diagnostic_timer.timer_period_ns == 50_000_000
            node._publisher = MagicMock()
            with patch(
                    'tdk_ros2_imu.tdk_imu_node.time.monotonic',
                    return_value=42.0):
                node._poll_serial()

            assert node._publisher.publish.call_count == 1
            msg = node._publisher.publish.call_args[0][0]

            assert msg.header.frame_id == 'base_imu_link'
            assert msg.linear_acceleration.x == pytest.approx(0.1 * 9.80665)
            assert msg.linear_acceleration.y == pytest.approx(-0.2 * 9.80665)
            assert msg.linear_acceleration.z == pytest.approx(1.0 * 9.80665)
            assert tuple(msg.linear_acceleration_covariance) == (0.0,) * 9
            assert tuple(msg.angular_velocity_covariance) == (
                1.0e-6, 0.0, 0.0,
                0.0, 1.0e-6, 0.0,
                0.0, 0.0, 1.0e-6,
            )
            assert tuple(msg.orientation_covariance) == (0.0,) * 9
            assert node._last_valid_packet_receive_time == 42.0
        finally:
            node.destroy_node()


def test_checksum_failure_does_not_refresh_freshness_or_raise_level():
    """Verify bad packets only increment the parser debugging counter."""
    mock_serial = MagicMock()
    packet = bytearray(_make_packet())
    packet[-1] ^= 0xff
    mock_serial.in_waiting = len(packet)
    mock_serial.read.return_value = bytes(packet)

    with patch('serial.Serial', return_value=mock_serial):
        node = TdkImuNode()
        try:
            node._last_valid_packet_receive_time = 20.0
            node._poll_serial()

            assert node._parser.checksum_error_count == 1
            assert node._last_valid_packet_receive_time == 20.0
            with patch(
                    'tdk_ros2_imu.tdk_imu_node.time.monotonic',
                    return_value=20.050):
                assert node._make_diagnostic_status().level == DiagnosticStatus.OK
            with patch(
                    'tdk_ros2_imu.tdk_imu_node.time.monotonic',
                    return_value=20.101):
                assert node._make_diagnostic_status().level == DiagnosticStatus.STALE
        finally:
            node.destroy_node()
