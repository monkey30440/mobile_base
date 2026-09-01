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

"""MVP metric extraction, sampling, and bounded volatile buffering."""

from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Generic, Optional, TypeVar


_NANOSECONDS_PER_SECOND = 1_000_000_000
LEFT_WHEEL_JOINT = 'driving_wheel_joint_L'
RIGHT_WHEEL_JOINT = 'driving_wheel_joint_R'


@dataclass(frozen=True)
class MetricObservation:
    """Latest value observed from the selected ROS source."""

    timestamp_ns: int
    timestamp_origin: str
    source: str
    metric: str
    value: float


@dataclass(frozen=True)
class TelemetryRecord:
    """Sample ready for the external time-series write path."""

    timestamp_ns: int
    timestamp_origin: str
    robot_id: str
    source: str
    metric: str
    value: float


def _header_timestamp_ns(message):
    stamp = message.header.stamp
    header_timestamp_ns = (
        int(stamp.sec) * _NANOSECONDS_PER_SECOND + int(stamp.nanosec)
    )
    if header_timestamp_ns <= 0:
        return None
    return header_timestamp_ns


def extract_filtered_odometry_metrics(message):
    """Extract the two approved Odometry metrics with a valid source time."""
    timestamp_ns = _header_timestamp_ns(message)
    if timestamp_ns is None:
        return ()

    values = (
        ('filtered_linear_velocity_x', message.twist.twist.linear.x),
        ('filtered_angular_velocity_z', message.twist.twist.angular.z),
    )
    return tuple(
        MetricObservation(
            timestamp_ns=timestamp_ns,
            timestamp_origin='header',
            source='/odometry/filtered',
            metric=metric,
            value=float(value),
        )
        for metric, value in values
    )


def extract_wheel_velocity_metrics(message):
    """Extract available wheel velocities by exact joint name, not position."""
    timestamp_ns = _header_timestamp_ns(message)
    if timestamp_ns is None:
        return ()

    indexes = {}
    for index, name in enumerate(message.name):
        indexes.setdefault(name, index)

    observations = []
    for joint_name, metric in (
        (LEFT_WHEEL_JOINT, 'left_wheel_velocity'),
        (RIGHT_WHEEL_JOINT, 'right_wheel_velocity'),
    ):
        index = indexes.get(joint_name)
        if index is None or index >= len(message.velocity):
            continue
        observations.append(MetricObservation(
            timestamp_ns=timestamp_ns,
            timestamp_origin='header',
            source='/joint_states',
            metric=metric,
            value=float(message.velocity[index]),
        ))
    return tuple(observations)


def extract_selected_diagnostic_level(message, selected_name):
    """Extract one exact DiagnosticStatus level with a valid array time."""
    if not selected_name:
        return None
    timestamp_ns = _header_timestamp_ns(message)
    if timestamp_ns is None:
        return None

    for status in message.status:
        if status.name != selected_name:
            continue
        level = status.level
        if isinstance(level, bytes):
            level = int.from_bytes(level, byteorder='little')
        return MetricObservation(
            timestamp_ns=timestamp_ns,
            timestamp_origin='header',
            source='/diagnostics',
            metric='selected_diagnostic_level',
            value=float(level),
        )
    return None


Item = TypeVar('Item')


class BoundedTelemetryQueue(Generic[Item]):
    """Thread-safe volatile FIFO whose full behavior is drop-oldest."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError('capacity must be greater than zero')
        self._items = deque(maxlen=capacity)
        self._lock = Lock()

    def append(self, item: Item) -> None:
        """Append newest data; deque discards the oldest item when full."""
        with self._lock:
            self._items.append(item)

    def popleft(self) -> Optional[Item]:
        """Return and remove the oldest item, or None when empty."""
        with self._lock:
            if not self._items:
                return None
            return self._items.popleft()

    def snapshot(self):
        """Return a stable list for diagnostics and tests."""
        with self._lock:
            return list(self._items)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


class LatestMetricSampler:
    """Separate high-rate observation updates from low-rate queue sampling."""

    def __init__(
        self,
        queue: BoundedTelemetryQueue[TelemetryRecord],
        robot_id: str,
    ) -> None:
        self._queue = queue
        self._robot_id = robot_id
        self._latest = {}
        self._lock = Lock()

    def update(self, observation: MetricObservation) -> None:
        """Replace the latest observation without enqueueing or doing I/O."""
        with self._lock:
            self._latest[observation.metric] = observation

    def sample(self):
        """Enqueue one record for every latest metric observation."""
        with self._lock:
            observations = tuple(self._latest.values())

        records = []
        for observation in observations:
            record = TelemetryRecord(
                timestamp_ns=observation.timestamp_ns,
                timestamp_origin=observation.timestamp_origin,
                robot_id=self._robot_id,
                source=observation.source,
                metric=observation.metric,
                value=observation.value,
            )
            self._queue.append(record)
            records.append(record)
        return records
