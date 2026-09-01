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

"""Minimal InfluxDB v2 HTTP write client and isolated sender worker."""

from dataclasses import dataclass
from threading import Event
from threading import Lock
from threading import Thread
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

from mobile_base_observability.telemetry import BoundedTelemetryQueue
from mobile_base_observability.telemetry import TelemetryRecord


def _escape_measurement(value: str) -> str:
    return value.replace('\\', '\\\\').replace(',', '\\,').replace(' ', '\\ ')


def _escape_tag(value: str) -> str:
    return (
        value.replace('\\', '\\\\')
        .replace(',', '\\,')
        .replace('=', '\\=')
        .replace(' ', '\\ ')
    )


def _reject_crlf(name: str, value: str) -> None:
    if '\r' in value or '\n' in value:
        raise ValueError(f'{name} must not contain CR or LF')


def line_protocol(record: TelemetryRecord) -> str:
    """Map one MVP telemetry record to InfluxDB line protocol."""
    identities = {
        'metric': record.metric,
        'robot_id': record.robot_id,
        'source': record.source,
        'timestamp_origin': record.timestamp_origin,
    }
    for name, value in identities.items():
        _reject_crlf(name, value)

    measurement = _escape_measurement(record.metric)
    tags = (
        f'robot_id={_escape_tag(record.robot_id)},'
        f'source={_escape_tag(record.source)},'
        f'timestamp_origin={_escape_tag(record.timestamp_origin)}'
    )
    return (
        f'{measurement},{tags} value={repr(float(record.value))} '
        f'{record.timestamp_ns}'
    )


@dataclass(frozen=True)
class InfluxConfig:
    """External InfluxDB client configuration."""

    url: str
    organization: str
    bucket: str
    token: str
    robot_id: str
    timeout_seconds: float = 2.0

    @property
    def is_complete(self) -> bool:
        """Return whether all required client settings are present."""
        return not self.configuration_errors()

    def missing_fields(self):
        """Return required configuration fields that are empty."""
        values = {
            'url': self.url,
            'organization': self.organization,
            'bucket': self.bucket,
            'token': self.token,
            'robot_id': self.robot_id,
        }
        return tuple(name for name, value in values.items() if not value)

    def configuration_errors(self):
        """Return non-secret descriptions of invalid client settings."""
        errors = list(self.missing_fields())
        if self.robot_id and ('\r' in self.robot_id or '\n' in self.robot_id):
            errors.append('robot_id contains CR/LF')
        return tuple(errors)


class InfluxHttpWriter:
    """Write individual telemetry records through the InfluxDB v2 API."""

    def __init__(self, config: InfluxConfig) -> None:
        if not config.is_complete:
            raise ValueError(
                'incomplete InfluxDB configuration: '
                + ', '.join(config.configuration_errors())
            )
        if config.timeout_seconds <= 0:
            raise ValueError('timeout_seconds must be greater than zero')
        self._config = config

    def write(self, record: TelemetryRecord) -> None:
        """Perform one bounded-time HTTP write request."""
        query = urlencode({
            'org': self._config.organization,
            'bucket': self._config.bucket,
            'precision': 'ns',
        })
        request = Request(
            f'{self._config.url.rstrip("/")}/api/v2/write?{query}',
            data=line_protocol(record).encode('utf-8'),
            headers={
                'Authorization': f'Token {self._config.token}',
                'Content-Type': 'text/plain; charset=utf-8',
            },
            method='POST',
        )
        with urlopen(request, timeout=self._config.timeout_seconds) as response:
            if response.status != 204:
                raise RuntimeError(
                    f'InfluxDB write returned HTTP {response.status}'
                )


class TelemetrySender:
    """Drain a bounded queue on a daemon thread with at-most-once writes."""

    def __init__(
        self,
        queue: BoundedTelemetryQueue[TelemetryRecord],
        write_record: Callable[[TelemetryRecord], None],
        report_error: Callable[[str], None],
        idle_wait_seconds: float = 0.1,
    ) -> None:
        self._queue = queue
        self._write_record = write_record
        self._report_error = report_error
        self._idle_wait_seconds = idle_wait_seconds
        self._stop_event = Event()
        self._report_lock = Lock()
        self._thread = None

    def send_once(self) -> bool:
        """Attempt one record once; contain failures and discard that record."""
        record = self._queue.popleft()
        if record is None:
            return False
        try:
            self._write_record(record)
        except Exception as error:  # External network/library boundary.
            with self._report_lock:
                if not self._stop_event.is_set():
                    self._report_error(str(error))
            return False
        return True

    def start(self) -> None:
        """Start the independent sender thread."""
        if self._thread is not None:
            return
        self._thread = Thread(
            target=self._run,
            name='observability_influx_sender',
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float) -> None:
        """Request sender shutdown and wait only for a bounded interval."""
        self._stop_event.set()
        with self._report_lock:
            pass
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self.send_once():
                self._stop_event.wait(self._idle_wait_seconds)
