#!/usr/bin/env python3
"""
Safe staged M1 motor test.

Lifecycle:
  1. Read and validate both drivers are alarm-free and stationary.
  2. Enable SERVO-EN on both drivers by setting only the configured NET-IN bit.
  3. Confirm both leave WAIT/INHIBIT and remain at zero RPM.
  4. Use Multi-drive 2.0 FC17 to send JG + RPM while reading feedback.
  5. Send zero RPM repeatedly and confirm stop.
  6. Restore each driver's original NET-IN value (SERVO-EN OFF if it was OFF).

Safety gates:
  - explicit --arm I_UNDERSTAND
  - |RPM| <= 300
  - duration <= 5 s
  - abort on active alarm
  - finally block always attempts STOP then NET-IN restore

IMPORTANT:
  --ids is RIGHT_ID,LEFT_ID.
"""

import argparse
import struct
import time
import sys

from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16


CMD_JG = 0x0001
NET_IN_ADDR = 0x1400


def fc06(ser, slave, address, value):
    ser.reset_input_buffer()
    req = frame(struct.pack(">BBHH", slave, 0x06, address, value & 0xFFFF))
    ser.write(req)
    ser.flush()

    resp = read_exact(ser, 8)
    check_crc(resp)
    if resp[:-2] != req[:-2]:
        raise RuntimeError(
            f"FC06 echo mismatch: req={req.hex(' ')} resp={resp.hex(' ')}"
        )


def bitmask(driver_ids):
    mask = 0
    for driver_id in driver_ids:
        if not 1 <= driver_id <= 8:
            raise ValueError("Multi-drive 2.0 IDs must be in range 1..8")
        mask |= 1 << (driver_id - 1)
    return mask


