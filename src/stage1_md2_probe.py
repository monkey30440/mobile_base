#!/usr/bin/env python3
"""
SUB-001 Stage 1 — Multi-drive 2.0 通訊驗證（拋棄式工具，不納入正式 package）

目的：於實機上否證 `05_subsystem.md` SUB-001 所列之未驗證假設：
  - RS-485 通訊參數（Baud / 框架）
  - Driver ID
  - Multi-drive 2.0 FC17h 群組定址與 Register Map
  - 左右輪可各自獨立轉動並讀回回授

協議參數來源：既有專案 Baseline（`ref/base_motor_controller`），
本階段任務即為在實機上證實或否證這些值。

三段漸進，安全閘控：
  read   唯讀      FC03 讀取各驅動器狀態，不寫入任何暫存器
  md2    寫入但不動 FC17h 群組讀寫，CMD=ISTOP、speed=0
  spin   會轉動     單輪低速轉動，需 --confirm，車輛須架高

用法：
    python3 stage1_md2_probe.py read
    python3 stage1_md2_probe.py md2
    python3 stage1_md2_probe.py spin --wheel right --rpm 60 --seconds 2 --confirm
"""

import argparse
import struct
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("需要 pyserial：pip3 install pyserial")


# ── 待驗證之協議參數（來源：既有專案 Baseline）────────────────────────────────
PORT_DEFAULT = "/dev/ttyUSB0"
BAUD = 230400
BYTESIZE, PARITY, STOPBITS = 8, "N", 1

RIGHT_ID, LEFT_ID = 1, 2

# 個別驅動器暫存器（FC03 讀 / FC06 寫）
ADDR_NET_IN = 0x1400
ADDR_ALARM_NO = 0x0003
ADDR_MOTOR_STATUS = 0x4600

# NET-IN bit mapping
BIT_FWD, BIT_REV, BIT_ALM_RST = 0, 1, 3
BIT_D0, BIT_D1, BIT_FREE, BIT_SERVO_EN = 4, 5, 6, 7

# Multi-Drive Lite CMD
MD_LITE_ISTOP = 0x0000
MD_LITE_JG = 0x0001

# FC17h 群組定址
MD2_DEVICE_ID = 0x65
FC17H = 0x17
R_ADDR, R_CNT = 0xF003, 16      # 8 items/driver × 2 drivers（含 Error_Check）
W_ADDR, W_CNT = 0xF803, 4       # cmd + speed，× 2 drivers
ITEMS_PER_DRIVER = 8
IDX_STATUS, IDX_ALARM, IDX_RPM, IDX_ENC_HI, IDX_ENC_LO = 0, 1, 2, 5, 6

RPM_MIN, RPM_MAX = 60, 4400

MOTOR_STATUS_MAP = {
    0: "STOP", 2: "RUN", 3: "EBRAKE", 4: "FREE", 5: "FAULT",
    6: "WAIT/INHIBIT", 7: "MOVING(SERVO ON)", 8: "SLIGHT-POS-KEEPING", 9: "STO",
}


# ── Modbus RTU 基礎 ───────────────────────────────────────────────────────────

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def with_crc(frame: bytes) -> bytes:
    crc = crc16(frame)
    return frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def crc_ok(frame: bytes) -> bool:
    return len(frame) >= 3 and crc16(frame[:-2]) == (frame[-2] | (frame[-1] << 8))


def s16(x: int) -> int:
    x &= 0xFFFF
    return x - 0x10000 if x >= 0x8000 else x


def s32(hi: int, lo: int) -> int:
    v = ((hi & 0xFFFF) << 16 | (lo & 0xFFFF)) & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def open_port(port: str, timeout: float = 0.1) -> serial.Serial:
    return serial.Serial(
        port=port, baudrate=BAUD, bytesize=BYTESIZE,
        parity=PARITY, stopbits=STOPBITS, timeout=timeout,
    )


def transact(ser: serial.Serial, request: bytes, expect_len: int) -> bytes:
    ser.reset_input_buffer()
    ser.write(request)
    ser.flush()
    return ser.read(expect_len)


# ── FC03 / FC06（個別驅動器）──────────────────────────────────────────────────

