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

"""Tests for the isolated InfluxDB write boundary."""

from threading import Event
import time

from mobile_base_observability.influx import InfluxConfig
from mobile_base_observability.influx import line_protocol
from mobile_base_observability.influx import TelemetrySender
from mobile_base_observability.telemetry import BoundedTelemetryQueue
from mobile_base_observability.telemetry import TelemetryRecord
import pytest


def _record(value=1.23):
    return TelemetryRecord(
        timestamp_ns=123_000_000_456,
        timestamp_origin='header',
        robot_id='test_amr',
        source='/odometry/filtered',
        metric='filtered_linear_velocity_x',
        value=value,
    )


def test_line_protocol_maps_single_metric_record():
    """Changing the MVP Influx mapping must break this test."""
    assert line_protocol(_record()) == (
        'filtered_linear_velocity_x,'
        'robot_id=test_amr,'
        'source=/odometry/filtered,'
        'timestamp_origin=header '
        'value=1.23 123000000456'
    )


def test_sender_failure_is_contained_and_does_not_grow_queue():
    """Allowing HTTP failure to escape or queue growth must break this test."""
    queue = BoundedTelemetryQueue(capacity=3)
    for value in (1.0, 2.0, 3.0, 4.0):
        queue.append(_record(value))

    errors = []

    def failing_write(_record):
        raise OSError('server unavailable')

    sender = TelemetrySender(queue, failing_write, errors.append)

    assert sender.send_once() is False
    assert [item.value for item in queue.snapshot()] == [3.0, 4.0]
    assert len(errors) == 1


def test_incomplete_server_configuration_is_explicitly_disabled():
    """Starting a sender with missing credentials must break this test."""
    config = InfluxConfig(
        url='',
        organization='mobile_base',
        bucket='observability',
        token='',
        robot_id='test_amr',
    )

    assert config.missing_fields() == ('url', 'token')
    assert config.is_complete is False


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('robot_id', 'robot\nother'),
        ('source', '/odometry/filtered\rmalformed'),
        ('metric', 'filtered\nvelocity'),
        ('timestamp_origin', 'header\rorigin'),
    ],
)
def test_line_protocol_rejects_crlf_in_identity_fields(field, value):
    """CR/LF must not produce multiple or malformed Influx lines."""
    values = _record().__dict__.copy()
    values[field] = value

    with pytest.raises(ValueError, match='must not contain CR or LF'):
        line_protocol(TelemetryRecord(**values))


def test_blocked_sender_shutdown_is_bounded_and_suppresses_late_error_callback():
    """A blocked HTTP operation must not access ROS callbacks after stop."""
    queue = BoundedTelemetryQueue(capacity=1)
    queue.append(_record())
    write_started = Event()
    release_write = Event()
    errors = []

    def blocked_write(_record):
        write_started.set()
        release_write.wait(timeout=1.0)
        raise OSError('late failure')

    sender = TelemetrySender(queue, blocked_write, errors.append)
    sender.start()
    assert write_started.wait(timeout=0.5)

    started = time.monotonic()
    sender.stop(timeout_seconds=0.02)
    elapsed = time.monotonic() - started
    release_write.set()
    sender.stop(timeout_seconds=0.5)

    assert elapsed < 0.2
    assert errors == []
