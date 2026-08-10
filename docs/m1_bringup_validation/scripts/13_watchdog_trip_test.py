#!/usr/bin/env python3
"""
M1 communication-watchdog trip test.

Purpose:
  Verify that the configured RS485 watchdog actually reacts to communication loss.

Expected target setup:
  05-17 = 100 ms
  05-18 = 3
  05-21 = 2   (alarm stop + clear remote/virtual I/O)

Test sequence:
  1. Verify both drivers are stopped, alarm-free, and watchdog settings are enabled.
  2. Discover the NET-X bit mapped to SERVO-EN (function 14).
  3. Discover the NET-X bit mapped to ALM-RST (function 8).
  4. Enable SERVO-EN on both drivers.
  5. Send only zero-RPM FC17 traffic for several cycles.
  6. Intentionally send NO RS485 traffic for --silence-ms (default 300 ms).
  7. Read status/alarm/RPM/NET-IN.
  8. Require:
       - alarm becomes non-zero (normally Alarm 21 for communication timeout)
       - RPM remains 0
       - SERVO-EN virtual input is cleared when 05-21=2
  9. Pulse the discovered ALM-RST NET-X bit to recover.
 10. Confirm alarm clears and SERVO-EN remains OFF.

No non-zero RPM command is ever sent.
"""

import argparse
import struct
import sys
import time

from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16


NET_IN_ADDR = 0x1400
FUNC_ALM_RST = 8
FUNC_SERVO_EN = 14
CMD_JG = 0x0001


def fc06(ser, slave, address, value):
    ser.reset_input_buffer()
    req = frame(struct.pack(">BBHH", slave, 0x06, address, value & 0xFFFF))
    ser.write(req)
    ser.flush()

    resp = read_exact(ser, 8)
    check_crc(resp)

    if resp[:-2] != req[:-2]:
        raise RuntimeError(
            f"ID{slave}: FC06 echo mismatch at 0x{address:04X}"
        )


def read_state(ser, driver_id):
    return {
        "status": fc03_one(ser, driver_id, 0x0000),
        "rpm": s16(fc03_one(ser, driver_id, 0x0002)),
        "alarm": fc03_one(ser, driver_id, 0x0003),
        "net_in": fc03_one(ser, driver_id, NET_IN_ADDR),
        "timeout_ms": fc03_one(ser, driver_id, 0x0510),
        "error_count": fc03_one(ser, driver_id, 0x0511),
        "failure_action": fc03_one(ser, driver_id, 0x0514),
    }


def show_state(prefix, driver_id, state):
    print(
        f"{prefix} ID{driver_id}: "
        f"status={state['status']} alarm={state['alarm']} "
        f"rpm={state['rpm']:+d} NET-IN=0x{state['net_in']:04X}"
    )


def find_netx_bit(ser, driver_id, function_code):
    matches = []
    for bit in range(15):
        value = fc03_one(ser, driver_id, 0x0900 + bit)
        if value == function_code:
            matches.append(bit)

    if len(matches) != 1:
        raise RuntimeError(
            f"ID{driver_id}: expected exactly one NET-X mapping for "
            f"function {function_code}, found bits {matches}"
        )
    return matches[0]


def driver_bitmask(driver_ids):
    mask = 0
    for driver_id in driver_ids:
        if not 1 <= driver_id <= 8:
            raise ValueError("Multi-drive 2.0 IDs must be 1..8")
        mask |= 1 << (driver_id - 1)
    return mask


