#!/usr/bin/env python3
"""
M1 gear-ratio bring-up test.

Purpose:
  Verify the mechanical relationship:
      motor revolutions / wheel revolutions ~= gear ratio

This script does NOT infer wheel revolutions electronically.
It moves exactly a requested number of MOTOR revolutions using M1 encoder feedback,
then the operator visually checks how many WHEEL revolutions occurred.

Example for nominal 20:1:
  --motor-revs 20
  Expected visual result: wheel ~= 1 revolution.

Safety lifecycle:
  1. Validate both drivers are stationary and alarm-free.
  2. Read encoder resolution and position format from the selected driver.
  3. Require position format 02-14 = 0 (Index(turns) + pulse).
  4. Enable both drivers while preserving unrelated NET-IN bits.
  5. Send zero-RPM FC17 sanity command.
  6. Run ONE selected motor at low RPM.
  7. Stop when encoder delta reaches requested motor revolutions.
  8. Send zero RPM and confirm stop.
  9. Restore original NET-IN values.

IMPORTANT:
  --ids means RIGHT_ID,LEFT_ID.
  Keep wheels lifted and E-stop/STO immediately available.
"""

import argparse
import struct
import time
import sys

from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16


CMD_JG = 0x0001
NET_IN_ADDR = 0x1400
QUADRATURE_FACTOR = 4


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


def driver_bitmask(driver_ids):
    mask = 0
    for driver_id in driver_ids:
        if not 1 <= driver_id <= 8:
            raise ValueError("Multi-drive 2.0 IDs must be in range 1..8")
        mask |= 1 << (driver_id - 1)
    return mask


