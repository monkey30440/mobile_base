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

"""Unit and orientation conversions for ROS Imu messages."""

import math


STANDARD_GRAVITY = 9.80665


def acceleration_to_si(
    acceleration_g: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Convert acceleration from standard gravity to metres per second squared."""
    return tuple(value * STANDARD_GRAVITY for value in acceleration_g)


def angular_velocity_to_si(
    angular_velocity_dps: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Convert angular velocity from degrees per second to radians per second."""
    return tuple(math.radians(value) for value in angular_velocity_dps)


def quaternion_from_euler_degrees(
    rpy_degrees: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    """Convert roll, pitch, yaw in degrees to an x-y-z-w quaternion."""
    roll, pitch, yaw = (math.radians(value) for value in rpy_degrees)

    sin_roll = math.sin(roll / 2.0)
    cos_roll = math.cos(roll / 2.0)
    sin_pitch = math.sin(pitch / 2.0)
    cos_pitch = math.cos(pitch / 2.0)
    sin_yaw = math.sin(yaw / 2.0)
    cos_yaw = math.cos(yaw / 2.0)

    return (
        sin_roll * cos_pitch * cos_yaw - cos_roll * sin_pitch * sin_yaw,
        cos_roll * sin_pitch * cos_yaw + sin_roll * cos_pitch * sin_yaw,
        cos_roll * cos_pitch * sin_yaw - sin_roll * sin_pitch * cos_yaw,
        cos_roll * cos_pitch * cos_yaw + sin_roll * sin_pitch * sin_yaw,
    )
