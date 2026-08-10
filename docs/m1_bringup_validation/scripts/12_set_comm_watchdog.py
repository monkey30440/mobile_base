#!/usr/bin/env python3
import argparse
import struct
import sys
import time

from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16

REG_TIMEOUT = 0x0510
REG_ERROR_COUNT = 0x0511
REG_FAILURE_ACTION = 0x0514
REG_CONFIGURATION = 0x0A27
REG_NET_IN = 0x1400
SERVO_MASK = 0x0080

def fc06(ser, slave, address, value):
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

def configure(ser, driver_id):
    fc06(ser, driver_id, REG_CONFIGURATION, 1)
    time.sleep(0.5)

def read_watchdog(ser, driver_id):
    return {
        "timeout_ms": fc03_one(ser, driver_id, REG_TIMEOUT),
        "error_count": fc03_one(ser, driver_id, REG_ERROR_COUNT),
        "failure_action": fc03_one(ser, driver_id, REG_FAILURE_ACTION),
    }

def print_watchdog(prefix, driver_id, values):
    print(
        f"{prefix} ID{driver_id}: "
        f"05-17={values['timeout_ms']} ms "
        f"05-18={values['error_count']} "
        f"05-21={values['failure_action']}"
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, required=True)
    parser.add_argument("--ids", required=True)
    parser.add_argument("--timeout-ms", type=int, default=100)
    parser.add_argument("--error-count", type=int, default=3)
    parser.add_argument("--failure-action", type=int, default=2)
    parser.add_argument("--serial-timeout", type=float, default=0.25)
    parser.add_argument("--arm", default="")
    args = parser.parse_args()

    if args.arm != "I_UNDERSTAND":
        sys.exit("Refusing parameter write. Re-run with --arm I_UNDERSTAND.")

    ids = [int(x) for x in args.ids.split(",")]
    if not ids or len(ids) != len(set(ids)):
        sys.exit("--ids must contain unique driver IDs")
    if not 1 <= args.timeout_ms <= 65535:
        sys.exit("--timeout-ms must be 1..65535")
    if not 1 <= args.error_count <= 10:
        sys.exit("--error-count must be 1..10")
    if args.failure_action not in (0, 1, 2):
        sys.exit("--failure-action must be 0, 1, or 2")

    target = {
        "timeout_ms": args.timeout_ms,
        "error_count": args.error_count,
        "failure_action": args.failure_action,
    }
    originals = {}

    with serial.Serial(
        args.port, args.baud,
        bytesize=8, parity="N", stopbits=1,
        timeout=args.serial_timeout,
    ) as ser:
        print("=== PRECHECK ===")
        for driver_id in ids:
            status = fc03_one(ser, driver_id, 0x0000)
            rpm = s16(fc03_one(ser, driver_id, 0x0002))
            alarm = fc03_one(ser, driver_id, 0x0003)
            net_in = fc03_one(ser, driver_id, REG_NET_IN)
            values = read_watchdog(ser, driver_id)
            originals[driver_id] = values

            print(
                f"ID{driver_id}: status={status} alarm={alarm} "
                f"rpm={rpm:+d} NET-IN=0x{net_in:04X}"
            )
            print_watchdog("ORIGINAL", driver_id, values)

            if alarm != 0:
                sys.exit(f"BLOCKED: ID{driver_id} has alarm={alarm}")
            if rpm != 0:
                sys.exit(f"BLOCKED: ID{driver_id} is moving, rpm={rpm}")
            if net_in & SERVO_MASK:
                sys.exit(
                    f"BLOCKED: ID{driver_id} SERVO-EN is ON "
                    f"(NET-IN=0x{net_in:04X})"
                )

        print(
            "\nTARGET: "
            f"05-17={target['timeout_ms']} ms "
            f"05-18={target['error_count']} "
            f"05-21={target['failure_action']}"
        )

        if all(originals[sid] == target for sid in ids):
            print("\nPASS: all requested drivers already match target.")
            return

        try:
            print("\n=== WRITE EEP PARAMETERS ===")
            for driver_id in ids:
                fc06(ser, driver_id, REG_TIMEOUT, target["timeout_ms"])
                fc06(ser, driver_id, REG_ERROR_COUNT, target["error_count"])
                fc06(ser, driver_id, REG_FAILURE_ACTION, target["failure_action"])
                print(
                    f"ID{driver_id}: wrote "
                    f"05-17={target['timeout_ms']}, "
                    f"05-18={target['error_count']}, "
                    f"05-21={target['failure_action']}"
                )

            print("\n=== CONFIGURATION ===")
            for driver_id in ids:
                configure(ser, driver_id)
                print(f"ID{driver_id}: Configuration complete")

            print("\n=== VERIFY ===")
            for driver_id in ids:
                values = read_watchdog(ser, driver_id)
                print_watchdog("VERIFY", driver_id, values)
                if values != target:
                    raise RuntimeError(
                        f"ID{driver_id}: verification mismatch "
                        f"got={values}, expected={target}"
                    )
                alarm = fc03_one(ser, driver_id, 0x0003)
                rpm = s16(fc03_one(ser, driver_id, 0x0002))
                if alarm != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: alarm after configuration: {alarm}"
                    )
                if rpm != 0:
                    raise RuntimeError(
                        f"ID{driver_id}: unexpected RPM after configuration: {rpm}"
                    )

        except Exception:
            print("\n=== FAILURE: ATTEMPT ROLLBACK ===", file=sys.stderr)
            for driver_id in ids:
                original = originals[driver_id]
                try:
                    fc06(ser, driver_id, REG_TIMEOUT, original["timeout_ms"])
                    fc06(ser, driver_id, REG_ERROR_COUNT, original["error_count"])
                    fc06(ser, driver_id, REG_FAILURE_ACTION, original["failure_action"])
                    configure(ser, driver_id)
                    restored = read_watchdog(ser, driver_id)
                    print_watchdog("RESTORED", driver_id, restored)
                except Exception as exc:
                    print(
                        f"ID{driver_id}: ROLLBACK FAILED: {exc}",
                        file=sys.stderr,
                    )
            raise

        print(
            "\nPASS: communication watchdog parameters "
            "written and verified on all requested drivers."
        )

if __name__ == "__main__":
    main()
