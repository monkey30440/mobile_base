#!/usr/bin/env python3
"""
READ-ONLY validation of M1 Multi-drive 2.0 FC03 read_state().

Purpose:
  Verify that one Multi-drive 2.0 FC03 request can read ID1+ID2 and that
  status/alarm/RPM/position agree with ordinary Standard Modbus reference reads.

Safety:
  - READ ONLY: no enable, no register write, no RPM command.
  - Requires both motors to already be stationary.
  - Requires 02-14 = 1 so position is interpreted as signed int32 steps.

Reference reads:
  Standard Modbus dynamic registers:
    0x0000 status, 0x0002 actual RPM, 0x0003 alarm
  Standard Modbus Monitor Data:
    0x4615 current-position high word, 0x4616 current-position low word

Multi-drive 2.0 read:
  Group ID 0x65, FC03
  Read index 0..6 + per-driver Error_Check
"""

import argparse
import struct
import sys

from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16

GROUP_ID = 0x65
FC03 = 0x03
REG_POSITION_FORMAT = 0x020D
REG_CURRENT_POSITION_HI = 0x4615
REG_CURRENT_POSITION_LO = 0x4616


def s32(hi, lo):
    u = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    return u - 0x100000000 if u & 0x80000000 else u


def driver_bitmask(ids):
    mask = 0
    for sid in ids:
        if not 1 <= sid <= 8:
            raise ValueError("Multi-drive 2.0 IDs must be 1..8")
        mask |= 1 << (sid - 1)
    return mask


def fc03_many(ser, slave, address, count):
    """Standard Modbus FC03 for contiguous 16-bit registers."""
    ser.reset_input_buffer()
    req = frame(struct.pack(">BBHH", slave, FC03, address, count))
    ser.write(req)
    ser.flush()

    head = read_exact(ser, 3)
    if head[0] != slave:
        raise RuntimeError(
            f"ID{slave}: unexpected response slave 0x{head[0]:02X}"
        )
    if head[1] == 0x83:
        tail = read_exact(ser, 3)
        pkt = head + tail
        check_crc(pkt)
        raise RuntimeError(
            f"ID{slave}: Standard FC03 exception 0x{pkt[2]:02X}"
        )
    if head[1] != FC03:
        raise RuntimeError(
            f"ID{slave}: unexpected Standard Modbus FC 0x{head[1]:02X}"
        )
    if head[2] != count * 2:
        raise RuntimeError(
            f"ID{slave}: expected {count * 2} data bytes, got {head[2]}"
        )

    tail = read_exact(ser, head[2] + 2)
    pkt = head + tail
    check_crc(pkt)
    return list(struct.unpack(">" + "H" * count, pkt[3:-2]))


def read_standard_reference(ser, sid):
    # 0x0000..0x0003 gives status/reserved-or-command/rpm/alarm in the
    # already-used validation path. One transaction keeps the watchdog gap small.
    d = fc03_many(ser, sid, 0x0000, 4)
    pos = fc03_many(ser, sid, REG_CURRENT_POSITION_HI, 2)
    return {
        "status": d[0],
        "rpm": s16(d[2]),
        "alarm": d[3],
        "pos_hi": pos[0],
        "pos_lo": pos[1],
        "position_steps": s32(pos[0], pos[1]),
    }


