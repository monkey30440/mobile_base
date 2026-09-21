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

"""ROS 2 driver for the TDK IIM-42652 HandBoard IMU V1."""

import time

from diagnostic_msgs.msg import DiagnosticArray
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_msgs.msg import KeyValue
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
try:
    import ros2top
except ImportError:
    ros2top = None
from sensor_msgs.msg import Imu
import serial

from tdk_ros2_imu.conversions import acceleration_to_si
from tdk_ros2_imu.conversions import angular_velocity_to_si
from tdk_ros2_imu.conversions import quaternion_from_euler_degrees
from tdk_ros2_imu.protocol import ImuSample
from tdk_ros2_imu.protocol import PacketStreamParser


_POLL_PERIOD_SECONDS = 0.005
_DIAGNOSTIC_PERIOD_SECONDS = 0.05
_STALE_TIMEOUT_SECONDS = 0.1
_CHECKSUM_WARNING_PERIOD_SECONDS = 5.0
_COMMUNICATION_FAILURES = {'SERIAL_OPEN_FAILED', 'SERIAL_EXCEPTION'}


def make_imu_diagnostic_status(
        communication: str,
        last_valid_packet_time: float | None,
        checksum_error_count: int,
        now: float) -> DiagnosticStatus:
    """Build the REP-107 status for the current IMU state."""
    status = DiagnosticStatus()
    status.name = 'IMU'
    status.hardware_id = 'tdk_imu'

    if communication in _COMMUNICATION_FAILURES:
        status.level = DiagnosticStatus.ERROR
        status.message = 'Serial communication failed'
    elif (
        communication != 'OK'
        or last_valid_packet_time is None
        or now - last_valid_packet_time > _STALE_TIMEOUT_SECONDS
    ):
        status.level = DiagnosticStatus.STALE
        status.message = 'Valid IMU data is unavailable or stale'
    else:
        status.level = DiagnosticStatus.OK
        status.message = 'Operating normally'

    status.values = [
        KeyValue(key='communication', value=communication),
        KeyValue(
            key='checksum_error_count',
            value=str(checksum_error_count),
        ),
    ]
    return status