def fc17_jg(ser, driver_ids, rpms):
    """
    Multi-drive 2.0:
      Read Index 0..6
      Write Index 8 = Multi-drive Lite command
      Write Index 9 = Multi-drive Lite Data1 (signed RPM)

    Per selected driver, response:
      Data0..Data6 + Error_Check
    """
    ordered_ids = sorted(driver_ids)
    mask = driver_bitmask(ordered_ids)

    read_addr = 0xF000 | mask
    read_count = len(ordered_ids) * 8

    write_addr = 0xF800 | mask
    write_words = []
    for driver_id in ordered_ids:
        write_words += [CMD_JG, rpms[driver_id] & 0xFFFF]

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
        raise RuntimeError(f"unexpected Multi-drive ID 0x{head[0]:02X}")

    if head[1] == 0x97:
        tail = read_exact(ser, 3)
        pkt = head + tail
        check_crc(pkt)
        raise RuntimeError(f"FC17 exception 0x{pkt[2]:02X}")

    if head[1] != 0x17:
        raise RuntimeError(f"unexpected FC 0x{head[1]:02X}")

    tail = read_exact(ser, head[2] + 2)
    pkt = head + tail
    check_crc(pkt)

    words = list(
        struct.unpack(">" + "H" * (head[2] // 2), pkt[3:-2])
    )

    expected = len(ordered_ids) * 8
    if len(words) != expected:
        raise RuntimeError(
            f"expected {expected} response words, got {len(words)}"
        )

    rows = {}
    for i, driver_id in enumerate(ordered_ids):
        w = words[i * 8 : (i + 1) * 8]
        rows[driver_id] = {
            "status": w[0],
            "alarm": w[1],
            "rpm": s16(w[2]),
            "bus_v_raw": w[3],
            "current_raw": w[4],
            "pos_turns": s16(w[5]),
            "pos_pulse": w[6],
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


class PositionTracker:
    """
    Convert 02-14 = 0:
        signed int16 turns + pulse-within-turn
    into continuous motor counts.

    The raw turns field can wrap from +32767 to -32768 or vice versa.
    """

    TURNS_RANGE = 65536
    TURNS_HALF_RANGE = 32768

    def __init__(self, counts_per_motor_rev):
        self.counts_per_motor_rev = counts_per_motor_rev
        self.last_raw_turns = None
        self.turn_offset = 0

    def update(self, raw_turns, pulse):
        if self.last_raw_turns is not None:
            delta = raw_turns - self.last_raw_turns
            if delta < -self.TURNS_HALF_RANGE:
                self.turn_offset += self.TURNS_RANGE
            elif delta > self.TURNS_HALF_RANGE:
                self.turn_offset -= self.TURNS_RANGE

        self.last_raw_turns = raw_turns
        continuous_turns = raw_turns + self.turn_offset

        return (
            continuous_turns * self.counts_per_motor_rev
            + int(pulse)
        )


def show_row(label, driver_id, row):
    print(
        f"{label} ID{driver_id}: "
        f"status={row['status']} alarm={row['alarm']} "
        f"rpm={row['rpm']:+d} "
        f"pos={row['pos_turns']}:{row['pos_pulse']} "
        f"current_raw={row['current_raw']}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Verify M1 mechanical gear ratio using encoder motor revolutions"
    )
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, required=True)
    parser.add_argument(
        "--ids",
        required=True,
        help="RIGHT_ID,LEFT_ID; e.g. 1,2",
    )
    parser.add_argument(
        "--wheel",
        choices=("right", "left"),
        required=True,
        help="which wheel/motor to move",
    )
    parser.add_argument(
        "--rpm",
        type=int,
        default=80,
        help="signed motor RPM. For ratio verification direction does not matter.",
    )
    parser.add_argument(
        "--motor-revs",
        type=float,
        default=20.0,
        help="target MOTOR revolutions, default 20",
    )
    parser.add_argument(
        "--nominal-ratio",
        type=float,
        default=20.0,
        help="nominal ratio used only to print expected wheel revolutions",
    )
    parser.add_argument("--hz", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=0.25)
    parser.add_argument("--settle", type=float, default=0.3)
    parser.add_argument(
        "--servo-mask",
        type=lambda x: int(x, 0),
        default=0x0080,
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=30.0,
        help="hard motion timeout even if encoder target is not reached",
    )
    parser.add_argument("--arm", default="")
    args = parser.parse_args()

    driver_ids = [int(x) for x in args.ids.split(",")]
    if len(driver_ids) != 2:
        sys.exit("--ids must be exactly RIGHT_ID,LEFT_ID")

    right_id, left_id = driver_ids
    if right_id == left_id:
        sys.exit("RIGHT_ID and LEFT_ID must differ")

    selected_id = right_id if args.wheel == "right" else left_id
    other_id = left_id if args.wheel == "right" else right_id

    if args.arm != "I_UNDERSTAND":
        sys.exit(
            "Refusing motion. Re-run with --arm I_UNDERSTAND "
            "after wheels are lifted and E-stop/STO is ready."
        )

    if args.rpm == 0:
        sys.exit("--rpm must be non-zero")

    if abs(args.rpm) > 300:
        sys.exit("Bring-up safety limit: |rpm| <= 300")

    if args.motor_revs <= 0 or args.motor_revs > 100:
        sys.exit("--motor-revs must be >0 and <=100")

    if args.nominal_ratio <= 0:
        sys.exit("--nominal-ratio must be >0")

    if args.hz <= 0 or args.hz > 50:
        sys.exit("--hz must be >0 and <=50")

    if args.max_seconds <= 0 or args.max_seconds > 120:
        sys.exit("--max-seconds must be >0 and <=120")

    expected_wheel_revs = args.motor_revs / args.nominal_ratio

    print("=== ARMED GEAR-RATIO TEST ===")
    print(f"port={args.port} baud={args.baud}")
    print(
        f"RIGHT ID{right_id}, LEFT ID{left_id}; "
        f"selected {args.wheel.upper()} = ID{selected_id}"
    )
    print(f"command RPM: {args.rpm:+d}")
    print(f"target motor revolutions: {args.motor_revs:.4f}")
    print(f"nominal gear ratio: {args.nominal_ratio:.4f}:1")
    print(
        f"VISUAL EXPECTATION: wheel should rotate about "
        f"{expected_wheel_revs:.4f} revolution(s)"
    )
    print(
        "Make a visible wheel reference mark before continuing. "
        "Ctrl-C/exception will attempt STOP and NET-IN restore."
    )

    originals = {}

    with serial.Serial(
        args.port,
        args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    ) as ser:

        print("\n[1] Read selected-driver encoder configuration")
        encoder_resolution = fc03_one(ser, selected_id, 0x0105)
        position_format = fc03_one(ser, selected_id, 0x020D)

        print(
            f"ID{selected_id} 01-06 encoder resolution = "
            f"{encoder_resolution} pulse/rev"
        )
        print(
            f"ID{selected_id} 02-14 position format = "
            f"{position_format}"
        )

        if encoder_resolution <= 0:
            sys.exit("BLOCKED: encoder resolution is zero")

        if position_format != 0:
            sys.exit(
                "BLOCKED: this test requires 02-14 = 0 "
                "(Index(turns) + pulse)"
            )

        counts_per_motor_rev = (
            encoder_resolution * QUADRATURE_FACTOR
        )
        target_counts = round(
            args.motor_revs * counts_per_motor_rev
        )

        print(
            f"counts_per_motor_rev = {counts_per_motor_rev}"
        )
        print(f"target encoder delta = {target_counts} counts")

        print("\n[2] Preflight")
        for driver_id in driver_ids:
            state = read_basic_state(ser, driver_id)
            originals[driver_id] = state["net_in"]

            print(
                f"ID{driver_id}: status={state['status']} "
                f"alarm={state['alarm']} rpm={state['rpm']:+d} "
                f"NET-IN=0x{state['net_in']:04X}"
            )

            if state["alarm"] != 0:
                sys.exit(
                    f"BLOCKED: ID{driver_id} alarm={state['alarm']}"
                )

            if state["rpm"] != 0:
                sys.exit(
                    f"BLOCKED: ID{driver_id} RPM is non-zero"
                )

        stopped = {right_id: 0, left_id: 0}
        motion = {right_id: 0, left_id: 0}
        motion[selected_id] = args.rpm

        try:
            print("\n[3] SERVO-EN ON")
            for driver_id in driver_ids:
                fc06(
                    ser,
                    driver_id,
                    NET_IN_ADDR,
                    originals[driver_id] | args.servo_mask,
                )
                time.sleep(0.03)

            time.sleep(args.settle)

            for driver_id in driver_ids:
                state = read_basic_state(ser, driver_id)
                print(
                    f"ID{driver_id}: status={state['status']} "
                    f"alarm={state['alarm']} rpm={state['rpm']:+d} "
                    f"NET-IN=0x{state['net_in']:04X}"
                )

                if state["alarm"] != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: alarm after enable"
                    )
                if state["rpm"] != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: unexpected RPM after enable"
                    )
                if state["status"] == 6:
                    raise RuntimeError(
                        f"ID{driver_id}: still WAIT/INHIBIT"
                    )

            print("\n[4] FC17 zero-RPM sanity")
            rows = fc17_jg(ser, driver_ids, stopped)
            for driver_id in driver_ids:
                show_row("", driver_id, rows[driver_id])

            tracker = PositionTracker(counts_per_motor_rev)
            selected = rows[selected_id]
            start_counts = tracker.update(
                selected["pos_turns"],
                selected["pos_pulse"],
            )

            print(
                f"start continuous motor counts = {start_counts}"
            )

            print("\n[5] Motion until encoder target")
            period = 1.0 / args.hz
            deadline = time.monotonic() + args.max_seconds
            final_counts = start_counts
            reached = False

            while time.monotonic() < deadline:
                loop_start = time.monotonic()

                rows = fc17_jg(ser, driver_ids, motion)

                selected = rows[selected_id]
                other = rows[other_id]

                if selected["alarm"] != 0:
                    raise RuntimeError(
                        f"selected ID{selected_id}: "
                        f"alarm={selected['alarm']}"
                    )

                if other["alarm"] != 0:
                    raise RuntimeError(
                        f"other ID{other_id}: "
                        f"alarm={other['alarm']}"
                    )

                # Other motor must remain stopped.
                if abs(other["rpm"]) > 2:
                    raise RuntimeError(
                        f"other ID{other_id} unexpectedly moving: "
                        f"rpm={other['rpm']}"
                    )

                final_counts = tracker.update(
                    selected["pos_turns"],
                    selected["pos_pulse"],
                )

                delta_counts = final_counts - start_counts
                abs_delta = abs(delta_counts)
                motor_revs = (
                    delta_counts / counts_per_motor_rev
                )

                print(
                    f"ID{selected_id}: rpm={selected['rpm']:+d} "
                    f"pos={selected['pos_turns']}:{selected['pos_pulse']} "
                    f"delta={delta_counts:+d} counts "
                    f"motor_revs={motor_revs:+.4f}"
                )

                if abs_delta >= target_counts:
                    reached = True
                    break

                remaining = period - (
                    time.monotonic() - loop_start
                )
                if remaining > 0:
                    time.sleep(remaining)

            if not reached:
                raise RuntimeError(
                    f"encoder target was not reached within "
                    f"{args.max_seconds:.1f}s"
                )

        finally:
            print("\n[6] STOP both motors")
            stop_confirmed = False
            for attempt in range(5):
                try:
                    rows = fc17_jg(ser, driver_ids, stopped)
                    for driver_id in driver_ids:
                        show_row("", driver_id, rows[driver_id])

                    if all(
                        abs(row["rpm"]) == 0
                        for row in rows.values()
                    ):
                        stop_confirmed = True
                        break
                except Exception as exc:
                    print(
                        f"STOP attempt {attempt + 1}/5 failed: {exc}",
                        file=sys.stderr,
                    )

                time.sleep(0.1)

            if not stop_confirmed:
                print(
                    "WARNING: stop was not confirmed. "
                    "Use hardware E-stop/STO immediately.",
                    file=sys.stderr,
                )

            print("\n[7] Restore original NET-IN")
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
                    print(
                        f"ID{driver_id}: status={state['status']} "
                        f"alarm={state['alarm']} rpm={state['rpm']:+d} "
                        f"NET-IN=0x{state['net_in']:04X}"
                    )
                except Exception as exc:
                    print(
                        f"ID{driver_id}: final read failed: {exc}",
                        file=sys.stderr,
                    )

            if restore_errors:
                raise RuntimeError(
                    "NET-IN restore failure. "
                    "Use hardware E-stop/STO and inspect the bus."
                )

        delta_counts = final_counts - start_counts
        measured_motor_revs = (
            delta_counts / counts_per_motor_rev
        )

        print("\n=== RESULT ===")
        print(
            f"encoder delta      = {delta_counts:+d} counts"
        )
        print(
            f"measured motor rev = {measured_motor_revs:+.6f}"
        )
        print(
            f"nominal wheel rev  = "
            f"{abs(measured_motor_revs) / args.nominal_ratio:.6f} "
            f"(if ratio really is {args.nominal_ratio}:1)"
        )
        print()
        print(
            "VISUAL CHECK REQUIRED:"
        )
        print(
            f"Did the {args.wheel} wheel rotate approximately "
            f"{expected_wheel_revs:.4f} revolution(s)?"
        )
        print(
            "Record the observed wheel revolutions, then calculate:"
        )
        print(
            "  measured_gear_ratio = "
            "abs(measured_motor_revs) / observed_wheel_revolutions"
        )


if __name__ == "__main__":
    main()
