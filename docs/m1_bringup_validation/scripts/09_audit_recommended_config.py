#!/usr/bin/env python3
"""
Read-only audit of the M1 settings chosen for the ROS 2 mobile-base architecture.

This does not blindly accept current hardware values. It compares them against
the intended contract and reports PASS/WARN/BLOCKER.
"""
import argparse, sys
from m1_modbus import serial, fc03_one

BAUD_SELECTOR={9600:0,19200:1,38400:2,57600:3,115200:4,230400:5}

def item(label, actual, expected=None, pred=None, severity="BLOCKER", note=""):
    good = (actual==expected) if pred is None else pred(actual)
    tag = "PASS" if good else severity
    exp = f" expected={expected}" if expected is not None else ""
    print(f"{tag:7s} {label:34s} actual={actual}{exp}" + (f"  # {note}" if note else ""))
    return good, tag

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port",default="/dev/ttyUSB0")
    ap.add_argument("--baud",type=int,required=True)
    ap.add_argument("--ids",required=True,help="RIGHT_ID,LEFT_ID")
    a=ap.parse_args()
    ids=[int(x) for x in a.ids.split(",")]
    if len(ids)!=2 or len(set(ids))!=2: sys.exit("--ids must be RIGHT_ID,LEFT_ID")
    if a.baud not in BAUD_SELECTOR: sys.exit("unsupported baud for audit")
    right,left=ids

    blockers=0; warnings=0
    with serial.Serial(a.port,a.baud,bytesize=8,parity="N",stopbits=1,timeout=.25) as ser:
        for sid,side in ((right,"RIGHT"),(left,"LEFT")):
            print(f"\n===== {side} Driver ID {sid} =====")
            checks=[
                ("01-10 lifecycle enable", fc03_one(ser,sid,0x0109), 1, None, "BLOCKER",
                 "SERVO-ON controlled lifecycle"),
                ("01-11 control mode", fc03_one(ser,sid,0x010A), 0, None, "BLOCKER", "Speed closed-loop"),
                ("01-12 speed source", fc03_one(ser,sid,0x010B), 4, None, "BLOCKER", "Multi-drive Lite JG"),
                ("02-14 position format", fc03_one(ser,sid,0x020D), 1, None, "BLOCKER", "signed 32-bit Step"),
                ("02-15 RPM refresh", fc03_one(ser,sid,0x020E), 3, None, "WARN", "100 Hz monitor refresh"),
                ("09-18 protocol", fc03_one(ser,sid,0x0911), 0, None, "BLOCKER", "Modbus RTU"),
                ("09-19 driver ID", fc03_one(ser,sid,0x0912), sid, None, "BLOCKER", "must match deployment mapping"),
                ("09-20 baud selector", fc03_one(ser,sid,0x0913), BAUD_SELECTOR[a.baud], None, "BLOCKER", str(a.baud)),
                ("09-21 RTU C3.5", fc03_one(ser,sid,0x0914), 0, None, "WARN", "standard 1.75 ms"),
                ("09-26 MD2 mapping", fc03_one(ser,sid,0x0919), 0, None, "BLOCKER", "driver assumes mapping 0"),
            ]
            for label,actual,expected,pred,severity,note in checks:
                good,tag=item(label,actual,expected,pred,severity,note)
                if not good:
                    blockers += tag=="BLOCKER"; warnings += tag=="WARN"

            # Safety settings are intentionally policy checks, not exact values yet.
            v=fc03_one(ser,sid,0x0510)
            good,tag=item("05-17 comm timeout",v,pred=lambda x:x>0,severity="BLOCKER",
                          note="must be >0; exact ms chosen after timing test")
            if not good: blockers+=1
            v=fc03_one(ser,sid,0x0511)
            good,tag=item("05-18 RS485 error count",v,pred=lambda x:1<=x<=10,severity="WARN",
                          note="0 disables protection; exact count is policy")
            if not good: warnings+=1
            v=fc03_one(ser,sid,0x0514)
            good,tag=item("05-21 comm failure action",v,2,None,"WARN",
                          "recommended: alarm stop + clear remote I/O")
            if not good: warnings+=1

    print("\n===== AUDIT RESULT =====")
    print(f"blockers={blockers} warnings={warnings}")
    if blockers:
        sys.exit(2)

if __name__=="__main__":
    main()
