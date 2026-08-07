"""Modbus Transport — Multi-drive 2.0 over RS-485.

負責 Modbus RTU 封包組裝、CRC、序列埠收發。

不負責：單位換算、運動學、驅動器狀態機（由上層 driver_interface 處理）。

協議參數於 2026-08-07 實機驗證，詳見 docs/implementation/SUB-001-base-control-plan.md。
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass

import serial

# ── Modbus function codes ────────────────────────────────────────────────────
FC_READ_HOLDING = 0x03
FC_WRITE_SINGLE = 0x06
FC_READ_WRITE_MULTIPLE = 0x17

# ── Multi-drive 2.0 群組定址 ─────────────────────────────────────────────────
# 位址上位元組 [15:12]=0xF、[11:8]=Index；下位元組 bit n = Driver ID (n+1) 被選中。
MD2_GROUP_ID = 0x65
_DRIVER_BITMASK = 0x03          # ID1 + ID2

READ_INDEX_BASE = 0
READ_ITEM_COUNT = 7             # Read index 0~6
WRITE_INDEX_BASE = 8
WRITE_ITEM_COUNT = 2            # Write index 8~9

R_ADDR = 0xF000 | (READ_INDEX_BASE << 8) | _DRIVER_BITMASK    # 0xF003
W_ADDR = 0xF000 | (WRITE_INDEX_BASE << 8) | _DRIVER_BITMASK   # 0xF803

NUM_DRIVERS = 2
_ITEMS_PER_DRIVER = READ_ITEM_COUNT + 1     # +1: Error_Check
R_CNT = _ITEMS_PER_DRIVER * NUM_DRIVERS     # 16 words
W_CNT = WRITE_ITEM_COUNT * NUM_DRIVERS      # 4 words

# Read Data Mapping（09-26 = 0）
IDX_STATUS = 0
IDX_ALARM = 1
IDX_RPM = 2
IDX_POS_TURNS = 5
IDX_POS_PULSE = 6


class Md2Error(Exception):
    """Multi-drive 2.0 通訊或解析錯誤。"""


@dataclass(frozen=True, slots=True)
class DriverRaw:
    """單一驅動器之原始回授（未套用方向修正與單位換算）。"""

    status: int
    alarm: int
    rpm: int            # signed, 馬達端 RPM
    pos_turns: int      # signed, 圈數
    pos_pulse: int      # 0 ~ (pulse_per_rev - 1)


@dataclass(frozen=True, slots=True)
class Md2Feedback:
    """一次 FC17h 交易之雙驅動器回授。"""

    right: DriverRaw
    left: DriverRaw
    comm_s: float


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def _with_crc(frame: bytes) -> bytes:
    crc = crc16(frame)
    return frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def _crc_ok(frame: bytes) -> bool:
    return len(frame) >= 3 and crc16(frame[:-2]) == (frame[-2] | (frame[-1] << 8))


def to_s16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value >= 0x8000 else value


class Md2Transport:
    """RS-485 Multi-drive 2.0 傳輸層。"""

    def __init__(
        self,
        port: str,
        baud: int = 230400,
        timeout_s: float = 0.1,
        bytesize: int = 8,
        parity: str = 'N',
        stopbits: int = 1,
    ) -> None:
        self._serial = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout_s,
        )

    def close(self) -> None:
        if self._serial.is_open:
            self._serial.close()

    def drain(self, settle_s: float = 0.05) -> None:
        """清空收發緩衝並等待匯流排靜默。

        交易途中被中斷時，未讀完之回應會殘留於緩衝區，
        使後續請求讀到前一筆回應而 CRC 失敗。關閉流程前須先排空。
        """
        time.sleep(settle_s)
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

    def __enter__(self) -> 'Md2Transport':
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── 低階收發 ─────────────────────────────────────────────────────────────

    def _transact(self, request: bytes, expect_len: int) -> bytes:
        self._serial.reset_input_buffer()
        self._serial.write(request)
        self._serial.flush()
        response = self._serial.read(expect_len)
        if len(response) < expect_len:
            raise Md2Error(
                f'回應長度不足：期望 {expect_len}，收到 {len(response)}'
                f'（{response.hex()}）'
            )
        if response[1] & 0x80:
            raise Md2Error(f'驅動器例外碼 0x{response[2]:02X}')
        if not _crc_ok(response):
            raise Md2Error(f'CRC 錯誤：{response.hex()}')
        return response

    # ── FC03 / FC06：個別驅動器 ──────────────────────────────────────────────

    def read_register(self, driver_id: int, address: int) -> int:
        """讀取單一保持暫存器。"""
        request = _with_crc(
            bytes([driver_id, FC_READ_HOLDING]) + struct.pack('>HH', address, 1)
        )
        response = self._transact(request, 7)
        return struct.unpack('>H', response[3:5])[0]

    def write_register(self, driver_id: int, address: int, value: int) -> None:
        """寫入單一保持暫存器。"""
        request = _with_crc(
            bytes([driver_id, FC_WRITE_SINGLE])
            + struct.pack('>HH', address, value & 0xFFFF)
        )
        self._transact(request, 8)

    # ── FC17h：雙驅動器讀寫合一 ──────────────────────────────────────────────

    def read_write(
        self,
        right_cmd: int,
        right_rpm: int,
        left_cmd: int,
        left_rpm: int,
    ) -> Md2Feedback:
        """單一封包同時下達雙輪命令並讀回回授。

        Write data 為 driver-major：[ID1_cmd][ID1_rpm][ID2_cmd][ID2_rpm]。
        """
        header = bytes([MD2_GROUP_ID, FC_READ_WRITE_MULTIPLE]) + struct.pack(
            '>HHHHB', R_ADDR, R_CNT, W_ADDR, W_CNT, W_CNT * 2
        )
        body = struct.pack(
            '>HHHH',
            right_cmd & 0xFFFF,
            right_rpm & 0xFFFF,
            left_cmd & 0xFFFF,
            left_rpm & 0xFFFF,
        )
        expect_len = 3 + R_CNT * 2 + 2

        start = time.monotonic()
        response = self._transact(_with_crc(header + body), expect_len)
        comm_s = time.monotonic() - start

        if response[2] != R_CNT * 2:
            raise Md2Error(
                f'byte_cnt 不符：期望 {R_CNT * 2}，收到 {response[2]}'
            )

        words = [
            struct.unpack('>H', response[3 + i * 2:5 + i * 2])[0]
            for i in range(R_CNT)
        ]
        return Md2Feedback(
            right=self._extract(words, 0),
            left=self._extract(words, 1),
            comm_s=comm_s,
        )

    @staticmethod
    def _extract(words: list[int], driver_slot: int) -> DriverRaw:
        base = driver_slot * _ITEMS_PER_DRIVER
        return DriverRaw(
            status=words[base + IDX_STATUS],
            alarm=words[base + IDX_ALARM],
            rpm=to_s16(words[base + IDX_RPM]),
            pos_turns=to_s16(words[base + IDX_POS_TURNS]),
            pos_pulse=words[base + IDX_POS_PULSE],
        )
