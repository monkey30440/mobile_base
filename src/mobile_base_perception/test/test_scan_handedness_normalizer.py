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
