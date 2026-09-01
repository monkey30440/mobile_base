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

"""Tests for the ROS observability adapter assembly."""

import math
import os
import subprocess

from diagnostic_msgs.msg import DiagnosticArray
from diagnostic_msgs.msg import DiagnosticStatus
from mobile_base_observability.observability_adapter_node import (
    ObservabilityAdapterNode,
)
from nav_msgs.msg import Odometry
import pytest
import rclpy
from rclpy.exceptions import InvalidParameterTypeException
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState


@pytest.fixture(autouse=True)
def rclpy_context():
    """Initialize and teardown rclpy for each test."""
    rclpy.init()
    yield
    if rclpy.ok():
        rclpy.shutdown()


def test_missing_server_configuration_keeps_node_alive_with_sender_disabled():
    """Missing external configuration must not terminate the ROS process."""
    node = ObservabilityAdapterNode(parameter_overrides=[
        Parameter('influxdb_url', value=''),
        Parameter('influxdb_token', value=''),
        Parameter('robot_id', value='test_amr'),
    ])
    try:
        assert node.sender_enabled is False
        assert node.get_name() == 'ros_observability_adapter'
        assert node.has_parameter('influxdb_token') is False
    finally:
        node.destroy_node()


def test_odometry_callback_only_updates_latest_until_sampling_occurs():
    """Moving enqueue into the subscription callback must break this test."""
    node = ObservabilityAdapterNode(parameter_overrides=[
        Parameter('influxdb_url', value=''),
        Parameter('influxdb_token', value=''),
        Parameter('robot_id', value='test_amr'),
        Parameter('queue_capacity', value=3),
    ])
    message = Odometry()
    message.header.stamp.sec = 123
    message.twist.twist.linear.x = 1.23
    message.twist.twist.angular.z = 0.45

    try:
        node.handle_odometry(message)
        assert node.queued_record_count == 0

        node.sample_latest()
        assert node.queued_record_count == 2
    finally:
        node.destroy_node()


def test_zero_timestamp_odometry_is_not_enqueued():
    """Zero source timestamps must be discarded before sampling."""
    node = ObservabilityAdapterNode(parameter_overrides=[
        Parameter('robot_id', value='test_amr'),
        Parameter('queue_capacity', value=3),
    ])
    message = Odometry()
    message.twist.twist.linear.x = 1.23

    try:
        node.handle_odometry(message)
        node.sample_latest()
        assert node.queued_record_count == 0
    finally:
        node.destroy_node()


def test_malformed_timestamp_never_reaches_queue_or_influx_sender():
    """A noncanonical source timestamp must not update or enqueue data."""
    node = ObservabilityAdapterNode(parameter_overrides=[
        Parameter('robot_id', value='test_amr'),
        Parameter('queue_capacity', value=3),
    ])
    message = Odometry()
    message.header.stamp.sec = 1
    message.header.stamp.nanosec = 1_500_000_000
    message.twist.twist.linear.x = 1.23

    try:
        node.handle_odometry(message)
        assert node.queued_record_count == 0

        node.sample_latest()
        assert node.queued_record_count == 0
    finally:
        node.destroy_node()


def test_all_topic_callbacks_only_update_latest_until_sampling_occurs():
    node = ObservabilityAdapterNode(parameter_overrides=[
        Parameter('robot_id', value='test_amr'),
        Parameter('queue_capacity', value=5),
        Parameter('diagnostic_status_name', value='synthetic status'),
    ])
    odometry = Odometry()
    odometry.header.stamp.sec = 123
    joint_state = JointState()
    joint_state.header.stamp.sec = 123
    joint_state.name = ['driving_wheel_joint_R', 'driving_wheel_joint_L']
    joint_state.velocity = [2.0, 1.0]
    diagnostics = DiagnosticArray()
    diagnostics.header.stamp.sec = 123
    diagnostics.status = [DiagnosticStatus(name='synthetic status', level=2)]

    try:
        node.handle_odometry(odometry)
        node.handle_joint_states(joint_state)
        node.handle_diagnostics(diagnostics)
        assert node.queued_record_count == 0

        node.sample_latest()
        assert node.queued_record_count == 5
    finally:
        node.destroy_node()


def test_diagnostic_selection_has_evidence_based_default_and_can_be_disabled():
    default_node = ObservabilityAdapterNode(parameter_overrides=[
        Parameter('robot_id', value='test_amr'),
    ])
    disabled_node = ObservabilityAdapterNode(parameter_overrides=[
        Parameter('robot_id', value='test_amr'),
        Parameter('diagnostic_status_name', value=''),
    ])
    try:
        assert default_node.get_parameter('diagnostic_status_name').value == (
            'controller_manager: Hardware Components Activity'
        )

        diagnostics = DiagnosticArray()
        diagnostics.header.stamp.sec = 123
        diagnostics.status = [DiagnosticStatus(
            name='controller_manager: Hardware Components Activity', level=2
        )]
        disabled_node.handle_diagnostics(diagnostics)
        disabled_node.sample_latest()
        assert disabled_node.queued_record_count == 0
    finally:
        default_node.destroy_node()
        disabled_node.destroy_node()


def test_environment_token_enables_sender_without_ros_parameter(monkeypatch, capfd):
    """The secret must enter only through the process environment."""
    token = 'environment-secret-token'
    monkeypatch.setenv('MOBILE_BASE_INFLUXDB_TOKEN', token)
    node = ObservabilityAdapterNode(parameter_overrides=[
        Parameter('influxdb_url', value='http://127.0.0.1:1'),
        Parameter('influxdb_organization', value='mobile_base'),
        Parameter('influxdb_bucket', value='observability'),
        Parameter('robot_id', value='test_amr'),
    ])
    try:
        assert node.sender_enabled is True
        assert node.has_parameter('influxdb_token') is False
    finally:
        node.destroy_node()

    captured = capfd.readouterr()
    assert token not in captured.out
    assert token not in captured.err


def test_standalone_launch_has_no_token_argument():
    """The launch interface must not materialize the token as an argument."""
    environment = os.environ.copy()
    environment['MOBILE_BASE_INFLUXDB_TOKEN'] = 'launch-secret-token'
    result = subprocess.run(
        [
            'ros2', 'launch', 'mobile_base_observability',
            'observability_adapter.launch.py', '--show-args',
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert 'influxdb_token' not in result.stdout
    assert environment['MOBILE_BASE_INFLUXDB_TOKEN'] not in result.stdout


@pytest.mark.parametrize(
    ('name', 'value'),
    [
        ('sample_rate_hz', 0.0),
        ('sample_rate_hz', -1.0),
        ('sample_rate_hz', math.nan),
        ('sample_rate_hz', math.inf),
        ('sample_rate_hz', -math.inf),
        ('http_timeout_seconds', 0.0),
        ('http_timeout_seconds', -1.0),
        ('http_timeout_seconds', math.nan),
        ('http_timeout_seconds', math.inf),
        ('http_timeout_seconds', -math.inf),
        ('queue_capacity', 0),
        ('queue_capacity', -1),
        ('queue_capacity', math.nan),
        ('queue_capacity', math.inf),
        ('queue_capacity', -math.inf),
    ],
)
def test_invalid_numeric_parameter_is_rejected(name, value):
    """Non-positive and non-finite resource parameters must be rejected."""
    with pytest.raises((ValueError, InvalidParameterTypeException)):
        ObservabilityAdapterNode(parameter_overrides=[Parameter(name, value=value)])
