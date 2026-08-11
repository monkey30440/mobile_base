#!/usr/bin/env python3
"""
Safe M1 Multi-drive 2.0 lifecycle validation: SVON -> JG 0 -> SVOFF.

Purpose:
  Verify that the normal runtime lifecycle can use Multi-drive 2.0 FC17 for:
    - SVON  (servo enable)
    - JG 0  (explicit zero-speed command)
    - SVOFF (servo disable)
  while reading both drivers' state in the same FC17 transaction.

NO NON-ZERO RPM COMMAND IS EVER SENT.

Safety strategy:
  - requires explicit --arm I_UNDERSTAND
  - starts only if both drivers are alarm-free, rpm=0, status=WAIT/INHIBIT
  - requires verified mapping target 09-26=0
  - requires the verified SERVO-EN NET-X7 mapping (09-08=14)
  - finally always attempts JG 0, SVOFF, then the previously verified
    Standard Modbus NET-IN restore as a fallback

Target mapping used by existing bring-up scripts:
  Multi-drive 2.0 Write index 8 = Multi-drive Lite command
  Multi-drive 2.0 Write index 9 = Multi-drive Lite Data1

Commands:
  JG    = 0x01
  SVON  = 0x06
  SVOFF = 0x07
"""

import argparse
import struct
import sys
import time

from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16

GROUP_ID = 0x65
FC17 = 0x17
CMD_JG = 0x0001
CMD_SVON = 0x0006
CMD_SVOFF = 0x0007

REG_MD2_MAPPING = 0x0919   # 09-26
REG_NETX7_FUNCTION = 0x0907  # 09-08 = NET-X7 function
REG_NET_IN = 0x1400
FUNC_SERVO_EN = 14
SERVO_MASK = 0x0080


def s32(hi, lo):
    u = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    return u - 0x100000000 if u & 0x80000000 else u


def fc06(ser, slave, address, value):
    """Standard Modbus FC06, used only as the already-verified safety fallback."""
    ser.reset_input_buffer()
    req = frame(struct.pack(">BBHH", slave, 0x06, address, value & 0xFFFF))
    ser.write(req)
    ser.flush()

    resp = read_exact(ser, 8)
    check_crc(resp)
    if resp[:-2] != req[:-2]:
        raise RuntimeError(
            f"ID{slave}: FC06 echo mismatch addr=0x{address:04X}"
        )


def driver_bitmask(ids):
    mask = 0
    for sid in ids:
        if not 1 <= sid <= 8:
            raise ValueError("Multi-drive 2.0 IDs must be 1..8")
        mask |= 1 << (sid - 1)
    return mask


def parse_md2_words(words, ordered_ids):
    if len(words) != len(ordered_ids) * 8:
        raise RuntimeError(
            f"expected {len(ordered_ids) * 8} state words, got {len(words)}"
        )

    rows = {}
    for i, sid in enumerate(ordered_ids):
        w = words[i * 8:(i + 1) * 8]
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


