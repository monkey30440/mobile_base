#!/usr/bin/env python3
"""
M1 SERVO-EN lifecycle test.

Writes ONLY NET-IN (0x1400) to toggle the discovered/configured SERVO-EN bit.
It does NOT send JG or RPM commands.

Default expected mapping from the verified setup:
  NET-X7 = SERVO-EN -> mask 0x0080
"""

import argparse
import struct
import time
import sys

from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16


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


def read_state(ser, driver_id):
    return {
        "status": fc03_one(ser, driver_id, 0x0000),
        "rpm": s16(fc03_one(ser, driver_id, 0x0002)),
        "alarm": fc03_one(ser, driver_id, 0x0003),
        "net_in": fc03_one(ser, driver_id, 0x1400),
    }


def show(label, state):
    print(label)
    print(f" status = {state['status']}")
    print(f" alarm  = {state['alarm']}")
    print(f" rpm    = {state['rpm']:+d}")
    print(f" NET-IN = 0x{state['net_in']:04X}")


def main():
    parser = argparse.ArgumentParser(description="M1 SERVO-EN enable/disable test")
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, required=True)
    parser.add_argument("--id", type=int, required=True, dest="driver_id")
    parser.add_argument(
        "--servo-mask",
        type=lambda x: int(x, 0),
        default=0x0080,
        help="SERVO-EN NET-IN mask, default 0x0080 (NET-X7)",
    )
    parser.add_argument("--timeout", type=float, default=0.2)
    parser.add_argument("--settle", type=float, default=0.3)
    parser.add_argument(
        "--arm",
        default="",
        help="must be I_UNDERSTAND because this test enables the drive",
    )
    args = parser.parse_args()

    if args.arm != "I_UNDERSTAND":
        sys.exit(
            "Refusing to enable drive. Re-run with --arm I_UNDERSTAND "
            "after wheels are lifted and E-stop/STO is ready."
        )

    with serial.Serial(
        args.port,
        args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    ) as ser:
        before = read_state(ser, args.driver_id)
        show("Before:", before)

        if before["alarm"] != 0:
            sys.exit("BLOCKED: driver has an active alarm")

        if before["rpm"] != 0:
            sys.exit("BLOCKED: motor RPM is not zero before enable test")

        # Preserve every unrelated NET-IN bit. Toggle only SERVO-EN.
        original_net_in = before["net_in"]
        enabled_net_in = original_net_in | args.servo_mask

        try:
            print("\nSERVO-EN ON")
            fc06(ser, args.driver_id, 0x1400, enabled_net_in)
            time.sleep(args.settle)

            enabled = read_state(ser, args.driver_id)
            show("", enabled)

            if (enabled["net_in"] & args.servo_mask) == 0:
                raise RuntimeError("SERVO-EN bit did not become ON")
            if enabled["rpm"] != 0:
                raise RuntimeError(
                    f"unexpected RPM after enable without motion command: {enabled['rpm']}"
                )
            if enabled["alarm"] != 0:
                raise RuntimeError(f"alarm after enable: {enabled['alarm']}")

        finally:
            print("\nSERVO-EN OFF / restore original NET-IN")
            try:
                fc06(ser, args.driver_id, 0x1400, original_net_in)
                time.sleep(args.settle)
                restored = read_state(ser, args.driver_id)
                show("", restored)
            except Exception as exc:
                print(
                    f"WARNING: failed to restore NET-IN: {exc}\n"
                    "Use hardware E-stop/STO if needed.",
                    file=sys.stderr,
                )
                raise


if __name__ == "__main__":
    main()
