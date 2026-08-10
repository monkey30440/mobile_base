#!/usr/bin/env python3
"""
Read-only verification for the M1 speed-command source and NET-X / SERVO-EN mapping.

Does NOT write any register.
"""

import argparse

from m1_modbus import serial, fc03_one


def main():
    parser = argparse.ArgumentParser(
        description="Read-only M1 01-12 and NET-X / SERVO-EN mapping verification"
    )
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, required=True)
    parser.add_argument("--ids", required=True, help="comma-separated IDs, e.g. 1,2")
    parser.add_argument("--timeout", type=float, default=0.2)
    args = parser.parse_args()

    driver_ids = [int(x) for x in args.ids.split(",")]

    with serial.Serial(
        args.port,
        args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=args.timeout,
    ) as ser:
        for driver_id in driver_ids:
            print(f"\n===== Driver ID {driver_id} =====")

            speed_method = fc03_one(ser, driver_id, 0x010B)  # 01-12
            print(f"01-12 speed control method = {speed_method}")

            servo_bits = []
            for i in range(15):
                addr = 0x0900 + i
                value = fc03_one(ser, driver_id, addr)
                marker = ""
                if value == 14:
                    servo_bits.append(i)
                    marker = "  <-- SERVO-EN"
                print(
                    f"09-{i + 1:02d} NET-X{i} function "
                    f"0x{addr:04X} = {value}{marker}"
                )

            logic = fc03_one(ser, driver_id, 0x090F)  # 09-16
            net_in = fc03_one(ser, driver_id, 0x1400)

            print(f"09-16 NET-X logic = 0x{logic:04X}")
            print(f"1400h NET-IN      = 0x{net_in:04X}")

            if speed_method == 4:
                print("CHECK 01-12: PASS (Multi-drive Lite)")
            else:
                print(
                    "CHECK 01-12: WARNING "
                    f"(expected 4 for the tested JG/RPM path, got {speed_method})"
                )

            if len(servo_bits) == 1:
                bit = servo_bits[0]
                print(
                    f"CHECK SERVO-EN mapping: PASS "
                    f"(NET-X{bit}, mask=0x{1 << bit:04X})"
                )
            elif not servo_bits:
                print("CHECK SERVO-EN mapping: FAIL (SERVO-EN function 14 not found)")
            else:
                print(
                    "CHECK SERVO-EN mapping: WARNING "
                    f"(SERVO-EN appears on multiple NET-X bits: {servo_bits})"
                )


if __name__ == "__main__":
    main()