def fc17_jg(ser, driver_ids, rpms):
    """
    Verified/tested mapping target:
      Read index 0..6
      Write index 8 = Multi-drive Lite CMD
      Write index 9 = Multi-drive Lite Data1 (signed RPM)

    The FC17 response contains, per selected driver:
      Data0..Data6 + Error_Check
    """
    ordered_ids = sorted(driver_ids)
    mask = bitmask(ordered_ids)

    read_addr = 0xF000 | mask
    read_count = len(ordered_ids) * 8  # 7 data + 1 Error_Check per driver

    write_addr = 0xF800 | mask
    write_words = []
    for driver_id in ordered_ids:
        rpm = rpms[driver_id]
        write_words.extend([CMD_JG, rpm & 0xFFFF])

    write_count = len(write_words)

    body = struct.pack(
        ">BBHHHHB",
        0x65,
        0x17,
        read_addr,
        read_count,
        write_addr,
        write_count,
        write_count * 2,
    )
    body += struct.pack(">" + "H" * write_count, *write_words)

    req = frame(body)
    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()

    head = read_exact(ser, 3)
    if head[0] != 0x65:
        raise RuntimeError(f"unexpected Multi-drive group ID 0x{head[0]:02X}")

    if head[1] == 0x97:
        tail = read_exact(ser, 3)
        pkt = head + tail
        check_crc(pkt)
        raise RuntimeError(f"FC17 Modbus exception 0x{pkt[2]:02X}")

    if head[1] != 0x17:
        raise RuntimeError(f"unexpected FC 0x{head[1]:02X}")

    tail = read_exact(ser, head[2] + 2)
    pkt = head + tail
    check_crc(pkt)

    words = list(
        struct.unpack(">" + "H" * (head[2] // 2), pkt[3:-2])
    )

    expected_words = len(ordered_ids) * 8
    if len(words) != expected_words:
        raise RuntimeError(
            f"expected {expected_words} FC17 response words, got {len(words)}"
        )

    rows = {}
    for index, driver_id in enumerate(ordered_ids):
        w = words[index * 8 : (index + 1) * 8]
        rows[driver_id] = {
            "status": w[0],
            "alarm": w[1],
            "rpm": s16(w[2]),
            "bus_v_raw": w[3],
            "current_raw": w[4],
            "pos_hi": s16(w[5]),
            "pos_lo": w[6],
            "error_check": w[7],
        }
    return rows


def read_basic_state(ser, driver_id):
    return {
        "status": fc03_one(ser, driver_id, 0x0000),
        "rpm": s16(fc03_one(ser, driver_id, 0x0002)),
        "alarm": fc03_one(ser, driver_id, 0x0003),
        "net_in": fc03_one(ser, driver_id, NET_IN_ADDR),
    }


def show_basic(prefix, driver_id, state):
    print(
        f"{prefix} ID{driver_id}: "
        f"status={state['status']} alarm={state['alarm']} "
        f"rpm={state['rpm']:+d} NET-IN=0x{state['net_in']:04X}"
    )


def show_fc17(rows, right_id, left_id):
    for label, driver_id in (("RIGHT", right_id), ("LEFT", left_id)):
        r = rows[driver_id]
        print(
            f"{label} ID{driver_id}: "
            f"status={r['status']} alarm={r['alarm']} rpm={r['rpm']:+d} "
            f"pos_hi={r['pos_hi']} pos_lo={r['pos_lo']} "
            f"bus_raw={r['bus_v_raw']} current_raw={r['current_raw']} "
            f"errchk=0x{r['error_check']:04X}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Safe M1 Enable -> JG/RPM -> Stop -> Disable test"
    )
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, required=True)
    parser.add_argument(
        "--ids",
        required=True,
        help="RIGHT_ID,LEFT_ID; e.g. 1,2",
    )
    parser.add_argument("--right-rpm", type=int, default=0)
    parser.add_argument("--left-rpm", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument("--hz", type=float, default=10.0)
    parser.add_argument("--timeout", type=float, default=0.25)
    parser.add_argument("--settle", type=float, default=0.3)
    parser.add_argument(
        "--servo-mask",
        type=lambda x: int(x, 0),
        default=0x0080,
        help="SERVO-EN NET-IN mask; verified setup uses 0x0080 (NET-X7)",
    )
    parser.add_argument("--arm", default="")
    args = parser.parse_args()

    driver_ids = [int(x) for x in args.ids.split(",")]
    if len(driver_ids) != 2:
        sys.exit("--ids must contain exactly RIGHT_ID,LEFT_ID")

    right_id, left_id = driver_ids
    if right_id == left_id:
        sys.exit("RIGHT_ID and LEFT_ID must be different")

    if args.arm != "I_UNDERSTAND":
        sys.exit(
            "Refusing motor command. Re-run with --arm I_UNDERSTAND "
            "after wheels are lifted and E-stop/STO is ready."
        )

    if args.seconds <= 0 or args.seconds > 5.0:
        sys.exit("--seconds must be > 0 and <= 5")

    if args.hz <= 0 or args.hz > 50:
        sys.exit("--hz must be > 0 and <= 50 for this bring-up test")

    if max(abs(args.right_rpm), abs(args.left_rpm)) > 300:
        sys.exit("Bring-up safety limit: |RPM| <= 300")

    if args.right_rpm == 0 and args.left_rpm == 0:
        print("NOTE: both requested RPM values are zero; this will test lifecycle only.")

    requested = {
        right_id: args.right_rpm,
        left_id: args.left_rpm,
    }
    stopped = {
        right_id: 0,
        left_id: 0,
    }

    print("=== ARMED SAFE MOTOR TEST ===")
    print(f"port={args.port} baud={args.baud}")
    print(f"RIGHT ID{right_id}: {args.right_rpm:+d} RPM")
    print(f"LEFT  ID{left_id}: {args.left_rpm:+d} RPM")
    print(f"duration={args.seconds:.3f}s rate={args.hz:.1f}Hz")
    print("Ctrl-C / exception will still attempt STOP and NET-IN restore.")

    originals = {}

    with serial.Serial(
        args.port,
        args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    ) as ser:

        # Stage 1: preflight state
        print("\n[1] Preflight")
        for driver_id in driver_ids:
            state = read_basic_state(ser, driver_id)
            originals[driver_id] = state["net_in"]
            show_basic("BEFORE", driver_id, state)

            if state["alarm"] != 0:
                sys.exit(f"BLOCKED: ID{driver_id} has alarm {state['alarm']}")
            if state["rpm"] != 0:
                sys.exit(
                    f"BLOCKED: ID{driver_id} RPM is non-zero before test: {state['rpm']}"
                )

        try:
            # Stage 2: enable, preserving unrelated NET-IN bits
            print("\n[2] SERVO-EN ON")
            for driver_id in driver_ids:
                enabled_word = originals[driver_id] | args.servo_mask
                fc06(ser, driver_id, NET_IN_ADDR, enabled_word)
                time.sleep(0.03)

            time.sleep(args.settle)

            for driver_id in driver_ids:
                state = read_basic_state(ser, driver_id)
                show_basic("ENABLED", driver_id, state)

                if (state["net_in"] & args.servo_mask) == 0:
                    raise RuntimeError(f"ID{driver_id}: SERVO-EN bit did not turn ON")
                if state["alarm"] != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: alarm after enable: {state['alarm']}"
                    )
                if state["rpm"] != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: unexpected RPM after enable: {state['rpm']}"
                    )
                if state["status"] == 6:
                    raise RuntimeError(
                        f"ID{driver_id}: still WAIT/INHIBIT after SERVO-EN"
                    )

            # Stage 3: first explicit zero FC17
            print("\n[3] FC17 zero-RPM sanity check")
            rows = fc17_jg(ser, driver_ids, stopped)
            show_fc17(rows, right_id, left_id)
            for driver_id, row in rows.items():
                if row["alarm"] != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: alarm during zero-RPM FC17: {row['alarm']}"
                    )

            # Stage 4: commanded motion
            print("\n[4] Motion")
            deadline = time.monotonic() + args.seconds
            period = 1.0 / args.hz

            while time.monotonic() < deadline:
                start = time.monotonic()
                rows = fc17_jg(ser, driver_ids, requested)
                show_fc17(rows, right_id, left_id)

                for driver_id, row in rows.items():
                    if row["alarm"] != 0:
                        raise RuntimeError(
                            f"ID{driver_id}: alarm during motion: {row['alarm']}"
                        )

                remaining = period - (time.monotonic() - start)
                if remaining > 0:
                    time.sleep(remaining)

        finally:
            # Stage 5: stop before disable
            print("\n[5] STOP: command both motors to 0 RPM")
            stop_confirmed = False
            for attempt in range(3):
                try:
                    rows = fc17_jg(ser, driver_ids, stopped)
                    show_fc17(rows, right_id, left_id)
                    if all(abs(r["rpm"]) == 0 for r in rows.values()):
                        stop_confirmed = True
                        break
                except Exception as exc:
                    print(
                        f"STOP attempt {attempt + 1}/3 failed: {exc}",
                        file=sys.stderr,
                    )
                time.sleep(0.1)

            if not stop_confirmed:
                print(
                    "WARNING: zero-RPM feedback was not confirmed. "
                    "Proceeding to restore SERVO-EN state; "
                    "use hardware E-stop/STO immediately if motion persists.",
                    file=sys.stderr,
                )

            # Stage 6: always restore original NET-IN on each driver independently
            print("\n[6] Restore original NET-IN / SERVO-EN state")
            restore_errors = []
            for driver_id in driver_ids:
                try:
                    fc06(
                        ser,
                        driver_id,
                        NET_IN_ADDR,
                        originals.get(driver_id, 0),
                    )
                    time.sleep(0.05)
                except Exception as exc:
                    restore_errors.append((driver_id, exc))
                    print(
                        f"ID{driver_id}: NET-IN restore failed: {exc}",
                        file=sys.stderr,
                    )

            time.sleep(args.settle)

            for driver_id in driver_ids:
                try:
                    state = read_basic_state(ser, driver_id)
                    show_basic("RESTORED", driver_id, state)
                except Exception as exc:
                    print(
                        f"ID{driver_id}: final state read failed: {exc}",
                        file=sys.stderr,
                    )

            if restore_errors:
                raise RuntimeError(
                    "One or more drivers failed NET-IN restore. "
                    "Use hardware E-stop/STO and inspect the bus."
                )

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
