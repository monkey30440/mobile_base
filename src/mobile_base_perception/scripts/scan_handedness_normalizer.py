#!/usr/bin/env python3

# Copyright 2026 Antigravity Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Normalize LaserScan handedness from an upside-down picoScan."""

from copy import deepcopy

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan


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
        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value
        if not input_topic or not output_topic:
            raise ValueError('input_topic and output_topic must be non-empty')

        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.publisher = self.create_publisher(LaserScan, output_topic, qos)
        self.subscription = self.create_subscription(
            LaserScan, input_topic, self._scan_callback, qos
        )

    def _scan_callback(self, scan: LaserScan) -> None:
        self.publisher.publish(normalize_scan(scan))


def main(args=None) -> None:
    """Run the scan handedness normalizer node."""
    rclpy.init(args=args)
    node = ScanHandednessNormalizer()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