def read_md2_fc03(ser, ids, start_index=0, n_items=7):
    ordered = sorted(ids)
    mask = driver_bitmask(ordered)

    read_addr = 0xF000 | (start_index << 8) | mask
    # Manual: each selected driver returns requested data + one Error_Check word.
    read_count = len(ordered) * (n_items + 1)

    req = frame(struct.pack(">BBHH", GROUP_ID, FC03, read_addr, read_count))
    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()

    head = read_exact(ser, 3)
    if head[0] != GROUP_ID:
        raise RuntimeError(
            f"unexpected Multi-drive group ID 0x{head[0]:02X}"
        )
    if head[1] == 0x83:
        tail = read_exact(ser, 3)
        pkt = head + tail
        check_crc(pkt)
        raise RuntimeError(
            f"Multi-drive 2.0 FC03 exception 0x{pkt[2]:02X}"
        )
    if head[1] != FC03:
        raise RuntimeError(
            f"unexpected Multi-drive 2.0 FC 0x{head[1]:02X}"
        )

    tail = read_exact(ser, head[2] + 2)
    pkt = head + tail
    check_crc(pkt)

    words = list(struct.unpack(">" + "H" * (head[2] // 2), pkt[3:-2]))
    expected = len(ordered) * (n_items + 1)
    if len(words) != expected:
        raise RuntimeError(
            f"expected {expected} response words, got {len(words)}"
        )

    rows = {}
    stride = n_items + 1
    for i, sid in enumerate(ordered):
        w = words[i * stride:(i + 1) * stride]
        rows[sid] = {
            "status": w[0],
            "alarm": w[1],
            "rpm": s16(w[2]),
            "bus_v_raw": w[3],
            "current_raw": w[4],
            "pos_hi": w[5],
            "pos_lo": w[6],
            "position_steps": s32(w[5], w[6]),
            "error_check": w[7],
        }
    return rows


def show(label, sid, row):
    print(
        f"{label} ID{sid}: status={row['status']} alarm={row['alarm']} "
        f"rpm={row['rpm']:+d} position_steps={row['position_steps']:+d} "
        f"hi=0x{row['pos_hi']:04X} lo=0x{row['pos_lo']:04X}"
    )


def main():
    ap = argparse.ArgumentParser(
        description="READ-ONLY compare Standard Modbus state with Multi-drive 2.0 FC03"
    )
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, required=True)
    ap.add_argument("--ids", required=True, help="two unique IDs, e.g. 1,2")
    ap.add_argument("--timeout", type=float, default=0.25)
    ap.add_argument(
        "--position-tolerance",
        type=int,
        default=2,
        help="allowed step difference between sequential reference/MD2 reads",
    )
    args = ap.parse_args()

    ids = [int(x) for x in args.ids.split(",")]
    if len(ids) != 2 or len(set(ids)) != 2:
        sys.exit("--ids must contain exactly two unique driver IDs")
    if any(not 1 <= sid <= 8 for sid in ids):
        sys.exit("driver IDs must be 1..8")
    if args.position_tolerance < 0:
        sys.exit("--position-tolerance must be >= 0")

    print("=== M1 MULTI-DRIVE 2.0 FC03 STATE TEST (READ ONLY) ===")
    print(f"port={args.port} baud={args.baud} ids={ids}")

    with serial.Serial(
        args.port,
        args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    ) as ser:
        print("\n[1] Preconditions")
        for sid in ids:
            fmt = fc03_one(ser, sid, REG_POSITION_FORMAT)
            print(f"ID{sid}: 02-14 position format = {fmt}")
            if fmt != 1:
                sys.exit(
                    f"BLOCKED: ID{sid} 02-14={fmt}; this test expects format 1"
                )

        print("\n[2] Standard Modbus reference")
        reference = {}
        for sid in ids:
            reference[sid] = read_standard_reference(ser, sid)
            show("STANDARD", sid, reference[sid])
            if reference[sid]["alarm"] != 0:
                sys.exit(
                    f"BLOCKED: ID{sid} alarm={reference[sid]['alarm']}"
                )
            if reference[sid]["rpm"] != 0:
                sys.exit(
                    f"BLOCKED: ID{sid} is moving (rpm={reference[sid]['rpm']})"
                )

        print("\n[3] One Multi-drive 2.0 FC03 read for both drivers")
        md2 = read_md2_fc03(ser, ids)
        for sid in sorted(ids):
            show("MD2-FC03", sid, md2[sid])
            print(f"           error_check=0x{md2[sid]['error_check']:04X}")

        print("\n[4] Compare")
        passed = True
        for sid in ids:
            ref = reference[sid]
            got = md2[sid]

            checks = {
                "status": got["status"] == ref["status"],
                "alarm": got["alarm"] == ref["alarm"],
                "rpm": got["rpm"] == ref["rpm"],
                "position": abs(
                    got["position_steps"] - ref["position_steps"]
                ) <= args.position_tolerance,
            }

            for name, ok in checks.items():
                if name == "position":
                    detail = (
                        f"standard={ref['position_steps']:+d} "
                        f"md2={got['position_steps']:+d} "
                        f"delta={got['position_steps'] - ref['position_steps']:+d}"
                    )
                else:
                    detail = f"standard={ref[name]} md2={got[name]}"
                print(f"ID{sid} {name:8s}: {'PASS' if ok else 'FAIL'} ({detail})")
                passed &= ok

        print("\n=== RESULT ===")
        if not passed:
            print("FAIL: Multi-drive 2.0 FC03 did not match the reference reads")
            sys.exit(2)

        print(
            "PASS: one Multi-drive 2.0 FC03 request returned both drivers with "
            "matching status/alarm/RPM/position semantics"
        )


if __name__ == "__main__":
    main()
