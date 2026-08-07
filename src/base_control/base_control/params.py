"""Parameter Manager — ROS 參數宣告、讀取與驗證。

集中管理 SUB-001 之所有可組態項目，避免參數散落於各模組。
"""

from __future__ import annotations

from dataclasses import dataclass

from rclpy.node import Node

from .kinematics import VehicleGeometry


@dataclass(frozen=True, slots=True)
class SerialParams:
    port: str
    baud: int
    timeout_s: float
    bytesize: int
    parity: str
    stopbits: int


@dataclass(frozen=True, slots=True)
class DriverParams:
    right_id: int
    left_id: int
    linear_acc_ms: int
    linear_dec_ms: int
    s_curve_acc_ms: int
    s_curve_dec_ms: int


@dataclass(frozen=True, slots=True)
class ControlParams:
    loop_period_s: float
    cmd_vel_timeout_s: float
    frame_id: str
    left_joint_name: str
    right_joint_name: str


@dataclass(frozen=True, slots=True)
class BaseControlParams:
    serial: SerialParams
    driver: DriverParams
    control: ControlParams
    vehicle: dict

    def build_geometry(self, counts_per_motor_rev: int) -> VehicleGeometry:
        """以驅動器實測之 counts_per_motor_rev 建立車體幾何。

        counts_per_motor_rev 不由參數提供，一律由驅動器 01-06 推導，
        避免組態與硬體不一致產生無聲之里程誤差。
        """
        return VehicleGeometry(
            counts_per_motor_rev=counts_per_motor_rev,
            **self.vehicle,
        )


_DECLARATIONS = (
    ('serial.port', '/dev/ttyUSB0'),
    ('serial.baud', 230400),
    ('serial.timeout_s', 0.1),
    ('serial.bytesize', 8),
    ('serial.parity', 'N'),
    ('serial.stopbits', 1),

    ('driver.right_id', 1),
    ('driver.left_id', 2),
    ('driver.linear_acc_ms', 100),
    ('driver.linear_dec_ms', 100),
    ('driver.s_curve_acc_ms', 1),
    ('driver.s_curve_dec_ms', 1),

    ('vehicle.wheel_radius_m', 0.08),
    ('vehicle.wheel_separation_m', 0.555),
    ('vehicle.gear_ratio', 20.0),
    ('vehicle.right_motor_sign', -1),
    ('vehicle.left_motor_sign', 1),
    ('vehicle.right_feedback_sign', -1),
    ('vehicle.left_feedback_sign', 1),
    ('vehicle.max_motor_rpm', 4400),
    ('vehicle.min_effective_motor_rpm', 60),

    ('control.loop_period_s', 0.02),
    ('control.cmd_vel_timeout_s', 0.5),
    ('control.frame_id', 'base_link'),
    ('control.left_joint_name', 'left_wheel_joint'),
    ('control.right_joint_name', 'right_wheel_joint'),
)

_VEHICLE_KEYS = (
    'wheel_radius_m',
    'wheel_separation_m',
    'gear_ratio',
    'right_motor_sign',
    'left_motor_sign',
    'right_feedback_sign',
    'left_feedback_sign',
    'max_motor_rpm',
    'min_effective_motor_rpm',
)


def declare_parameters(node: Node) -> None:
    for name, default in _DECLARATIONS:
        node.declare_parameter(name, default)


def load_parameters(node: Node) -> BaseControlParams:
    def value(name: str):
        return node.get_parameter(name).value

    params = BaseControlParams(
        serial=SerialParams(
            port=value('serial.port'),
            baud=value('serial.baud'),
            timeout_s=value('serial.timeout_s'),
            bytesize=value('serial.bytesize'),
            parity=value('serial.parity'),
            stopbits=value('serial.stopbits'),
        ),
        driver=DriverParams(
            right_id=value('driver.right_id'),
            left_id=value('driver.left_id'),
            linear_acc_ms=value('driver.linear_acc_ms'),
            linear_dec_ms=value('driver.linear_dec_ms'),
            s_curve_acc_ms=value('driver.s_curve_acc_ms'),
            s_curve_dec_ms=value('driver.s_curve_dec_ms'),
        ),
        control=ControlParams(
            loop_period_s=value('control.loop_period_s'),
            cmd_vel_timeout_s=value('control.cmd_vel_timeout_s'),
            frame_id=value('control.frame_id'),
            left_joint_name=value('control.left_joint_name'),
            right_joint_name=value('control.right_joint_name'),
        ),
        vehicle={key: value(f'vehicle.{key}') for key in _VEHICLE_KEYS},
    )
    _validate(params)
    return params


def _validate(params: BaseControlParams) -> None:
    if params.control.loop_period_s <= 0.0:
        raise ValueError('control.loop_period_s 必須 > 0')
    if params.control.cmd_vel_timeout_s <= 0.0:
        raise ValueError('control.cmd_vel_timeout_s 必須 > 0')
    if params.driver.right_id == params.driver.left_id:
        raise ValueError('driver.right_id 與 driver.left_id 不得相同')
    if params.serial.parity not in ('N', 'E', 'O'):
        raise ValueError("serial.parity 必須為 'N'、'E' 或 'O'")
    # VehicleGeometry 之數值檢查於 build_geometry() 時由其 __post_init__ 執行
