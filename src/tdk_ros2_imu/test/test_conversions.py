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

import math

import pytest

from tdk_ros2_imu.conversions import acceleration_to_si
from tdk_ros2_imu.conversions import angular_velocity_to_si
from tdk_ros2_imu.conversions import quaternion_from_euler_degrees


def test_acceleration_to_si_uses_standard_gravity():
    assert acceleration_to_si((1.0, -0.5, 0.0)) == pytest.approx(
        (9.80665, -4.903325, 0.0)
    )


def test_angular_velocity_to_si_converts_degrees_to_radians():
    assert angular_velocity_to_si((180.0, -90.0, 0.0)) == pytest.approx(
        (math.pi, -math.pi / 2.0, 0.0)
    )


def test_zero_euler_angles_produce_identity_quaternion():
    assert quaternion_from_euler_degrees((0.0, 0.0, 0.0)) == pytest.approx(
        (0.0, 0.0, 0.0, 1.0)
    )


def test_quaternion_is_normalized():
    quaternion = quaternion_from_euler_degrees((30.0, -20.0, 120.0))
    norm = math.sqrt(sum(component * component for component in quaternion))

    assert norm == pytest.approx(1.0)
