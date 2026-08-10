#!/usr/bin/env python3
"""Read-only dump of M1 communication error history registers 0x4800..0x4809."""
import argparse, sys
from m1_modbus import serial, fc03_one

ERRORS={
    0:"none/empty",
    0x84:"packet format or LRC/CRC-related communication error",
    0x85:"communication timeout",
    0x88:"unsupported/invalid command",
    0x8C:"setting out of range",
    0x8D:"command could not execute (possibly motor running)",
}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port",default="/dev/ttyUSB0")
    ap.add_argument("--baud",type=int,required=True)
    ap.add_argument("--ids",required=True)
    a=ap.parse_args()
    ids=[int(x) for x in a.ids.split(",")]
    with serial.Serial(a.port,a.baud,bytesize=8,parity="N",stopbits=1,timeout=.25) as ser:
        for sid in ids:
            print(f"\n===== Driver ID {sid} communication error history =====")
            for i in range(10):
                v=fc03_one(ser,sid,0x4800+i)
                print(f"{i+1:02d}: 0x{v:04X} ({v}) {ERRORS.get(v,'unknown')}")
if __name__=="__main__":
    main()