def md2_fc03_state(ser, ids):
    """Pure Multi-drive 2.0 FC03 read of Data0..6 for all selected drivers."""
    ordered = sorted(ids)
    mask = driver_bitmask(ordered)
    address = 0xF000 | mask
    count = len(ordered) * 8

    req = frame(struct.pack(">BBHH", GROUP_ID, 0x03, address, count))
    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()

    head = read_exact(ser, 3)
    if head[0] != GROUP_ID:
        raise RuntimeError(f"unexpected group ID 0x{head[0]:02X}")
    if head[1] == 0x83:
        tail = read_exact(ser, 3)
        pkt = head + tail
        check_crc(pkt)
        raise RuntimeError(f"Multi-drive 2.0 FC03 exception 0x{pkt[2]:02X}")
    if head[1] != 0x03:
        raise RuntimeError(f"unexpected FC 0x{head[1]:02X}")

    tail = read_exact(ser, head[2] + 2)
    pkt = head + tail
    check_crc(pkt)
    words = list(struct.unpack(">" + "H" * (head[2] // 2), pkt[3:-2]))
    return parse_md2_words(words, ordered)


def md2_fc17_command(ser, ids, commands):
    """
    One Multi-drive 2.0 FC17 transaction.

    commands: {driver_id: (command_word, data1_word)}

    Reads Data0..6 while writing index8/index9 for every selected driver.
    """
    ordered = sorted(ids)
    mask = driver_bitmask(ordered)

    read_addr = 0xF000 | mask
    read_count = len(ordered) * 8
    write_addr = 0xF800 | mask

    write_words = []
    for sid in ordered:
        if sid not in commands:
            raise ValueError(f"missing command for ID{sid}")
        cmd, data1 = commands[sid]
        write_words.extend([cmd & 0xFFFF, data1 & 0xFFFF])

    body = struct.pack(
        ">BBHHHHB",
        GROUP_ID,
        FC17,
        read_addr,
        read_count,
        write_addr,
        len(write_words),
        len(write_words) * 2,
    )
    body += struct.pack(">" + "H" * len(write_words), *write_words)

    req = frame(body)
    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()

    head = read_exact(ser, 3)
    if head[0] != GROUP_ID:
        raise RuntimeError(f"unexpected group ID 0x{head[0]:02X}")
    if head[1] == 0x97:
        tail = read_exact(ser, 3)
        pkt = head + tail
        check_crc(pkt)
        raise RuntimeError(f"Multi-drive 2.0 FC17 exception 0x{pkt[2]:02X}")
    if head[1] != FC17:
        raise RuntimeError(f"unexpected FC 0x{head[1]:02X}")

    tail = read_exact(ser, head[2] + 2)
    pkt = head + tail
    check_crc(pkt)
    words = list(struct.unpack(">" + "H" * (head[2] // 2), pkt[3:-2]))
    return parse_md2_words(words, ordered)


def command_all(ids, command, data1=0):
    return {sid: (command, data1) for sid in ids}


def show(label, rows):
    print(label)
    for sid in sorted(rows):
        r = rows[sid]
        print(
            f"  ID{sid}: status={r['status']} alarm={r['alarm']} "
            f"rpm={r['rpm']:+d} pos={r['position_steps']:+d} "
            f"errchk=0x{r['error_check']:04X}"
        )


def all_safe_zero(rows):
    return all(r["alarm"] == 0 and r["rpm"] == 0 for r in rows.values())


def poll_state(ser, ids, predicate, attempts=4, interval=0.02):
    last = None
    for _ in range(attempts):
        last = md2_fc03_state(ser, ids)
        show("  poll", last)
        if predicate(last):
            return last
        time.sleep(interval)
    return last


def main():
    ap = argparse.ArgumentParser(
        description="Safe Multi-drive 2.0 FC17 SVON/JG0/SVOFF lifecycle test"
    )
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, required=True)
    ap.add_argument("--ids", required=True, help="two unique IDs, e.g. 1,2")
    ap.add_argument("--timeout", type=float, default=0.25)
    ap.add_argument("--arm", default="")
    args = ap.parse_args()

    if args.arm != "I_UNDERSTAND":
        sys.exit(
            "Refusing lifecycle writes. Re-run with --arm I_UNDERSTAND after "
            "wheels are lifted and E-stop/STO is immediately available."
        )

    ids = [int(x) for x in args.ids.split(",")]
    if len(ids) != 2 or len(set(ids)) != 2:
        sys.exit("--ids must contain exactly two unique driver IDs")
    if any(not 1 <= sid <= 8 for sid in ids):
        sys.exit("driver IDs must be 1..8")

    original_net_in = {}
    svon_sent = False
    passed = False

    print("=== ARMED M1 MULTI-DRIVE 2.0 LIFECYCLE TEST ===")
    print("NO NON-ZERO RPM COMMAND WILL BE SENT")
    print(f"port={args.port} baud={args.baud} ids={ids}")

    with serial.Serial(
        args.port,
        args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    ) as ser:
        print("\n[1] Verify target mapping and save NET-IN fallback state")
        for sid in ids:
            mapping = fc03_one(ser, sid, REG_MD2_MAPPING)
            netx7 = fc03_one(ser, sid, REG_NETX7_FUNCTION)
            net_in = fc03_one(ser, sid, REG_NET_IN)
            original_net_in[sid] = net_in

            print(
                f"ID{sid}: 09-26={mapping} 09-08(NET-X7)={netx7} "
                f"NET-IN=0x{net_in:04X}"
            )

            if mapping != 0:
                sys.exit(
                    f"BLOCKED: ID{sid} 09-26={mapping}; test target is verified mapping 0"
                )
            if netx7 != FUNC_SERVO_EN:
                sys.exit(
                    f"BLOCKED: ID{sid} NET-X7 function={netx7}, expected SERVO-EN(14)"
                )
            if net_in & SERVO_MASK:
                sys.exit(
                    f"BLOCKED: ID{sid} SERVO-EN is already ON in NET-IN"
                )

        print("\n[2] Preflight via Multi-drive 2.0 FC03")
        before = md2_fc03_state(ser, ids)
        show("BEFORE", before)
        for sid, row in before.items():
            if row["alarm"] != 0:
                sys.exit(f"BLOCKED: ID{sid} alarm={row['alarm']}")
            if row["rpm"] != 0:
                sys.exit(f"BLOCKED: ID{sid} rpm={row['rpm']} (must be 0)")
            if row["status"] != 6:
                sys.exit(
                    f"BLOCKED: ID{sid} status={row['status']}, expected WAIT/INHIBIT(6)"
                )

        try:
            print("\n[3] FC17 SVON + simultaneous state read")
            immediate = md2_fc17_command(
                ser, ids, command_all(ids, CMD_SVON, 0)
            )
            svon_sent = True
            show("SVON immediate response", immediate)
            if not all_safe_zero(immediate):
                raise RuntimeError("alarm or non-zero RPM in SVON response")

            enabled = poll_state(
                ser,
                ids,
                lambda rows: all(
                    r["status"] == 0 and r["alarm"] == 0 and r["rpm"] == 0
                    for r in rows.values()
                ),
            )
            if enabled is None or not all(
                r["status"] == 0 and r["alarm"] == 0 and r["rpm"] == 0
                for r in enabled.values()
            ):
                raise RuntimeError(
                    "SVON did not produce STOP(0), alarm=0, rpm=0 on both drivers"
                )

            print("\n[4] FC17 JG 0 + simultaneous state read")
            zero = md2_fc17_command(
                ser, ids, command_all(ids, CMD_JG, 0)
            )
            show("JG0 response", zero)
            if not all_safe_zero(zero):
                raise RuntimeError("JG0 produced alarm or non-zero RPM")

            print("\n[5] FC17 SVOFF + simultaneous state read")
            off_immediate = md2_fc17_command(
                ser, ids, command_all(ids, CMD_SVOFF, 0)
            )
            show("SVOFF immediate response", off_immediate)
            if not all_safe_zero(off_immediate):
                raise RuntimeError("alarm or non-zero RPM in SVOFF response")

            disabled = poll_state(
                ser,
                ids,
                lambda rows: all(
                    r["status"] == 6 and r["alarm"] == 0 and r["rpm"] == 0
                    for r in rows.values()
                ),
            )
            if disabled is None or not all(
                r["status"] == 6 and r["alarm"] == 0 and r["rpm"] == 0
                for r in disabled.values()
            ):
                raise RuntimeError(
                    "SVOFF did not produce WAIT/INHIBIT(6), alarm=0, rpm=0 on both drivers"
                )

            passed = True

        finally:
            print("\n[6] SAFETY CLEANUP / FALLBACK")

            # First: explicit zero-RPM traffic, if SVON may have been issued.
            if svon_sent:
                for attempt in range(3):
                    try:
                        rows = md2_fc17_command(
                            ser, ids, command_all(ids, CMD_JG, 0)
                        )
                        show(f"JG0 cleanup {attempt + 1}/3", rows)
                        if all(r["rpm"] == 0 for r in rows.values()):
                            break
                    except Exception as exc:
                        print(f"JG0 cleanup failed: {exc}", file=sys.stderr)
                    time.sleep(0.02)

                # Then try the new path under test: SVOFF.
                try:
                    rows = md2_fc17_command(
                        ser, ids, command_all(ids, CMD_SVOFF, 0)
                    )
                    show("SVOFF cleanup", rows)
                except Exception as exc:
                    print(f"SVOFF cleanup failed: {exc}", file=sys.stderr)

            # Last-resort, already-verified path: restore NET-IN with SERVO bit OFF.
            print("Standard Modbus NET-IN fallback restore")
            for sid in ids:
                try:
                    fallback = original_net_in.get(sid, 0) & ~SERVO_MASK
                    fc06(ser, sid, REG_NET_IN, fallback)
                    print(f"  ID{sid}: NET-IN -> 0x{fallback:04X}")
                except Exception as exc:
                    print(
                        f"  ID{sid}: NET-IN fallback FAILED: {exc}",
                        file=sys.stderr,
                    )

            try:
                final_rows = md2_fc03_state(ser, ids)
                show("FINAL", final_rows)
            except Exception as exc:
                print(f"final state read failed: {exc}", file=sys.stderr)

        print("\n=== RESULT ===")
        if not passed:
            print("FAIL: Multi-drive 2.0 lifecycle validation did not complete")
            sys.exit(2)

        print(
            "PASS: FC17 SVON -> JG0 -> SVOFF controlled both drivers with zero RPM, "
            "and Multi-drive 2.0 state feedback confirmed the lifecycle"
        )


if __name__ == "__main__":
    main()
