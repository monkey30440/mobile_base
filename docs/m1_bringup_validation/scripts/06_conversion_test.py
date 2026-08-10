#!/usr/bin/env python3
"""
Pure M1 <-> ros2_control math verification.

NO serial, NO RS485, NO motor command.

Default target architecture:
  02-14 = 1 (signed 32-bit position step)
  gear ratio = 20
  encoder PPR = 2500
  quadrature factor = 4
  left sign = +1
  right sign = -1
"""
import argparse
import math
import sys

def s32_from_words(hi, lo):
    u = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    return u - 0x100000000 if u & 0x80000000 else u

def words_from_s32(value):
    u = value & 0xFFFFFFFF
    return (u >> 16) & 0xFFFF, u & 0xFFFF

def wheel_rad_s_to_motor_rpm(w, ratio, sign):
    return w * 60.0 / (2.0 * math.pi) * ratio * sign

def motor_rpm_to_wheel_rad_s(rpm, ratio, sign):
    return rpm * (2.0 * math.pi) / 60.0 / ratio * sign

def motor_steps_to_wheel_rad(steps, counts_per_motor_rev, ratio, sign):
    return steps * (2.0 * math.pi) / counts_per_motor_rev / ratio * sign

def almost(a, b, tol=1e-9):
    return abs(a-b) <= tol

def check(name, cond, detail):
    print(("PASS " if cond else "FAIL ") + name + ": " + detail)
    return cond

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--gear-ratio",type=float,default=20.0)
    ap.add_argument("--encoder-ppr",type=int,default=2500)
    ap.add_argument("--quadrature",type=int,default=4)
    ap.add_argument("--left-sign",type=int,default=1)
    ap.add_argument("--right-sign",type=int,default=-1)
    a=ap.parse_args()
    if a.gear_ratio <= 0 or a.encoder_ppr <= 0 or a.quadrature <= 0:
        sys.exit("invalid conversion parameters")
    if a.left_sign not in (-1,1) or a.right_sign not in (-1,1):
        sys.exit("signs must be +/-1")

    cpm = a.encoder_ppr * a.quadrature
    cpw = cpm * a.gear_ratio
    ok=True

    print("=== FORMAT-1 CONVERSION MODEL ===")
    print(f"gear_ratio={a.gear_ratio}")
    print(f"counts_per_motor_rev={cpm}")
    print(f"counts_per_wheel_rev={cpw}")
    print(f"left_sign={a.left_sign:+d} right_sign={a.right_sign:+d}")

    print("\n[1] signed 32-bit high/low packing")
    cases=[0,1,-1,22500,-22500,200000,-200000,2147483647,-2147483648]
    for value in cases:
        hi,lo=words_from_s32(value)
        got=s32_from_words(hi,lo)
        ok &= check(str(value), got==value, f"hi=0x{hi:04X} lo=0x{lo:04X} -> {got}")

    print("\n[2] wheel velocity round-trip")
    for side,sign in (("left",a.left_sign),("right",a.right_sign)):
        for w in (0.0,1.0,-1.0,2.5):
            rpm=wheel_rad_s_to_motor_rpm(w,a.gear_ratio,sign)
            got=motor_rpm_to_wheel_rad_s(rpm,a.gear_ratio,sign)
            ok &= check(f"{side} {w:+.2f}", almost(w,got),
                        f"{w:+.6f} rad/s -> {rpm:+.6f} RPM -> {got:+.6f} rad/s")

    print("\n[3] one wheel revolution")
    left=motor_steps_to_wheel_rad(int(cpw),cpm,a.gear_ratio,a.left_sign)
    right=motor_steps_to_wheel_rad(int(cpw),cpm,a.gear_ratio,a.right_sign)
    ok &= check("left +200000 steps", almost(left,2*math.pi), f"{left:+.9f} rad")
    ok &= check("right +200000 native steps", almost(right,-2*math.pi), f"{right:+.9f} rad")

    print("\n[4] ros2_control-facing constants")
    print(f"motor_rpm_per_wheel_rad_s={60/(2*math.pi)*a.gear_ratio:.12f}")
    print(f"wheel_rad_s_per_motor_rpm={(2*math.pi)/60/a.gear_ratio:.12f}")
    print(f"wheel_rad_per_motor_step={(2*math.pi)/cpm/a.gear_ratio:.12f}")

    print("\n=== RESULT ===")
    if not ok:
        print("FAIL")
        sys.exit(1)
    print("PASS: all format-1 conversion checks passed")

if __name__=="__main__":
    main()
