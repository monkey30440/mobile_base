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

"""ROS node for the five-metric observability adapter MVP."""

import math
import os

from diagnostic_msgs.msg import DiagnosticArray
from mobile_base_observability.influx import InfluxConfig
from mobile_base_observability.influx import InfluxHttpWriter
from mobile_base_observability.influx import TelemetrySender
from mobile_base_observability.telemetry import BoundedTelemetryQueue
from mobile_base_observability.telemetry import extract_filtered_odometry_metrics
from mobile_base_observability.telemetry import extract_selected_diagnostic_level
from mobile_base_observability.telemetry import extract_wheel_velocity_metrics
from mobile_base_observability.telemetry import LatestMetricSampler
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState


_DEFAULT_DIAGNOSTIC_STATUS_NAME = (
    'controller_manager: Hardware Components Activity'
)


class ObservabilityAdapterNode(Node):
    """Sample the MVP telemetry profile without blocking ROS callbacks."""

    def __init__(self, parameter_overrides=None) -> None:
        super().__init__(
            'ros_observability_adapter',
            parameter_overrides=parameter_overrides,
        )
        self.declare_parameter(
            'influxdb_url', os.getenv('MOBILE_BASE_INFLUXDB_URL', '')
        )
        self.declare_parameter(
            'influxdb_organization',
            os.getenv('MOBILE_BASE_INFLUXDB_ORGANIZATION', ''),
        )
        self.declare_parameter(
            'influxdb_bucket', os.getenv('MOBILE_BASE_INFLUXDB_BUCKET', '')
        )
        self.declare_parameter('robot_id', os.getenv('MOBILE_BASE_ROBOT_ID', ''))
        self.declare_parameter('sample_rate_hz', 1.0)
        self.declare_parameter('queue_capacity', 60)
        self.declare_parameter('http_timeout_seconds', 2.0)
        self.declare_parameter(
            'diagnostic_status_name',
            os.getenv(
                'MOBILE_BASE_DIAGNOSTIC_STATUS_NAME',
                _DEFAULT_DIAGNOSTIC_STATUS_NAME,
            ),
        )

        sample_rate_hz = self.get_parameter('sample_rate_hz').value
        queue_capacity = self.get_parameter('queue_capacity').value
        timeout_seconds = self.get_parameter('http_timeout_seconds').value
        if not math.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
            raise ValueError('sample_rate_hz must be greater than zero')
        if (
            not isinstance(queue_capacity, int)
            or isinstance(queue_capacity, bool)
            or queue_capacity <= 0
        ):
            raise ValueError('queue_capacity must be a positive integer')
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError('http_timeout_seconds must be greater than zero')

        config = InfluxConfig(
            url=self.get_parameter('influxdb_url').value,
            organization=self.get_parameter('influxdb_organization').value,
            bucket=self.get_parameter('influxdb_bucket').value,
            token=os.getenv('MOBILE_BASE_INFLUXDB_TOKEN', ''),
            robot_id=self.get_parameter('robot_id').value,
            timeout_seconds=timeout_seconds,
        )
        self._queue = BoundedTelemetryQueue(queue_capacity)
        self._sampler = LatestMetricSampler(self._queue, config.robot_id)
        self._sender = None
        self._warned_zero_timestamp_sources = set()
        self._diagnostic_status_name = self.get_parameter(
            'diagnostic_status_name'
        ).value

        if config.is_complete:
            writer = InfluxHttpWriter(config)
            self._sender = TelemetrySender(
                self._queue,
                writer.write,
                self._report_sender_error,
            )
            self._sender.start()
        else:
            self.get_logger().error(
                'InfluxDB sender disabled; invalid client configuration: '
                + ', '.join(config.configuration_errors())
            )

        self._odometry_subscription = self.create_subscription(
            Odometry,
            '/odometry/filtered',
            self.handle_odometry,
            qos_profile_sensor_data,
        )
        self._joint_states_subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.handle_joint_states,
            qos_profile_sensor_data,
        )
        self._diagnostics_subscription = self.create_subscription(
            DiagnosticArray,
            '/diagnostics',
            self.handle_diagnostics,
            10,
        )
        self._sample_timer = self.create_timer(
            1.0 / sample_rate_hz,
            self.sample_latest,
        )
        self.get_logger().info(
            'Observing the five-metric telemetry profile '
            f'at {sample_rate_hz:g} Hz'
        )

    @property
    def sender_enabled(self) -> bool:
        """Report whether complete configuration enabled the sender."""
        return self._sender is not None

    @property
    def queued_record_count(self) -> int:
        """Return current volatile queue occupancy."""
        return len(self._queue)

    def handle_odometry(self, message: Odometry) -> None:
        """Update only the latest observed value; never perform network I/O."""
        observations = extract_filtered_odometry_metrics(message)
        if not observations:
            self._warn_zero_timestamp_once('/odometry/filtered')
        for observation in observations:
            self._sampler.update(observation)

    def handle_joint_states(self, message: JointState) -> None:
        """Update available wheel metrics by joint name without network I/O."""
        observations = extract_wheel_velocity_metrics(message)
        if not observations and self._timestamp_is_zero(message):
            self._warn_zero_timestamp_once('/joint_states')
        for observation in observations:
            self._sampler.update(observation)

    def handle_diagnostics(self, message: DiagnosticArray) -> None:
        """Update the configured exact diagnostic status without network I/O."""
        observation = extract_selected_diagnostic_level(
            message, self._diagnostic_status_name
        )
        if observation is not None:
            self._sampler.update(observation)
        elif self._diagnostic_status_name and self._timestamp_is_zero(message):
            self._warn_zero_timestamp_once('/diagnostics')

    def sample_latest(self) -> None:
        """Add one latest-value record per available metric per timer tick."""
        self._sampler.sample()

    @staticmethod
    def _timestamp_is_zero(message) -> bool:
        stamp = message.header.stamp
        return int(stamp.sec) == 0 and int(stamp.nanosec) == 0

    def _warn_zero_timestamp_once(self, source: str) -> None:
        if source in self._warned_zero_timestamp_sources:
            return
        self._warned_zero_timestamp_sources.add(source)
        self.get_logger().warning(
            f'Discarding {source} data with zero header timestamp'
        )

    def _report_sender_error(self, message: str) -> None:
        self.get_logger().error(f'InfluxDB write failed; record discarded: {message}')

    def destroy_node(self) -> None:
        """Stop the sender within the configured HTTP time boundary."""
        if self._sender is not None:
            timeout_seconds = self.get_parameter('http_timeout_seconds').value + 0.5
            self._sender.stop(timeout_seconds=timeout_seconds)
            self._sender = None
        super().destroy_node()


def main(args=None) -> None:
    """Run the standalone observability adapter node."""
    rclpy.init(args=args)
    node = None
    try:
        node = ObservabilityAdapterNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
