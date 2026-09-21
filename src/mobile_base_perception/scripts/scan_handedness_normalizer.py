#!/usr/bin/env python3

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

"""Normalize LaserScan handedness from an upside-down picoScan."""

from copy import deepcopy
import time

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan


SCAN_STALE_TIMEOUT_SECONDS = 0.200
DIAGNOSTIC_PERIOD_SECONDS = 0.100


def make_scan_diagnostic_status(
    name: str,
    hardware_id: str,
    last_scan_receive_time: float | None,
    now: float,
) -> DiagnosticStatus:
    """Build the REP-107 status for raw scan receive freshness."""
    status = DiagnosticStatus(name=name, hardware_id=hardware_id)
    if last_scan_receive_time is None:
        status.level = DiagnosticStatus.STALE
        status.message = 'Waiting for scan data'
        scan_value = 'STALE'
    elif now - last_scan_receive_time <= SCAN_STALE_TIMEOUT_SECONDS:
        status.level = DiagnosticStatus.OK
        status.message = 'Scan data normal'
        scan_value = 'OK'
    else:
        status.level = DiagnosticStatus.STALE
        status.message = 'Scan data stale'
        scan_value = 'STALE'
    status.values = [KeyValue(key='scan', value=scan_value)]
    return status


def normalize_scan(scan: LaserScan) -> LaserScan:
    """Reflect scan angles while keeping an ascending angular sequence."""
    normalized = deepcopy(scan)
    normalized.angle_min = -scan.angle_max
    normalized.angle_max = -scan.angle_min
    normalized.ranges = list(reversed(scan.ranges))
    if scan.intensities:
        normalized.intensities = list(reversed(scan.intensities))
    return normalized


class ScanHandednessNormalizer(Node):
    """Republish a reflected LaserScan for a z-up corrected scan frame."""

    def __init__(self) -> None:
        super().__init__('scan_handedness_normalizer')
        self.declare_parameter('input_topic', '')
        self.declare_parameter('output_topic', '')
        self.declare_parameter('diagnostic_name', '')
        self.declare_parameter('hardware_id', '')
        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value
        self._diagnostic_name = self.get_parameter('diagnostic_name').value
        self._hardware_id = self.get_parameter('hardware_id').value
        if not all((
            input_topic,
            output_topic,
            self._diagnostic_name,
            self._hardware_id,
        )):
            raise ValueError(
                'input_topic, output_topic, diagnostic_name, and hardware_id '
                'must be non-empty'
            )

        self._last_scan_receive_time = None

        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(LaserScan, output_topic, qos)
        self.subscription = self.create_subscription(
            LaserScan, input_topic, self._scan_callback, qos
        )
        self._diagnostic_publisher = self.create_publisher(
            DiagnosticArray, '/diagnostics', 10
        )
        self._diagnostic_timer = self.create_timer(
            DIAGNOSTIC_PERIOD_SECONDS, self._publish_diagnostic
        )

    def _scan_callback(self, scan: LaserScan) -> None:
        self._last_scan_receive_time = time.monotonic()
        self.publisher.publish(normalize_scan(scan))

    def _publish_diagnostic(self) -> None:
        diagnostic = DiagnosticArray()
        diagnostic.header.stamp = self.get_clock().now().to_msg()
        diagnostic.status = [make_scan_diagnostic_status(
            self._diagnostic_name,
            self._hardware_id,
            self._last_scan_receive_time,
            time.monotonic(),
        )]
        self._diagnostic_publisher.publish(diagnostic)


def main(args=None) -> None:
    """Run the scan handedness normalizer node."""
    rclpy.init(args=args)
    node = ScanHandednessNormalizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
