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

"""Contract tests for deployment environment variable names and defaults."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPOSITORY_ROOT / '.env.example'


def _environment_template():
    entries = {}
    for line in ENV_EXAMPLE.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            name, value = line.split('=', maxsplit=1)
            entries[name] = value
    return entries


def test_required_influxdb_environment_variables_are_empty():
    """Required InfluxDB client settings must exist without repo defaults."""
    entries = _environment_template()

    for name in (
        'MOBILE_BASE_INFLUXDB_URL',
        'MOBILE_BASE_INFLUXDB_ORGANIZATION',
        'MOBILE_BASE_INFLUXDB_BUCKET',
        'MOBILE_BASE_INFLUXDB_TOKEN',
    ):
        assert name in entries
        assert entries[name] == ''


def test_observability_environment_template_has_no_deployment_defaults():
    """No onboard client identity, endpoint, or credential may be defaulted."""
    entries = _environment_template()

    assert all(
        value == ''
        for name, value in entries.items()
        if name.startswith('MOBILE_BASE_')
    )
