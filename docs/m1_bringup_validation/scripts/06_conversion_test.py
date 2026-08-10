#!/usr/bin/env python3
"""
Pure math verification for the M1 <-> ros2_control conversions.

NO serial access.
NO RS485.
NO motor commands.

Verified inputs used by default:
  gear_ratio = 20.0
  encoder_ppr = 2500 pulse/rev
  quadrature_factor = 4
  left_sign = +1
  right_sign = -1

Conventions:
  ROS wheel velocity > 0  => robot-forward wheel direction
  ROS wheel position increases in that same positive direction.

M1:
  command/feedback RPM sign is motor-native sign.
  position format 02-14=0 is Index(turns) + pulse.
"""

import argparse
import math
import sys


def wheel_rad_s_to_motor_rpm(wheel_rad_s, gear_ratio, sign):
    return (
        wheel_rad_s
        * 60.0
        / (2.0 * math.pi)
        * gear_ratio
        * sign
    )


def motor_rpm_to_wheel_rad_s(motor_rpm, gear_ratio, sign):
    return (
        motor_rpm
        * (2.0 * math.pi)
        / 60.0
        / gear_ratio
        * sign
    )


def raw_position_to_motor_counts(
    index_turns,
    pulse,
    counts_per_motor_rev,
):
    return (
        int(index_turns) * counts_per_motor_rev
        + int(pulse)
    )


def motor_counts_to_wheel_rad(
    motor_counts,
    counts_per_motor_rev,
    gear_ratio,
    sign,
):
    return (
        motor_counts
        * (2.0 * math.pi)
        / counts_per_motor_rev
        / gear_ratio
        * sign
    )


def wheel_rad_to_motor_counts(
    wheel_rad,
    counts_per_motor_rev,
    gear_ratio,
    sign,
):
    return (
        wheel_rad
        / (2.0 * math.pi)
        * counts_per_motor_rev
        * gear_ratio
        * sign
    )


def almost_equal(a, b, tol=1e-9):
    return abs(a - b) <= tol


