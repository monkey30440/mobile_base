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

"""Regression tests for upside-down picoScan LaserScan handedness."""

import importlib.util
from pathlib import Path

from diagnostic_msgs.msg import DiagnosticStatus
import pytest
from sensor_msgs.msg import LaserScan


def _load_normalizer_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / 'scripts'
        / 'scan_handedness_normalizer.py'
    )
    spec = importlib.util.spec_from_file_location(
        'scan_handedness_normalizer', script_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_scan_reflects_angles_and_preserves_z_up_frame():
    """Catch publishing inverted ranges under an already-corrected z-up frame."""
    module = _load_normalizer_module()
    scan = LaserScan()
    scan.header.frame_id = 'base_lidar_link_FL_1'
    scan.angle_min = -2.0
    scan.angle_max = 1.0
    scan.angle_increment = 1.0
    scan.ranges = [10.0, 20.0, 30.0, 40.0]
    scan.intensities = [1.0, 2.0, 3.0, 4.0]

    normalized = module.normalize_scan(scan)

    assert normalized.header.frame_id == 'base_lidar_link_FL_1'
    assert normalized.angle_min == pytest.approx(-1.0)
    assert normalized.angle_max == pytest.approx(2.0)
    assert normalized.angle_increment == pytest.approx(1.0)
    assert list(normalized.ranges) == [40.0, 30.0, 20.0, 10.0]
    assert list(normalized.intensities) == [4.0, 3.0, 2.0, 1.0]


def test_normalize_scan_keeps_empty_intensities_empty():
    """Catch fabricating intensity samples when the driver publishes none."""
    module = _load_normalizer_module()
    scan = LaserScan()
    scan.angle_min = -1.0
    scan.angle_max = 1.0
    scan.angle_increment = 1.0
    scan.ranges = [1.0, 2.0, 3.0]

    normalized = module.normalize_scan(scan)

    assert list(normalized.ranges) == [3.0, 2.0, 1.0]
    assert list(normalized.intensities) == []


@pytest.mark.parametrize(
    ('last_scan_receive_time', 'now', 'expected_message'),
    [
        (None, 10.0, 'Waiting for scan data'),
        (9.799, 10.0, 'Scan data stale'),
    ],
)
def test_scan_diagnostic_is_stale_without_fresh_scan(
    last_scan_receive_time, now, expected_message
):
    """Report unavailable scan information as STALE, never hardware ERROR."""
    module = _load_normalizer_module()

    status = module.make_scan_diagnostic_status(
        'Front LiDAR', 'front_lidar', last_scan_receive_time, now
    )

    assert status.level == DiagnosticStatus.STALE
    assert status.message == expected_message
    assert [(value.key, value.value) for value in status.values] == [
        ('scan', 'STALE')
    ]


@pytest.mark.parametrize('age_seconds', [0.0, 0.199, 0.200])
def test_scan_diagnostic_is_ok_through_200_ms_boundary(age_seconds):
    """Keep a scan fresh through the inclusive 200 ms boundary."""
    module = _load_normalizer_module()

    status = module.make_scan_diagnostic_status(
        'Front LiDAR', 'front_lidar', 10.0 - age_seconds, 10.0
    )

    assert status.level == DiagnosticStatus.OK
    assert status.message == 'Scan data normal'
    assert [(value.key, value.value) for value in status.values] == [
        ('scan', 'OK')
    ]


@pytest.mark.parametrize(
    ('diagnostic_name', 'hardware_id'),
    [
        ('Front LiDAR', 'front_lidar'),
        ('Rear LiDAR', 'rear_lidar'),
    ],
)
def test_scan_diagnostic_preserves_exact_lidar_identity(
    diagnostic_name, hardware_id
):
    """Publish the external diagnostic contract without node-name prefixes."""
    module = _load_normalizer_module()

    status = module.make_scan_diagnostic_status(
        diagnostic_name, hardware_id, 9.9, 10.0
    )

    assert status.name == diagnostic_name
    assert status.hardware_id == hardware_id
    assert status.level not in (DiagnosticStatus.WARN, DiagnosticStatus.ERROR)
    assert [value.key for value in status.values] == ['scan']


def test_main_handles_sigint_after_rclpy_context_shutdown(monkeypatch):
    """Exit cleanly when the ROS signal handler already shut down context."""
    module = _load_normalizer_module()
    calls = []

    class FakeNode:

        def destroy_node(self):
            calls.append('destroy_node')

    monkeypatch.setattr(module.rclpy, 'init', lambda args=None: calls.append('init'))
    monkeypatch.setattr(module, 'ScanHandednessNormalizer', FakeNode)

    def interrupt_spin(node):
        calls.append('spin')
        raise KeyboardInterrupt

    monkeypatch.setattr(module.rclpy, 'spin', interrupt_spin)
    monkeypatch.setattr(module.rclpy, 'ok', lambda: False)
    monkeypatch.setattr(
        module.rclpy, 'shutdown', lambda: calls.append('shutdown')
    )

    module.main()

    assert calls == ['init', 'spin', 'destroy_node']