class TdkImuNode(Node):
    """Read HandBoard IMU packets and publish sensor_msgs/Imu."""

    def __init__(self) -> None:
        super().__init__('tdk_imu')
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('frame_id', 'base_imu_link')

        self._port = self.get_parameter('port').get_parameter_value().string_value
        self._baud_rate = (
            self.get_parameter('baud_rate').get_parameter_value().integer_value
        )
        self._frame_id = (
            self.get_parameter('frame_id').get_parameter_value().string_value
        )
        self._validate_parameters()

        self._parser = PacketStreamParser()
        self._last_checksum_warning_time = 0.0
        self._last_valid_packet_receive_time = None
        self._communication = 'UNKNOWN'
        self._publisher = self.create_publisher(
            Imu, '/tdk/imu', qos_profile_sensor_data
        )
        self._diagnostic_publisher = self.create_publisher(
            DiagnosticArray, '/diagnostics', 10
        )
        self._serial = None
        self._poll_timer = None
        self._diagnostic_timer = self.create_timer(
            _DIAGNOSTIC_PERIOD_SECONDS, self._publish_diagnostics
        )

        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baud_rate,
                timeout=0,
            )
        except (OSError, serial.SerialException) as error:
            self._communication = 'SERIAL_OPEN_FAILED'
            self.get_logger().fatal(
                f'Failed to open IMU serial port {self._port}: {error}'
            )
            return

        self._communication = 'OK'
        self._poll_timer = self.create_timer(
            _POLL_PERIOD_SECONDS, self._poll_serial
        )
        self.get_logger().info(
            f'Publishing {self._port} at {self._baud_rate} baud '
            f'on /tdk/imu with frame_id={self._frame_id}'
        )

    def _validate_parameters(self) -> None:
        if not self._port:
            raise ValueError('port parameter must not be empty')
        if self._baud_rate <= 0:
            raise ValueError('baud_rate parameter must be greater than zero')
        if not self._frame_id:
            raise ValueError('frame_id parameter must not be empty')

    def _poll_serial(self) -> None:
        try:
            bytes_available = self._serial.in_waiting
            if bytes_available <= 0:
                return
            serial_data = self._serial.read(bytes_available)
        except (OSError, serial.SerialException) as error:
            self.get_logger().fatal(f'IMU serial connection failed: {error}')
            self._communication = 'SERIAL_EXCEPTION'
            self._stop_serial_polling()
            return

        checksum_errors_before = self._parser.checksum_error_count
        samples = self._parser.feed(serial_data)
        if self._parser.checksum_error_count > checksum_errors_before:
            self._warn_checksum_error()

        for sample in samples:
            self._last_valid_packet_receive_time = time.monotonic()
            self._publish_sample(sample)

    def _make_diagnostic_status(self) -> DiagnosticStatus:
        return make_imu_diagnostic_status(
            communication=self._communication,
            last_valid_packet_time=self._last_valid_packet_receive_time,
            checksum_error_count=self._parser.checksum_error_count,
            now=time.monotonic(),
        )

    def _publish_diagnostics(self) -> None:
        message = DiagnosticArray()
        message.header.stamp = self.get_clock().now().to_msg()
        message.status = [self._make_diagnostic_status()]
        self._diagnostic_publisher.publish(message)

    def _warn_checksum_error(self) -> None:
        now = time.monotonic()
        if now - self._last_checksum_warning_time < _CHECKSUM_WARNING_PERIOD_SECONDS:
            return
        self._last_checksum_warning_time = now
        self.get_logger().warning(
            'Discarded an IMU packet with an invalid checksum '
            f'(total={self._parser.checksum_error_count})'
        )

    def _publish_sample(self, sample: ImuSample) -> None:
        acceleration = acceleration_to_si(sample.acceleration_g)
        angular_velocity = angular_velocity_to_si(sample.angular_velocity_dps)
        orientation = quaternion_from_euler_degrees(sample.fusion_rpy_deg)

        message = Imu()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self._frame_id
        message.orientation.x = orientation[0]
        message.orientation.y = orientation[1]
        message.orientation.z = orientation[2]
        message.orientation.w = orientation[3]
        message.angular_velocity.x = angular_velocity[0]
        message.angular_velocity.y = angular_velocity[1]
        message.angular_velocity.z = angular_velocity[2]
        message.angular_velocity_covariance = [
            1.0e-6, 0.0, 0.0,
            0.0, 1.0e-6, 0.0,
            0.0, 0.0, 1.0e-6,
        ]
        message.linear_acceleration.x = acceleration[0]
        message.linear_acceleration.y = acceleration[1]
        message.linear_acceleration.z = acceleration[2]
        self._publisher.publish(message)

    def destroy_node(self) -> None:
        """Stop polling and close the serial port before node destruction."""
        self._stop_serial_polling()
        if self._diagnostic_timer is not None:
            self._diagnostic_timer.cancel()
            self._diagnostic_timer = None
        super().destroy_node()

    def _stop_serial_polling(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.cancel()
            self._poll_timer = None
        if self._serial is not None:
            try:
                if self._serial.is_open:
                    self._serial.close()
            except (OSError, serial.SerialException) as error:
                self.get_logger().error(
                    f'Failed to close IMU serial port: {error}'
                )
            finally:
                self._serial = None


def main(args=None) -> None:
    """Run the ROS 2 IMU driver node."""
    rclpy.init(args=args)
    node = None
    ros2top_node_name = None
    try:
        node = TdkImuNode()
        if ros2top is not None:
            ros2top_node_name = node.get_fully_qualified_name()
            ros2top.register_node(ros2top_node_name)
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if ros2top is not None and ros2top_node_name is not None:
            ros2top.unregister_node(ros2top_node_name)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