def check(label, condition, detail):
    if condition:
        print(f"PASS {label}: {detail}")
        return True

    print(f"FAIL {label}: {detail}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Pure M1/ros2_control conversion verification"
    )
    parser.add_argument("--gear-ratio", type=float, default=20.0)
    parser.add_argument("--encoder-ppr", type=int, default=2500)
    parser.add_argument("--quadrature", type=int, default=4)
    parser.add_argument("--left-sign", type=int, default=1)
    parser.add_argument("--right-sign", type=int, default=-1)
    args = parser.parse_args()

    if args.gear_ratio <= 0:
        sys.exit("gear ratio must be > 0")

    if args.encoder_ppr <= 0:
        sys.exit("encoder PPR must be > 0")

    if args.quadrature <= 0:
        sys.exit("quadrature factor must be > 0")

    if args.left_sign not in (-1, 1):
        sys.exit("left sign must be -1 or +1")

    if args.right_sign not in (-1, 1):
        sys.exit("right sign must be -1 or +1")

    counts_per_motor_rev = (
        args.encoder_ppr * args.quadrature
    )
    counts_per_wheel_rev = (
        counts_per_motor_rev * args.gear_ratio
    )

    print("=== VERIFIED-CONVERSION MODEL ===")
    print(f"gear_ratio             = {args.gear_ratio}")
    print(f"encoder_ppr            = {args.encoder_ppr}")
    print(f"quadrature_factor      = {args.quadrature}")
    print(
        f"counts_per_motor_rev   = {counts_per_motor_rev}"
    )
    print(
        f"counts_per_wheel_rev   = {counts_per_wheel_rev}"
    )
    print(f"left_sign              = {args.left_sign:+d}")
    print(f"right_sign             = {args.right_sign:+d}")

    ok = True

    print("\n[1] ROS wheel velocity -> M1 motor RPM")

    for wheel_name, sign in (
        ("left", args.left_sign),
        ("right", args.right_sign),
    ):
        for wheel_rad_s in (0.0, 1.0, -1.0, 2.5):
            rpm = wheel_rad_s_to_motor_rpm(
                wheel_rad_s,
                args.gear_ratio,
                sign,
            )
            recovered = motor_rpm_to_wheel_rad_s(
                rpm,
                args.gear_ratio,
                sign,
            )

            print(
                f"{wheel_name:5s}: "
                f"wheel={wheel_rad_s:+.6f} rad/s "
                f"-> motor={rpm:+.6f} RPM "
                f"-> wheel={recovered:+.6f} rad/s"
            )

            ok &= check(
                f"{wheel_name} velocity round-trip "
                f"{wheel_rad_s:+.3f}",
                almost_equal(wheel_rad_s, recovered),
                f"{recovered:+.9f} rad/s",
            )

    print("\n[2] Known 1 rad/s expected command")

    expected_abs_rpm = (
        60.0
        / (2.0 * math.pi)
        * args.gear_ratio
    )

    left_1 = wheel_rad_s_to_motor_rpm(
        1.0,
        args.gear_ratio,
        args.left_sign,
    )
    right_1 = wheel_rad_s_to_motor_rpm(
        1.0,
        args.gear_ratio,
        args.right_sign,
    )

    print(f"|motor RPM| for 1 rad/s = {expected_abs_rpm:.9f}")
    print(f"LEFT  ROS +1 rad/s -> {left_1:+.9f} RPM")
    print(f"RIGHT ROS +1 rad/s -> {right_1:+.9f} RPM")

    ok &= check(
        "left +1 rad/s sign",
        left_1 > 0,
        f"{left_1:+.6f} RPM",
    )
    ok &= check(
        "right +1 rad/s sign",
        right_1 < 0,
        f"{right_1:+.6f} RPM",
    )

    print("\n[3] M1 Index+pulse -> motor counts")

    position_cases = (
        (0, 0, 0),
        (0, 9999, 9999),
        (1, 0, 10000),
        (1, 3207, 13207),
        (-1, 9999, -1),
        (-2, 5000, -15000),
    )

    for idx, pulse, expected in position_cases:
        counts = raw_position_to_motor_counts(
            idx,
            pulse,
            counts_per_motor_rev,
        )

        ok &= check(
            f"position {idx}:{pulse}",
            counts == expected,
            f"{counts} counts",
        )

    print("\n[4] Motor counts -> ROS wheel position")

    one_wheel_rev_counts = counts_per_wheel_rev

    left_pos = motor_counts_to_wheel_rad(
        one_wheel_rev_counts,
        counts_per_motor_rev,
        args.gear_ratio,
        args.left_sign,
    )
    right_pos = motor_counts_to_wheel_rad(
        one_wheel_rev_counts,
        counts_per_motor_rev,
        args.gear_ratio,
        args.right_sign,
    )

    print(
        f"{one_wheel_rev_counts:.0f} motor counts "
        f"= nominal 1 wheel revolution"
    )
    print(
        f"LEFT  feedback -> {left_pos:+.9f} rad"
    )
    print(
        f"RIGHT feedback -> {right_pos:+.9f} rad"
    )

    ok &= check(
        "left one-wheel-rev",
        almost_equal(left_pos, 2.0 * math.pi),
        f"{left_pos:+.9f} rad",
    )
    ok &= check(
        "right one-wheel-rev sign",
        almost_equal(right_pos, -2.0 * math.pi),
        f"{right_pos:+.9f} rad",
    )

    print("\n[5] Position round-trip")

    for wheel_name, sign in (
        ("left", args.left_sign),
        ("right", args.right_sign),
    ):
        for wheel_rad in (
            0.0,
            0.5,
            2.0 * math.pi,
            -2.0 * math.pi,
            12.345,
        ):
            counts = wheel_rad_to_motor_counts(
                wheel_rad,
                counts_per_motor_rev,
                args.gear_ratio,
                sign,
            )
            recovered = motor_counts_to_wheel_rad(
                counts,
                counts_per_motor_rev,
                args.gear_ratio,
                sign,
            )

            print(
                f"{wheel_name:5s}: "
                f"wheel={wheel_rad:+.9f} rad "
                f"-> counts={counts:+.6f} "
                f"-> wheel={recovered:+.9f} rad"
            )

            ok &= check(
                f"{wheel_name} position round-trip",
                almost_equal(wheel_rad, recovered),
                f"{recovered:+.9f} rad",
            )

    print("\n[6] ros2_control-facing constants")
    print(
        "motor_rpm_per_wheel_rad_s = "
        f"{60.0 / (2.0 * math.pi) * args.gear_ratio:.12f}"
    )
    print(
        "wheel_rad_s_per_motor_rpm = "
        f"{(2.0 * math.pi) / 60.0 / args.gear_ratio:.12f}"
    )
    print(
        "wheel_rad_per_motor_count = "
        f"{(2.0 * math.pi) / counts_per_motor_rev / args.gear_ratio:.12f}"
    )

    print("\n=== RESULT ===")
    if ok:
        print("PASS: all conversion checks passed")
        return

    print("FAIL: one or more conversion checks failed")
    sys.exit(1)


if __name__ == "__main__":
    main()
