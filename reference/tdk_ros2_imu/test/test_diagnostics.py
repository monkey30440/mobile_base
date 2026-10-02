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

"""Tests for the TDK IMU REP-107 diagnostic contract."""

from diagnostic_msgs.msg import DiagnosticStatus
import pytest

from tdk_ros2_imu import tdk_imu_node


def _status(communication, last_valid_packet_time, now=10.0, checksum_errors=0):
    return tdk_imu_node.make_imu_diagnostic_status(
        communication=communication,
        last_valid_packet_time=last_valid_packet_time,
        checksum_error_count=checksum_errors,
        now=now,
    )


@pytest.mark.parametrize('communication', ['UNKNOWN', 'OK'])
def test_no_valid_packet_is_stale(communication):
    """Catch startup states being reported as healthy or failed."""
    assert _status(communication, None).level == DiagnosticStatus.STALE


@pytest.mark.parametrize(
    ('last_valid_packet_time', 'now', 'expected_level'),
    [
        (0.0, 0.099, DiagnosticStatus.OK),
        (0.0, 0.100, DiagnosticStatus.OK),
        (0.0, 0.101, DiagnosticStatus.STALE),
    ],
)
def test_valid_packet_freshness_uses_inclusive_100_ms_boundary(
        last_valid_packet_time, now, expected_level):
    """Catch an incorrect freshness threshold or exclusive boundary."""
    status = _status('OK', last_valid_packet_time, now=now)

    assert status.level == expected_level


@pytest.mark.parametrize(
    'communication', ['SERIAL_OPEN_FAILED', 'SERIAL_EXCEPTION']
)
def test_known_serial_failure_is_error_even_without_fresh_data(communication):
    """Catch serial failures being hidden by the stale-data branch."""
    assert _status(communication, None).level == DiagnosticStatus.ERROR


def test_diagnostic_identity_and_public_values_are_exact():
    """Catch identity drift or accidental expansion of public values."""
    status = _status('OK', 10.0, checksum_errors=3)

    assert status.name == 'IMU'
    assert status.hardware_id == 'tdk_imu'
    assert status.message == 'Operating normally'
    assert [(value.key, value.value) for value in status.values] == [
        ('communication', 'OK'),
        ('checksum_error_count', '3'),
    ]


@pytest.mark.parametrize(
    ('communication', 'last_valid_packet_time'),
    [
        ('UNKNOWN', None),
        ('OK', None),
        ('OK', 9.899),
        ('SERIAL_OPEN_FAILED', None),
        ('SERIAL_EXCEPTION', 10.0),
    ],
)
def test_mvp_has_no_warn_trigger(communication, last_valid_packet_time):
    """Catch unsupported checksum, startup, or failure WARN states."""
    status = _status(communication, last_valid_packet_time)

    assert status.level != DiagnosticStatus.WARN
