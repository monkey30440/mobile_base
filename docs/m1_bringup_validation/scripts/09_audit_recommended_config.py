#!/usr/bin/env python3
"""
Read-only audit of M1 settings for the ROS 2 mobile-base architecture.

Profiles:
  development:
    Communication protection is intentionally disabled during bring-up:
      05-17 = 0
      05-18 = 0
      05-21 = 0

  deployment:
    Communication protection must be enabled:
      05-17 > 0
      05-18 = 1..10
      05-21 = 1 or 2

    Exact deployment values are NOT chosen by this script. They must be selected
    from timing/fault-injection evidence and then validated on the real system.
"""

import argparse
import sys

from m1_modbus import serial, fc03_one


BAUD_SELECTOR = {
    9600: 0,
    19200: 1,
    38400: 2,
    57600: 3,
    115200: 4,
    230400: 5,
}


def item(
    label,
    actual,
    expected=None,
    pred=None,
    severity="BLOCKER",
    note="",
):
    good = (
        actual == expected
        if pred is None
        else pred(actual)
    )
    tag = "PASS" if good else severity
    expected_text = (
        f" expected={expected}"
        if expected is not None
        else ""
    )
    note_text = f"  # {note}" if note else ""

    print(
        f"{tag:7s} {label:34s} "
        f"actual={actual}{expected_text}{note_text}"
    )
    return good, tag


def count_result(good, tag):
    if good:
        return 0, 0
    return (
        1 if tag == "BLOCKER" else 0,
        1 if tag == "WARN" else 0,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port",
        default="/dev/ttyUSB0",
    )
    parser.add_argument(
        "--baud",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--ids",
        required=True,
        help="RIGHT_ID,LEFT_ID",
    )
    parser.add_argument(
        "--profile",
        choices=("development", "deployment"),
        default="development",
        help="audit policy; default: development",
    )
    args = parser.parse_args()

    ids = [int(x) for x in args.ids.split(",")]

    if len(ids) != 2 or len(set(ids)) != 2:
        sys.exit("--ids must be RIGHT_ID,LEFT_ID")

    if args.baud not in BAUD_SELECTOR:
        sys.exit("unsupported baud for audit")

    right_id, left_id = ids
    blockers = 0
    warnings = 0

    print(f"PROFILE: {args.profile}")

    with serial.Serial(
        args.port,
        args.baud,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=0.25,
    ) as ser:
        for driver_id, side in (
            (right_id, "RIGHT"),
            (left_id, "LEFT"),
        ):
            print(
                f"\n===== {side} Driver ID "
                f"{driver_id} ====="
            )

            checks = [
                (
                    "01-10 lifecycle enable",
                    fc03_one(ser, driver_id, 0x0109),
                    1,
                    None,
                    "BLOCKER",
                    "SERVO-ON controlled lifecycle",
                ),
                (
                    "01-11 control mode",
                    fc03_one(ser, driver_id, 0x010A),
                    0,
                    None,
                    "BLOCKER",
                    "Speed closed-loop",
                ),
                (
                    "01-12 speed source",
                    fc03_one(ser, driver_id, 0x010B),
                    4,
                    None,
                    "BLOCKER",
                    "Multi-drive Lite JG",
                ),
                (
                    "02-14 position format",
                    fc03_one(ser, driver_id, 0x020D),
                    1,
                    None,
                    "BLOCKER",
                    "signed 32-bit Step",
                ),
                (
                    "02-15 RPM refresh",
                    fc03_one(ser, driver_id, 0x020E),
                    3,
                    None,
                    "WARN",
                    "100 Hz monitor refresh",
                ),
                (
                    "09-18 protocol",
                    fc03_one(ser, driver_id, 0x0911),
                    0,
                    None,
                    "BLOCKER",
                    "Modbus RTU",
                ),
                (
                    "09-19 driver ID",
                    fc03_one(ser, driver_id, 0x0912),
                    driver_id,
                    None,
                    "BLOCKER",
                    "must match deployment mapping",
                ),
                (
                    "09-20 baud selector",
                    fc03_one(ser, driver_id, 0x0913),
                    BAUD_SELECTOR[args.baud],
                    None,
                    "BLOCKER",
                    str(args.baud),
                ),
                (
                    "09-21 RTU C3.5",
                    fc03_one(ser, driver_id, 0x0914),
                    0,
                    None,
                    "WARN",
                    "standard 1.75 ms baseline",
                ),
                (
                    "09-26 MD2 mapping",
                    fc03_one(ser, driver_id, 0x0919),
                    0,
                    None,
                    "BLOCKER",
                    "driver assumes mapping 0",
                ),
            ]

            for check in checks:
                good, tag = item(*check)
                b, w = count_result(good, tag)
                blockers += b
                warnings += w

            timeout_ms = fc03_one(
                ser,
                driver_id,
                0x0510,
            )
            error_count = fc03_one(
                ser,
                driver_id,
                0x0511,
            )
            failure_action = fc03_one(
                ser,
                driver_id,
                0x0514,
            )

            if args.profile == "development":
                safety_checks = [
                    (
                        "05-17 comm timeout",
                        timeout_ms,
                        0,
                        None,
                        "BLOCKER",
                        "development only: watchdog intentionally disabled",
                    ),
                    (
                        "05-18 RS485 error count",
                        error_count,
                        0,
                        None,
                        "BLOCKER",
                        "development only: error-count protection disabled",
                    ),
                    (
                        "05-21 comm failure action",
                        failure_action,
                        0,
                        None,
                        "BLOCKER",
                        "development only: no automatic comm-failure action",
                    ),
                ]
            else:
                safety_checks = [
                    (
                        "05-17 comm timeout",
                        timeout_ms,
                        None,
                        lambda x: x > 0,
                        "BLOCKER",
                        "deployment requires watchdog; exact ms must be validated",
                    ),
                    (
                        "05-18 RS485 error count",
                        error_count,
                        None,
                        lambda x: 1 <= x <= 10,
                        "BLOCKER",
                        "deployment requires intentional non-zero policy",
                    ),
                    (
                        "05-21 comm failure action",
                        failure_action,
                        None,
                        lambda x: x in (1, 2),
                        "BLOCKER",
                        "0 is not accepted for deployment; validate recovery behavior",
                    ),
                ]

            for check in safety_checks:
                good, tag = item(*check)
                b, w = count_result(good, tag)
                blockers += b
                warnings += w

    print("\n===== AUDIT RESULT =====")
    print(
        f"profile={args.profile} "
        f"blockers={blockers} warnings={warnings}"
    )

    if args.profile == "development":
        print(
            "NOTE: PASS only means the system matches the "
            "intentional bring-up profile. Communication-loss "
            "protection is disabled and must be resolved before deployment."
        )
    else:
        print(
            "NOTE: value checks do not prove safe fault behavior. "
            "Deployment still requires real communication-loss "
            "and recovery validation."
        )

    if blockers:
        sys.exit(2)


if __name__ == "__main__":
    main()
