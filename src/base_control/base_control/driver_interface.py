"""Driver Interface — DEXMART M1 驅動器語意層。

負責驅動器暫存器語意、組態驗證、激磁控制、警報處理，
並將原始回授解碼為馬達端工程量（RPM、累積 counts）。

不負責：Modbus 封包（md2_transport）、車體運動學（kinematics）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .md2_transport import Md2Error, Md2Transport

# ── 暫存器位址 ───────────────────────────────────────────────────────────────
ADDR_ALARM_NO = 0x0003
ADDR_ENCODER_RESOLUTION = 0x0105        # 01-06 單相 pulse/rev
ADDR_POSITION_FORMAT = 0x020D           # 02-14 位置命令格式
ADDR_NET_IN = 0x1400
ADDR_LINEAR_ACC_MS = 0x4000             # 04-01
ADDR_SCURVE_ACC_MS = 0x4004
ADDR_LINEAR_DEC_MS = 0x4008             # 04-09
ADDR_SCURVE_DEC_MS = 0x400C
ADDR_MOTOR_STATUS = 0x4600

# ── NET-IN bit mapping ───────────────────────────────────────────────────────
BIT_FWD = 0
BIT_REV = 1
BIT_ALM_RST = 3
BIT_D0 = 4
BIT_D1 = 5
BIT_FREE = 6
BIT_SERVO_EN = 7

# ── Multi-Drive Lite 指令 ────────────────────────────────────────────────────
MD_LITE_ISTOP = 0x0000
MD_LITE_JG = 0x0001
MD_LITE_FREE = 0x0005
MD_LITE_SVON = 0x0006
MD_LITE_BRAKE = 0x0009

# ── 位置命令格式（02-14）─────────────────────────────────────────────────────
# 0: Index(turns) + pulse  ← 本專案採用之出廠預設
# 1: Step(上位) + Step(下位)
POSITION_FORMAT_TURNS_PULSE = 0

# 增量式編碼器為四倍頻
QUADRATURE_FACTOR = 4

MOTOR_STATUS_MAP = {
    0: 'STOP',
    2: 'RUN',
    3: 'EBRAKE',
    4: 'FREE',
    5: 'FAULT',
    6: 'WAIT/INHIBIT',
    7: 'MOVING(SERVO ON)',
    8: 'SLIGHT-POS-KEEPING',
    9: 'STO',
}

# 連續 FC06 之間隔；RS-485 半雙工，避免碰撞
_FC06_GAP_S = 0.02
_ALM_RST_PULSE_S = 0.2


class DriverConfigError(Exception):
    """驅動器組態與本專案假設不符。"""


@dataclass(frozen=True, slots=True)
class MotorFeedback:
    """單一驅動器之馬達端回授。"""

    status: int
    alarm: int
    rpm: int                # signed, 馬達端
    position_counts: int    # signed, 馬達端累積 counts

    @property
    def status_text(self) -> str:
        return MOTOR_STATUS_MAP.get(self.status, f'UNKNOWN({self.status})')

    @property
    def has_alarm(self) -> bool:
        return self.alarm != 0


@dataclass(frozen=True, slots=True)
class DualFeedback:
    right: MotorFeedback
    left: MotorFeedback
    comm_s: float


def net_in_word(
    servo_en: bool = False,
    free: bool = False,
    fwd: bool = False,
    rev: bool = False,
    alm_rst: bool = False,
) -> int:
    word = 0
    for bit, enabled in (
        (BIT_SERVO_EN, servo_en),
        (BIT_FREE, free),
        (BIT_FWD, fwd),
        (BIT_REV, rev),
        (BIT_ALM_RST, alm_rst),
    ):
        if enabled:
            word |= 1 << bit
    return word


class DriverInterface:
    """左右輪驅動器控制與狀態讀取。"""

    def __init__(
        self,
        transport: Md2Transport,
        right_id: int = 1,
        left_id: int = 2,
    ) -> None:
        self._transport = transport
        self._right_id = right_id
        self._left_id = left_id
        self._counts_per_motor_rev: int | None = None

    @property
    def driver_ids(self) -> tuple[int, int]:
        return self._right_id, self._left_id

    @property
    def counts_per_motor_rev(self) -> int:
        """每馬達轉之 counts，由 01-06 推導，須先呼叫 validate_configuration()。"""
        if self._counts_per_motor_rev is None:
            raise DriverConfigError(
                'counts_per_motor_rev 尚未確定，請先呼叫 validate_configuration()'
            )
        return self._counts_per_motor_rev

    # ── 組態驗證 ─────────────────────────────────────────────────────────────

    def validate_configuration(self) -> int:
        """驗證驅動器組態並推導每轉 counts。

        本專案要求 02-14 = 0（Index(turns) + pulse）。驅動器端不做持久化設定，
        若讀到其他值代表驅動器曾被更改或更換，直接視為錯誤而非靜默容忍，
        避免產生無聲之里程誤差。

        Returns:
            counts_per_motor_rev = 編碼器解析度 × 4

        Raises:
            DriverConfigError: 組態不符或左右輪不一致。
        """
        resolutions = {}
        for label, driver_id in (('右輪', self._right_id), ('左輪', self._left_id)):
            position_format = self._transport.read_register(
                driver_id, ADDR_POSITION_FORMAT
            )
            if position_format != POSITION_FORMAT_TURNS_PULSE:
                raise DriverConfigError(
                    f'{label}（ID {driver_id}）位置命令格式 02-14 = {position_format}，'
                    f'本專案要求 {POSITION_FORMAT_TURNS_PULSE}'
                    f'（Index(turns) + pulse）。請將驅動器回復出廠預設。'
                )
            resolution = self._transport.read_register(
                driver_id, ADDR_ENCODER_RESOLUTION
            )
            if resolution <= 0:
                raise DriverConfigError(
                    f'{label}（ID {driver_id}）編碼器解析度 01-06 = {resolution}，不合法'
                )
            resolutions[label] = resolution

        if len(set(resolutions.values())) != 1:
            raise DriverConfigError(
                f'左右輪編碼器解析度不一致：{resolutions}'
            )

        self._counts_per_motor_rev = (
            next(iter(resolutions.values())) * QUADRATURE_FACTOR
        )
        return self._counts_per_motor_rev

    # ── 激磁控制 ─────────────────────────────────────────────────────────────

    def enable(self) -> None:
        """SERVO-EN ON、FREE OFF。"""
        self._write_net_in_both(net_in_word(servo_en=True))

    def disable(self) -> None:
        """SERVO-EN OFF。"""
        self._write_net_in_both(net_in_word(servo_en=False))

    def free(self) -> None:
        """FREE ON：不激磁，馬達可被外力轉動（推車模式）。"""
        self._write_net_in_both(net_in_word(free=True))

    def alarm_reset(self) -> None:
        """ALM-RST 脈衝。呼叫前須確保已停止運動。"""
        self._write_net_in_both(net_in_word(alm_rst=True))
        time.sleep(_ALM_RST_PULSE_S)
        self._write_net_in_both(net_in_word(servo_en=False))

    def apply_motion_profile(
        self,
        linear_acc_ms: int,
        linear_dec_ms: int,
        s_curve_acc_ms: int,
        s_curve_dec_ms: int,
    ) -> None:
        """寫入加減速參數（低頻，僅於未運動時呼叫）。"""
        for address, value in (
            (ADDR_LINEAR_ACC_MS, linear_acc_ms),
            (ADDR_LINEAR_DEC_MS, linear_dec_ms),
            (ADDR_SCURVE_ACC_MS, s_curve_acc_ms),
            (ADDR_SCURVE_DEC_MS, s_curve_dec_ms),
        ):
            self._write_register_both(address, value)

    def _write_net_in_both(self, word: int) -> None:
        self._write_register_both(ADDR_NET_IN, word)

    def _write_register_both(self, address: int, value: int) -> None:
        for driver_id in (self._right_id, self._left_id):
            self._transport.write_register(driver_id, address, value)
            time.sleep(_FC06_GAP_S)

    # ── 運動命令 ─────────────────────────────────────────────────────────────

    def command(self, right_rpm: int, left_rpm: int) -> DualFeedback:
        """下達雙輪馬達端轉速命令並讀回回授。"""
        return self._exchange(MD_LITE_JG, right_rpm, left_rpm)

    def stop(self) -> DualFeedback:
        """立即停止，維持激磁。"""
        return self._exchange(MD_LITE_ISTOP, 0, 0)

    def _exchange(self, cmd: int, right_rpm: int, left_rpm: int) -> DualFeedback:
        raw = self._transport.read_write(
            right_cmd=cmd,
            right_rpm=right_rpm,
            left_cmd=cmd,
            left_rpm=left_rpm,
        )
        return DualFeedback(
            right=self._decode(raw.right),
            left=self._decode(raw.left),
            comm_s=raw.comm_s,
        )

    def _decode(self, raw) -> MotorFeedback:
        """解碼馬達端位置。

        02-14 = 0 時位置以 (turns, pulse) 兩個 word 表示，
        累積 counts = turns × counts_per_motor_rev + pulse。
        """
        return MotorFeedback(
            status=raw.status,
            alarm=raw.alarm,
            rpm=raw.rpm,
            position_counts=(
                raw.pos_turns * self.counts_per_motor_rev + raw.pos_pulse
            ),
        )


__all__ = [
    'DriverConfigError',
    'DriverInterface',
    'DualFeedback',
    'Md2Error',
    'MotorFeedback',
    'MOTOR_STATUS_MAP',
    'net_in_word',
]