def fc17_zero_rpm(ser, driver_ids):
    ordered_ids = sorted(driver_ids)
    mask = driver_bitmask(ordered_ids)

    read_addr = 0xF000 | mask
    read_count = len(ordered_ids) * 8

    write_addr = 0xF800 | mask
    write_words = []
    for _driver_id in ordered_ids:
        write_words.extend([CMD_JG, 0])

    body = struct.pack(
        ">BBHHHHB",
        0x65,
        0x17,
        read_addr,
        read_count,
        write_addr,
        len(write_words),
        len(write_words) * 2,
    )
    body += struct.pack(
        ">" + "H" * len(write_words),
        *write_words,
    )

    req = frame(body)

    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()

    head = read_exact(ser, 3)

    if head[0] != 0x65:
        raise RuntimeError(
            f"unexpected Multi-drive group ID 0x{head[0]:02X}"
        )

    if head[1] == 0x97:
        tail = read_exact(ser, 3)
        pkt = head + tail
        check_crc(pkt)
        raise RuntimeError(
            f"FC17 exception 0x{pkt[2]:02X}"
        )

    if head[1] != 0x17:
        raise RuntimeError(
            f"unexpected FC 0x{head[1]:02X}"
        )

    tail = read_exact(ser, head[2] + 2)
    pkt = head + tail
    check_crc(pkt)

    words = list(
        struct.unpack(
            ">" + "H" * (head[2] // 2),
            pkt[3:-2],
        )
    )

    if len(words) != len(ordered_ids) * 8:
        raise RuntimeError(
            f"unexpected FC17 response length: {len(words)} words"
        )

    rows = {}
    for index, driver_id in enumerate(ordered_ids):
        w = words[index * 8:(index + 1) * 8]
        rows[driver_id] = {
            "status": w[0],
            "alarm": w[1],
            "rpm": s16(w[2]),
        }

    return rows


def pulse_alarm_reset(
    ser,
    driver_id,
    alm_rst_mask,
    settle=0.15,
):
    current = fc03_one(ser, driver_id, NET_IN_ADDR)

    # Keep SERVO-EN OFF while resetting an alarm.
    base = current & ~alm_rst_mask

    fc06(
        ser,
        driver_id,
        NET_IN_ADDR,
        base | alm_rst_mask,
    )
    time.sleep(0.05)

    fc06(
        ser,
        driver_id,
        NET_IN_ADDR,
        base,
    )
    time.sleep(settle)


def main():
    parser = argparse.ArgumentParser(
        description="Intentionally trip and verify the M1 RS485 watchdog"
    )
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, required=True)
    parser.add_argument("--ids", required=True)
    parser.add_argument(
        "--silence-ms",
        type=int,
        default=300,
        help="intentional no-communication window; default 300 ms",
    )
    parser.add_argument(
        "--warmup-cycles",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--warmup-hz",
        type=float,
        default=30.0,
    )
    parser.add_argument(
        "--serial-timeout",
        type=float,
        default=0.25,
    )
    parser.add_argument("--arm", default="")
    args = parser.parse_args()

    if args.arm != "I_UNDERSTAND":
        sys.exit(
            "Refusing intentional watchdog trip. "
            "Re-run with --arm I_UNDERSTAND."
        )

    ids = [int(x) for x in args.ids.split(",")]

    if len(ids) != 2 or len(ids) != len(set(ids)):
        sys.exit("--ids must contain two unique driver IDs")

    if not 150 <= args.silence_ms <= 2000:
        sys.exit("--silence-ms must be 150..2000")

    if not 1 <= args.warmup_cycles <= 100:
        sys.exit("--warmup-cycles must be 1..100")

    if not 1 <= args.warmup_hz <= 50:
        sys.exit("--warmup-hz must be 1..50")

    servo_masks = {}
    alm_rst_masks = {}

    with serial.Serial(
        args.port,
        args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.serial_timeout,
    ) as ser:

        print("=== PRECHECK ===")
        for driver_id in ids:
            state = read_state(ser, driver_id)
            show_state("BEFORE", driver_id, state)

            print(
                f"ID{driver_id}: "
                f"05-17={state['timeout_ms']} ms "
                f"05-18={state['error_count']} "
                f"05-21={state['failure_action']}"
            )

            if state["alarm"] != 0:
                sys.exit(
                    f"BLOCKED: ID{driver_id} already has alarm "
                    f"{state['alarm']}"
                )

            if state["rpm"] != 0:
                sys.exit(
                    f"BLOCKED: ID{driver_id} is moving "
                    f"(rpm={state['rpm']})"
                )

            if state["timeout_ms"] <= 0:
                sys.exit(
                    f"BLOCKED: ID{driver_id} communication timeout is disabled"
                )

            if state["failure_action"] != 2:
                sys.exit(
                    f"BLOCKED: ID{driver_id} 05-21 is "
                    f"{state['failure_action']}, expected 2"
                )

            servo_bit = find_netx_bit(
                ser,
                driver_id,
                FUNC_SERVO_EN,
            )
            alm_rst_bit = find_netx_bit(
                ser,
                driver_id,
                FUNC_ALM_RST,
            )

            servo_masks[driver_id] = 1 << servo_bit
            alm_rst_masks[driver_id] = 1 << alm_rst_bit

            print(
                f"ID{driver_id}: "
                f"SERVO-EN=NET-X{servo_bit} "
                f"mask=0x{servo_masks[driver_id]:04X}; "
                f"ALM-RST=NET-X{alm_rst_bit} "
                f"mask=0x{alm_rst_masks[driver_id]:04X}"
            )

        print("\n=== ENABLE WITH ZERO RPM ONLY ===")
        for driver_id in ids:
            net_in = fc03_one(
                ser,
                driver_id,
                NET_IN_ADDR,
            )

            fc06(
                ser,
                driver_id,
                NET_IN_ADDR,
                net_in | servo_masks[driver_id],
            )

        # IMPORTANT:
        # 05-17 may be as low as 100 ms. Do not sleep here after enabling.
        # Start valid zero-RPM FC17 traffic immediately so the watchdog does not
        # trip before the intentional silence phase.
        print(
            f"\n=== ZERO-RPM TRAFFIC "
            f"({args.warmup_cycles} cycles @ {args.warmup_hz:.1f} Hz) ==="
        )

        period = 1.0 / args.warmup_hz

        # First FC17 immediately after enable.
        first_rows = fc17_zero_rpm(ser, ids)
        for driver_id in ids:
            row = first_rows[driver_id]
            print(
                f"ENABLED ID{driver_id}: "
                f"status={row['status']} alarm={row['alarm']} "
                f"rpm={row['rpm']:+d}"
            )
            if row["alarm"] != 0:
                raise RuntimeError(
                    f"ID{driver_id}: alarm immediately after enable"
                )
            if row["rpm"] != 0:
                raise RuntimeError(
                    f"ID{driver_id}: unexpected RPM after enable"
                )

        for index in range(args.warmup_cycles):
            loop_start = time.monotonic()

            rows = fc17_zero_rpm(
                ser,
                ids,
            )

            for driver_id in ids:
                row = rows[driver_id]

                if row["alarm"] != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: alarm before intentional silence"
                    )

                if row["rpm"] != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: unexpected RPM "
                        f"{row['rpm']} before intentional silence"
                    )

            remaining = period - (
                time.monotonic() - loop_start
            )

            if remaining > 0:
                time.sleep(remaining)

        print(
            f"\n=== INTENTIONAL RS485 SILENCE: "
            f"{args.silence_ms} ms ==="
        )
        print(
            "No serial read/write will occur during this interval."
        )

        time.sleep(args.silence_ms / 1000.0)

        print("\n=== AFTER SILENCE ===")

        passed = True

        for driver_id in ids:
            state = read_state(ser, driver_id)
            show_state("TRIPPED", driver_id, state)

            alarm_ok = state["alarm"] != 0
            rpm_ok = state["rpm"] == 0
            servo_cleared = (
                state["net_in"] & servo_masks[driver_id]
            ) == 0

            print(
                f"ID{driver_id}: "
                f"alarm_triggered={'PASS' if alarm_ok else 'FAIL'}; "
                f"rpm_zero={'PASS' if rpm_ok else 'FAIL'}; "
                f"SERVO-EN_cleared={'PASS' if servo_cleared else 'FAIL'}"
            )

            passed &= (
                alarm_ok
                and rpm_ok
                and servo_cleared
            )

        print("\n=== RECOVER WITH ALM-RST ===")

        recovery_ok = True

        for driver_id in ids:
            try:
                pulse_alarm_reset(
                    ser,
                    driver_id,
                    alm_rst_masks[driver_id],
                )

                state = read_state(
                    ser,
                    driver_id,
                )

                show_state(
                    "RECOVERED",
                    driver_id,
                    state,
                )

                clear_ok = state["alarm"] == 0
                servo_off = (
                    state["net_in"]
                    & servo_masks[driver_id]
                ) == 0

                print(
                    f"ID{driver_id}: "
                    f"alarm_clear={'PASS' if clear_ok else 'FAIL'}; "
                    f"SERVO-EN_off={'PASS' if servo_off else 'FAIL'}"
                )

                recovery_ok &= (
                    clear_ok
                    and servo_off
                )

            except Exception as exc:
                recovery_ok = False
                print(
                    f"ID{driver_id}: recovery failed: {exc}",
                    file=sys.stderr,
                )

        print("\n=== RESULT ===")

        if not passed:
            print(
                "FAIL: watchdog did not produce all expected safety effects."
            )
            sys.exit(2)

        if not recovery_ok:
            print(
                "WATCHDOG PASS, RECOVERY FAIL: "
                "alarm reset requires manual investigation."
            )
            sys.exit(3)

        print(
            "PASS: communication timeout triggered protection, "
            "RPM stayed zero, SERVO-EN was cleared, "
            "and ALM-RST recovery succeeded."
        )


if __name__ == "__main__":
    main()