def read_fc03(ser, driver_id: int, address: int, count: int = 1):
    req = with_crc(bytes([driver_id, 0x03]) + struct.pack(">HH", address, count))
    resp = transact(ser, req, 5 + count * 2)
    if len(resp) < 5:
        return None, f"無回應（收到 {len(resp)} bytes）"
    if resp[1] & 0x80:
        return None, f"exception 0x{resp[2]:02X}"
    if not crc_ok(resp):
        return None, f"CRC 錯誤 {resp.hex()}"
    n = resp[2]
    return [struct.unpack(">H", resp[3 + i * 2:5 + i * 2])[0] for i in range(n // 2)], None


def write_fc06(ser, driver_id: int, address: int, value: int):
    req = with_crc(bytes([driver_id, 0x06]) + struct.pack(">HH", address, value & 0xFFFF))
    resp = transact(ser, req, 8)
    if len(resp) < 8:
        return f"無回應（收到 {len(resp)} bytes）"
    if resp[1] & 0x80:
        return f"exception 0x{resp[2]:02X}"
    if not crc_ok(resp):
        return f"CRC 錯誤 {resp.hex()}"
    return None


def net_in(servo_en=False, free=False, fwd=False, rev=False, alm_rst=False) -> int:
    v = 0
    for bit, on in ((BIT_SERVO_EN, servo_en), (BIT_FREE, free), (BIT_FWD, fwd),
                    (BIT_REV, rev), (BIT_ALM_RST, alm_rst)):
        if on:
            v |= 1 << bit
    return v


# ── FC17h（群組讀寫）──────────────────────────────────────────────────────────

def fc17h(ser, right_rpm: int, left_rpm: int, cmd: int = MD_LITE_JG):
    header = bytes([MD2_DEVICE_ID, FC17H]) + struct.pack(
        ">HHHHB", R_ADDR, R_CNT, W_ADDR, W_CNT, W_CNT * 2)
    # driver-major: [D1_cmd][D1_spd][D2_cmd][D2_spd]
    body = struct.pack(">HHHH", cmd & 0xFFFF, right_rpm & 0xFFFF,
                       cmd & 0xFFFF, left_rpm & 0xFFFF)
    expect = 3 + R_CNT * 2 + 2
    t0 = time.perf_counter()
    resp = transact(ser, with_crc(header + body), expect)
    comm_ms = (time.perf_counter() - t0) * 1000

    if len(resp) < expect:
        return None, f"回應長度不足：期望 {expect}，收到 {len(resp)}（{resp.hex()}）"
    if resp[1] & 0x80:
        return None, f"exception 0x{resp[2]:02X}"
    if not crc_ok(resp[:expect]):
        return None, f"CRC 錯誤 {resp[:expect].hex()}"
    if resp[2] != R_CNT * 2:
        return None, f"byte_cnt 不符：期望 {R_CNT * 2}，收到 {resp[2]}"

    words = [struct.unpack(">H", resp[3 + i * 2:5 + i * 2])[0] for i in range(R_CNT)]

    def driver(d):
        base = d * ITEMS_PER_DRIVER
        w5 = words[base + IDX_ENC_HI]
        w6 = words[base + IDX_ENC_LO]
        return {
            "status": words[base + IDX_STATUS],
            "alarm": words[base + IDX_ALARM],
            "rpm": s16(words[base + IDX_RPM]),
            "encoder": s32(w5, w6),
            "w5": w5,
            "w6": w6,
        }

    return {"right": driver(0), "left": driver(1), "comm_ms": comm_ms}, None


def show(label: str, d: dict):
    st = MOTOR_STATUS_MAP.get(d["status"], f"UNKNOWN({d['status']})")
    print(f"  {label:5s} status={d['status']} ({st})  alarm={d['alarm']}  "
          f"rpm={d['rpm']:+5d}  encoder={d['encoder']:+d}")


# ── 指令 ──────────────────────────────────────────────────────────────────────

def cmd_read(args):
    """唯讀：FC03 逐顆讀取，不寫入任何暫存器。"""
    print(f"Port {args.port} @ {BAUD} {BYTESIZE}{PARITY}{STOPBITS}")
    print("唯讀模式，不會寫入暫存器，輪子不會轉動。\n")
    ok = True
    with open_port(args.port) as ser:
        for name, did in (("右輪", RIGHT_ID), ("左輪", LEFT_ID)):
            print(f"--- {name}（Driver ID {did}）---")
            for label, addr in (("motor_status", ADDR_MOTOR_STATUS),
                                ("alarm_no", ADDR_ALARM_NO),
                                ("net_in", ADDR_NET_IN)):
                values, err = read_fc03(ser, did, addr)
                if err:
                    print(f"  {label:13s} @0x{addr:04X}  {err}")
                    ok = False
                else:
                    v = values[0]
                    extra = ""
                    if label == "motor_status":
                        extra = f"  ({MOTOR_STATUS_MAP.get(v, 'UNKNOWN')})"
                    print(f"  {label:13s} @0x{addr:04X}  = {v:5d}  0x{v:04X}{extra}")
                time.sleep(0.02)
            print()
    print("=" * 56)
    print("通訊正常，Driver ID 與暫存器位址確認。" if ok else
          "部分讀取失敗，見上方訊息。")
    return 0 if ok else 1


def cmd_md2(args):
    """FC17h 群組協議驗證：CMD=ISTOP、speed=0，不會轉動。"""
    print(f"Port {args.port} @ {BAUD}  群組位址 0x{MD2_DEVICE_ID:02X}")
    print("FC17h 群組讀寫，CMD=ISTOP、speed=0，輪子不會轉動。\n")
    with open_port(args.port) as ser:
        fb, err = fc17h(ser, right_rpm=0, left_rpm=0, cmd=MD_LITE_ISTOP)
        if err:
            print(f"FC17h 失敗：{err}")
            return 1
        print(f"--- FC17h 回應（{fb['comm_ms']:.1f} ms）---")
        show("right", fb["right"])
        show("left", fb["left"])
    print("\n" + "=" * 56)
    print("FC17h 群組定址與 Register Map 確認。")
    return 0


def cmd_spin(args):
    """單輪低速轉動。需 --confirm，車輛須架高。"""
    if not args.confirm:
        print("此指令會使輪子轉動。確認車輛已架高、輪子懸空後，加上 --confirm 再執行。")
        return 1
    rpm = max(RPM_MIN, min(RPM_MAX, args.rpm))
    right = rpm if args.wheel == "right" else 0
    left = rpm if args.wheel == "left" else 0

    print(f"Port {args.port} @ {BAUD}")
    print(f"轉動 {args.wheel} 輪：{rpm} RPM，持續 {args.seconds} 秒")
    print("車輛應已架高。Ctrl-C 可隨時中止（中止時仍會送出停止命令）。\n")

    with open_port(args.port) as ser:
        try:
            # 1. SERVO-EN ON（FREE=OFF），逐顆 FC06
            print("[1] SERVO-EN ON")
            for did in (RIGHT_ID, LEFT_ID):
                err = write_fc06(ser, did, ADDR_NET_IN, net_in(servo_en=True))
                if err:
                    print(f"    Driver {did} 失敗：{err}")
                    return 1
                time.sleep(0.02)

            # 2. 先送 speed=0 確認通訊
            fb, err = fc17h(ser, 0, 0, cmd=MD_LITE_JG)
            if err:
                print(f"    FC17h 前置確認失敗：{err}")
                return 1
            print("    通訊確認 OK\n")

            # 3. 轉動
            print(f"[2] 送出速度命令")
            deadline = time.time() + args.seconds
            while time.time() < deadline:
                fb, err = fc17h(ser, right, left, cmd=MD_LITE_JG)
                if err:
                    print(f"    FC17h 失敗：{err}")
                    break
                if args.raw:
                    w = fb[args.wheel]
                    print(f"    {fb['comm_ms']:5.1f}ms  rpm={w['rpm']:+5d}  "
                          f"w5={w['w5']:6d}  w6={w['w6']:6d}  "
                          f"w5*10000+w6={w['w5'] * 10000 + w['w6']:+9d}  "
                          f"s32={w['encoder']:+9d}")
                else:
                    print(f"    {fb['comm_ms']:5.1f}ms  "
                          f"R rpm={fb['right']['rpm']:+5d} enc={fb['right']['encoder']:+9d}  |  "
                          f"L rpm={fb['left']['rpm']:+5d} enc={fb['left']['encoder']:+9d}")
                time.sleep(args.period)
        except KeyboardInterrupt:
            print("\n    使用者中止")
        finally:
            # 4. 停止並解除激磁
            print("\n[3] 停止")
            fc17h(ser, 0, 0, cmd=MD_LITE_ISTOP)
            time.sleep(0.05)
            for did in (RIGHT_ID, LEFT_ID):
                write_fc06(ser, did, ADDR_NET_IN, net_in(servo_en=False))
                time.sleep(0.02)
            print("    SERVO-EN OFF")
    return 0


def main():
    p = argparse.ArgumentParser(description="SUB-001 Stage 1 Multi-drive 2.0 通訊驗證")
    p.add_argument("--port", default=PORT_DEFAULT)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("read", help="唯讀：FC03 讀取驅動器狀態")
    s.set_defaults(func=cmd_read)

    s = sub.add_parser("md2", help="FC17h 群組協議驗證（speed=0，不轉動）")
    s.set_defaults(func=cmd_md2)

    s = sub.add_parser("spin", help="單輪低速轉動（需 --confirm）")
    s.add_argument("--wheel", choices=("right", "left"), required=True)
    s.add_argument("--rpm", type=int, default=RPM_MIN)
    s.add_argument("--seconds", type=float, default=2.0)
    s.add_argument("--period", type=float, default=0.1)
    s.add_argument("--confirm", action="store_true")
    s.add_argument("--raw", action="store_true", help="顯示 encoder 原始 word，驗證組合方式")
    s.set_defaults(func=cmd_spin)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
