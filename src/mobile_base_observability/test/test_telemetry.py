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

"""Tests for the five-metric telemetry profile."""

from types import SimpleNamespace

from mobile_base_observability.telemetry import BoundedTelemetryQueue
from mobile_base_observability.telemetry import extract_filtered_odometry_metrics
from mobile_base_observability.telemetry import extract_selected_diagnostic_level
from mobile_base_observability.telemetry import extract_wheel_velocity_metrics
from mobile_base_observability.telemetry import LatestMetricSampler
from mobile_base_observability.telemetry import MetricObservation
import pytest


def _stamp(sec=123, nanosec=456):
    return SimpleNamespace(sec=sec, nanosec=nanosec)


def _odometry(linear_x, angular_z, sec=123, nanosec=456):
    return SimpleNamespace(
        header=SimpleNamespace(stamp=_stamp(sec, nanosec)),
        twist=SimpleNamespace(twist=SimpleNamespace(
            linear=SimpleNamespace(x=linear_x),
            angular=SimpleNamespace(z=angular_z),
        )),
    )


def _joint_state(names, velocities, sec=123, nanosec=456):
    return SimpleNamespace(
        header=SimpleNamespace(stamp=_stamp(sec, nanosec)),
        name=names,
        velocity=velocities,
    )


def _diagnostics(statuses, sec=123, nanosec=456):
    return SimpleNamespace(
        header=SimpleNamespace(stamp=_stamp(sec, nanosec)),
        status=[SimpleNamespace(name=name, level=level) for name, level in statuses],
    )


def _observation(metric, value):
    return MetricObservation(
        timestamp_ns=123_000_000_456,
        timestamp_origin='header',
        source='/test',
        metric=metric,
        value=value,
    )


def test_extracts_two_filtered_odometry_metrics():
    observations = extract_filtered_odometry_metrics(_odometry(1.23, -0.45))

    assert [(item.metric, item.value) for item in observations] == [
        ('filtered_linear_velocity_x', pytest.approx(1.23)),
        ('filtered_angular_velocity_z', pytest.approx(-0.45)),
    ]
    assert all(item.source == '/odometry/filtered' for item in observations)
    assert all(item.timestamp_ns == 123_000_000_456 for item in observations)
    assert all(item.timestamp_origin == 'header' for item in observations)


def test_zero_odometry_header_timestamp_produces_no_observations():
    assert extract_filtered_odometry_metrics(
        _odometry(1.23, -0.45, sec=0, nanosec=0)
    ) == ()


@pytest.mark.parametrize(
    ('sec', 'nanosec'),
    [
        (1, 0),
        (0, 1),
        (1, 999_999_999),
    ],
)
def test_canonical_positive_header_timestamps_are_accepted(sec, nanosec):
    observations = extract_filtered_odometry_metrics(
        _odometry(1.23, -0.45, sec=sec, nanosec=nanosec)
    )

    assert len(observations) == 2
    assert all(
        item.timestamp_ns == sec * 1_000_000_000 + nanosec
        for item in observations
    )


@pytest.mark.parametrize('nanosec', [1_000_000_000, 1_500_000_000])
def test_noncanonical_nanoseconds_are_rejected_without_normalization(nanosec):
    assert extract_filtered_odometry_metrics(
        _odometry(1.23, -0.45, sec=1, nanosec=nanosec)
    ) == ()

    assert extract_wheel_velocity_metrics(_joint_state(
        ['driving_wheel_joint_L', 'driving_wheel_joint_R'], [1.0, 2.0],
        sec=1, nanosec=nanosec,
    )) == ()

    assert extract_selected_diagnostic_level(
        _diagnostics([('selected', 2)], sec=1, nanosec=nanosec),
        'selected',
    ) is None


def test_wheel_velocity_lookup_uses_names_when_order_is_swapped():
    observations = extract_wheel_velocity_metrics(_joint_state(
        ['driving_wheel_joint_R', 'driving_wheel_joint_L'], [2.0, 1.0]
    ))

    assert [(item.metric, item.value) for item in observations] == [
        ('left_wheel_velocity', pytest.approx(1.0)),
        ('right_wheel_velocity', pytest.approx(2.0)),
    ]
    assert all(item.source == '/joint_states' for item in observations)


@pytest.mark.parametrize(
    ('names', 'velocities', 'expected'),
    [
        (['driving_wheel_joint_R'], [2.0], [('right_wheel_velocity', 2.0)]),
        (['driving_wheel_joint_L'], [1.0], [('left_wheel_velocity', 1.0)]),
        (
            ['driving_wheel_joint_L', 'driving_wheel_joint_R'],
            [1.0],
            [('left_wheel_velocity', 1.0)],
        ),
    ],
)
def test_missing_joint_or_velocity_only_skips_affected_metric(
    names, velocities, expected
):
    observations = extract_wheel_velocity_metrics(
        _joint_state(names, velocities)
    )
    assert [(item.metric, item.value) for item in observations] == expected


def test_zero_joint_state_header_timestamp_produces_no_observations():
    assert extract_wheel_velocity_metrics(_joint_state(
        ['driving_wheel_joint_L', 'driving_wheel_joint_R'], [1.0, 2.0],
        sec=0, nanosec=0,
    )) == ()


@pytest.mark.parametrize('level', [0, 1, 2, 3])
def test_exact_selected_diagnostic_level_is_extracted(level):
    observation = extract_selected_diagnostic_level(
        _diagnostics([('other', 0), ('selected', level)]), 'selected'
    )
    assert observation.metric == 'selected_diagnostic_level'
    assert observation.value == pytest.approx(float(level))
    assert observation.source == '/diagnostics'


def test_non_matching_or_unconfigured_diagnostic_is_ignored():
    message = _diagnostics([('other', 2)])
    assert extract_selected_diagnostic_level(message, 'selected') is None
    assert extract_selected_diagnostic_level(message, '') is None


def test_zero_diagnostic_header_timestamp_is_ignored():
    assert extract_selected_diagnostic_level(
        _diagnostics([('selected', 2)], sec=0, nanosec=0), 'selected'
    ) is None


def test_bounded_queue_drops_oldest_when_capacity_is_exhausted():
    queue = BoundedTelemetryQueue(capacity=3)
    for value in (1.0, 2.0, 3.0, 4.0):
        queue.append(_observation('metric', value))
    assert [item.value for item in queue.snapshot()] == [2.0, 3.0, 4.0]


def test_sampling_enqueues_latest_value_per_metric_not_every_update():
    queue = BoundedTelemetryQueue(capacity=5)
    sampler = LatestMetricSampler(queue=queue, robot_id='test_amr')
    for value in range(50):
        sampler.update(_observation('first', float(value)))
        sampler.update(_observation('second', float(value + 100)))
    assert len(queue) == 0

    records = sampler.sample()

    assert [(item.metric, item.value) for item in records] == [
        ('first', 49.0), ('second', 149.0)
    ]
    assert all(item.robot_id == 'test_amr' for item in records)
    assert len(queue) == 2


def test_queue_remains_bounded_when_sampling_multiple_metrics():
    queue = BoundedTelemetryQueue(capacity=3)
    sampler = LatestMetricSampler(queue=queue, robot_id='test_amr')
    for metric in ('one', 'two', 'three', 'four', 'five'):
        sampler.update(_observation(metric, 1.0))
    sampler.sample()
    assert [item.metric for item in queue.snapshot()] == ['three', 'four', 'five']


def test_queue_rejects_non_positive_capacity():
    with pytest.raises(ValueError, match='capacity must be greater than zero'):
        BoundedTelemetryQueue(capacity=0)
