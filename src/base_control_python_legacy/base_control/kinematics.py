"""Differential Kinematics — 車體 ↔ 輪端 ↔ 馬達端換算。

負責差速輪運動學、單位換算、方向修正與轉速限制。

不負責：驅動器協議（driver_interface）、里程積分（SUB-004 Wheel Odometry）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_TWO_PI = 2.0 * math.pi
_RPM_TO_RAD_S = _TWO_PI / 60.0


@dataclass(frozen=True, slots=True)
class WheelCommand:
    """馬達端轉速命令（已含方向修正與限制）。"""

    right_motor_rpm: int
    left_motor_rpm: int


@dataclass(frozen=True, slots=True)
class WheelState:
    """輪端狀態（車體座標系）。"""

    right_position_rad: float
    left_position_rad: float
    right_velocity_rad_s: float
    left_velocity_rad_s: float


@dataclass(slots=True)
class VehicleGeometry:
    """車體幾何與傳動參數。

    counts_per_motor_rev 由驅動器 01-06 推導，不寫死；
    見 docs/05_subsystem.md § SUB-001 Encoder 位置解碼。
    """

    wheel_radius_m: float
    wheel_separation_m: float
    gear_ratio: float
    counts_per_motor_rev: int
    right_motor_sign: int = -1
    left_motor_sign: int = 1
    right_feedback_sign: int = -1
    left_feedback_sign: int = 1
    max_motor_rpm: int = 4000
    min_effective_motor_rpm: int = 60

    def __post_init__(self) -> None:
        if self.wheel_radius_m <= 0.0:
            raise ValueError('wheel_radius_m 必須 > 0')
        if self.wheel_separation_m <= 0.0:
            raise ValueError('wheel_separation_m 必須 > 0')
        if self.gear_ratio <= 0.0:
            raise ValueError('gear_ratio 必須 > 0')
        if self.counts_per_motor_rev <= 0:
            raise ValueError('counts_per_motor_rev 必須 > 0')
        if self.max_motor_rpm <= 0:
            raise ValueError('max_motor_rpm 必須 > 0')
        if self.min_effective_motor_rpm < 0:
            raise ValueError('min_effective_motor_rpm 必須 >= 0')
        if self.min_effective_motor_rpm > self.max_motor_rpm:
            raise ValueError('min_effective_motor_rpm 不得大於 max_motor_rpm')

        self.right_motor_sign = 1 if self.right_motor_sign >= 0 else -1
        self.left_motor_sign = 1 if self.left_motor_sign >= 0 else -1
        self.right_feedback_sign = 1 if self.right_feedback_sign >= 0 else -1
        self.left_feedback_sign = 1 if self.left_feedback_sign >= 0 else -1

    @property
    def counts_per_wheel_rev(self) -> float:
        return self.counts_per_motor_rev * self.gear_ratio


class DifferentialKinematics:
    """差速輪運動學換算。"""

    def __init__(self, geometry: VehicleGeometry) -> None:
        self._geometry = geometry

    @property
    def geometry(self) -> VehicleGeometry:
        return self._geometry

    # ── 命令路徑：/cmd_vel → 馬達端 RPM ──────────────────────────────────────

    def to_wheel_command(self, linear_x: float, angular_z: float) -> WheelCommand:
        """車體速度轉為左右輪馬達端轉速命令。

        超過 max_motor_rpm 時，兩輪等比例縮放以保持 v/omega 比值，
        避免獨立截斷改變實際行進方向。
        """
        geom = self._geometry
        half_track = 0.5 * geom.wheel_separation_m

        right_ground_m_s = linear_x + angular_z * half_track
        left_ground_m_s = linear_x - angular_z * half_track

        right_rpm = self._ground_speed_to_motor_rpm(right_ground_m_s)
        left_rpm = self._ground_speed_to_motor_rpm(left_ground_m_s)

        right_rpm, left_rpm = self._scale_to_limit(right_rpm, left_rpm)

        return WheelCommand(
            right_motor_rpm=int(round(
                self._apply_deadband(right_rpm) * geom.right_motor_sign
            )),
            left_motor_rpm=int(round(
                self._apply_deadband(left_rpm) * geom.left_motor_sign
            )),
        )

    def _ground_speed_to_motor_rpm(self, ground_m_s: float) -> float:
        geom = self._geometry
        wheel_rad_s = ground_m_s / geom.wheel_radius_m
        motor_rad_s = wheel_rad_s * geom.gear_ratio
        return motor_rad_s / _RPM_TO_RAD_S

    def _scale_to_limit(self, right_rpm: float, left_rpm: float) -> tuple[float, float]:
        peak = max(abs(right_rpm), abs(left_rpm))
        limit = self._geometry.max_motor_rpm
        if peak <= limit:
            return right_rpm, left_rpm
        scale = limit / peak
        return right_rpm * scale, left_rpm * scale

    def _apply_deadband(self, rpm: float) -> float:
        """低於最小有效轉速時驅動器控制不穩定，抬升至下限。

        兩輪各自套用，故極低速轉彎時 v/omega 比值會失真；
        此限制源自驅動器特性，實務行進速度不受影響。
        """
        minimum = self._geometry.min_effective_motor_rpm
        if rpm == 0.0 or minimum == 0:
            return rpm
        if abs(rpm) < minimum:
            return math.copysign(minimum, rpm)
        return rpm

    # ── 回授路徑：馬達端 → 輪端（車體座標系）────────────────────────────────

    def to_wheel_state(
        self,
        right_motor_rpm: int,
        left_motor_rpm: int,
        right_motor_counts: int,
        left_motor_counts: int,
    ) -> WheelState:
        """馬達端回授轉為輪端角位置與角速度，並套用方向修正。"""
        geom = self._geometry
        return WheelState(
            right_position_rad=self._counts_to_wheel_rad(right_motor_counts)
            * geom.right_feedback_sign,
            left_position_rad=self._counts_to_wheel_rad(left_motor_counts)
            * geom.left_feedback_sign,
            right_velocity_rad_s=self._motor_rpm_to_wheel_rad_s(right_motor_rpm)
            * geom.right_feedback_sign,
            left_velocity_rad_s=self._motor_rpm_to_wheel_rad_s(left_motor_rpm)
            * geom.left_feedback_sign,
        )

    def _counts_to_wheel_rad(self, motor_counts: int) -> float:
        return motor_counts / self._geometry.counts_per_wheel_rev * _TWO_PI

    def _motor_rpm_to_wheel_rad_s(self, motor_rpm: int) -> float:
        return motor_rpm * _RPM_TO_RAD_S / self._geometry.gear_ratio
