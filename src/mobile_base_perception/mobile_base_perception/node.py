"""USB bridge transport and device diagnostics, with receipt-time ROS output."""
import math
import os
import termios
import time

import diagnostic_updater
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from diagnostic_msgs.msg import DiagnosticStatus

from .packet import decode


class UsbImu(Node):
    def __init__(self, cli_args=None):
        super().__init__('usb_imu', cli_args=cli_args)
        defaults = {'port': '', 'baud': 0, 'protocol_profile': '',
                    'acceleration_scale': 0.0, 'gyro_scale': 0.0,
                    'axes': [0, 0, 0], 'sample_timeout': 0.0,
                    'angular_velocity_variances': [0.0, 0.0, 0.0]}
        config = {key: self.declare_parameter(key, value).value
                  for key, value in defaults.items()}
        self.fd = None
        self.buffer = bytearray()
        self.last_sample = time.monotonic()
        self.last_error = 'awaiting valid sample'
        self.last_event_valid = False
        self.invalid_packets = 0
        self.received_samples = 0
        self.config = config
        self.publisher = self.create_publisher(Imu, 'imu/data_raw', 10)
        self.updater = diagnostic_updater.Updater(self)
        self.updater.setHardwareID(config['port'] or 'unconfigured USB IMU')
        self.updater.add('USB IMU', self.diagnostic)
        self.configuration_error = self.validate(config)
        self.communication_error = ''
        if not self.configuration_error:
            self.open_port()
        self.create_timer(0.01, self.poll)
        self.create_timer(0.1, self.updater.force_update)

    @staticmethod
    def validate(config):
        variances = config['angular_velocity_variances']
        if (len(variances) != 3 or not all(math.isfinite(value) for value in variances)
                or not (all(value == 0 for value in variances) or all(value > 0 for value in variances))):
            return 'configuration: angular_velocity_variances require three finite positive values or all zeros'
        if config['protocol_profile'] != 'handboard_v1':
            return 'configuration: confirm protocol_profile=handboard_v1'
        baud = config['baud']
        if not config['port'] or type(baud) is not int or baud <= 0 or not hasattr(termios, 'B' + str(baud)):
            return 'configuration: explicit port and supported baud required'
        for key in ('acceleration_scale', 'gyro_scale', 'sample_timeout'):
            if not math.isfinite(config[key]) or config[key] <= 0:
                return f'configuration: positive finite {key} required'
        axes = config['axes']
        if sorted(abs(axis) for axis in axes) != [1, 2, 3]:
            return 'configuration: axes must be signed permutation of 1,2,3'
        inversions = sum(abs(axes[i]) > abs(axes[j])
                         for i in range(3) for j in range(i+1, 3))
        sign = math.prod(1 if axis > 0 else -1 for axis in axes)
        if sign * (-1)**inversions != 1:
            return 'configuration: axes must preserve right-handed coordinates'
        return ''

    def open_port(self):
        try:
            self.fd = os.open(self.config['port'], os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
            attributes = termios.tcgetattr(self.fd)
            attributes[0] = 0
            attributes[1] = 0
            attributes[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            attributes[3] = 0
            attributes[4] = attributes[5] = getattr(termios, 'B' + str(self.config['baud']))
            attributes[6][termios.VMIN] = 1
            attributes[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, attributes)
        except (OSError, termios.error) as error:
            self.communication_error = f'communication: {error}'
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None

    def poll(self):
        if self.fd is None:
            return
        try:
            data = os.read(self.fd, 4096)
            if not data:
                raise OSError('USB stream disconnected')
        except BlockingIOError:
            return
        except OSError as error:
            self.communication_error = f'communication: {error}'
            os.close(self.fd)
            self.fd = None
            return
        self.buffer.extend(data)
        while self.buffer:
            header = self.buffer.find(b'\xaa\x55')
            if header < 0:
                self.buffer[:] = b'\xaa' if self.buffer[-1] == 0xaa else b''
                self.last_error = 'packet framing invalid'
                self.last_event_valid = False
                break
            if header:
                del self.buffer[:header]
                self.last_error = 'packet framing invalid'
                self.last_event_valid = False
            if len(self.buffer) < 59:
                break
            try:
                acceleration, gyro = decode(bytes(self.buffer[:59]),
                                            self.config['acceleration_scale'],
                                            self.config['gyro_scale'], self.config['axes'])
                if not all(math.isfinite(value) for value in acceleration + gyro):
                    raise ValueError('converted data nonfinite')
            except ValueError as error:
                self.invalid_packets += 1
                self.last_error = str(error)
                self.last_event_valid = False
                del self.buffer[0]
                self.updater.force_update()
                continue
            del self.buffer[:59]
            message = Imu()
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = 'base_imu_link'
            message.orientation_covariance[0] = -1.0
            for index, variance in zip((0, 4, 8), self.config['angular_velocity_variances']):
                message.angular_velocity_covariance[index] = variance
            message.linear_acceleration.x, message.linear_acceleration.y, message.linear_acceleration.z = acceleration
            message.angular_velocity.x, message.angular_velocity.y, message.angular_velocity.z = gyro
            self.publisher.publish(message)
            self.last_sample = time.monotonic()
            self.last_event_valid = True
            self.received_samples += 1

    def diagnostic(self, status):
        age = time.monotonic() - self.last_sample
        if self.configuration_error or self.communication_error:
            status.summary(DiagnosticStatus.ERROR, self.configuration_error or self.communication_error)
        elif age > self.config['sample_timeout']:
            status.summary(DiagnosticStatus.ERROR, 'valid sample timeout')
        elif not self.last_event_valid:
            status.summary(DiagnosticStatus.ERROR, self.last_error)
        else:
            status.summary(DiagnosticStatus.OK, 'valid bridge samples; calibration not verified')
        status.add('port', self.config['port'])
        status.add('protocol_profile', self.config['protocol_profile'])
        status.add('valid_samples', str(self.received_samples))
        status.add('invalid_packets', str(self.invalid_packets))
        status.add('last_valid_sample_age_s', str(age))
        status.add('timestamp_source', 'host receipt; acquisition time unavailable')
        status.add('angular_velocity_covariance',
                   'invalid configuration' if 'angular_velocity_variances' in self.configuration_error else
                   'supplied diagonal SI variances; calibration not verified'
                   if any(self.config['angular_velocity_variances']) else 'unknown (ROS zeros)')
        status.add('covariance', 'acceleration unknown (ROS zeros); orientation unavailable')
        return status

    def destroy_node(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UsbImu()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
