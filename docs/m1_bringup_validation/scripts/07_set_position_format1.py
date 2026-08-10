#!/usr/bin/env python3
"""
Safely set 02-14 position format to 1 on all requested drivers.

Writes EEP register 0x020D and runs Configuration (0x0A27=1).
Requires stopped, alarm-free, SERVO-EN OFF state.
If any write/verification fails, attempts to restore every driver's original value.
"""
import argparse, struct, time, sys
from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16

def fc06(ser, slave, address, value):
    ser.reset_input_buffer()
    req=frame(struct.pack(">BBHH",slave,0x06,address,value & 0xFFFF))
    ser.write(req); ser.flush()
    resp=read_exact(ser,8); check_crc(resp)
    if resp[:-2] != req[:-2]:
        raise RuntimeError(f"FC06 echo mismatch ID{slave} addr=0x{address:04X}")

def configure(ser, sid):
    fc06(ser,sid,0x0A27,1)
    time.sleep(.5)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port",default="/dev/ttyUSB0")
    ap.add_argument("--baud",type=int,required=True)
    ap.add_argument("--ids",required=True)
    ap.add_argument("--timeout",type=float,default=.25)
    ap.add_argument("--arm",default="")
    a=ap.parse_args()
    if a.arm!="I_UNDERSTAND":
        sys.exit("Re-run with --arm I_UNDERSTAND")
    ids=[int(x) for x in a.ids.split(",")]
    if not ids or len(set(ids)) != len(ids):
        sys.exit("--ids must contain unique driver IDs")

    originals={}
    with serial.Serial(a.port,a.baud,bytesize=8,parity="N",stopbits=1,timeout=a.timeout) as ser:
        print("=== PRECHECK ===")
        for sid in ids:
            status=fc03_one(ser,sid,0x0000)
            rpm=s16(fc03_one(ser,sid,0x0002))
            alarm=fc03_one(ser,sid,0x0003)
            netin=fc03_one(ser,sid,0x1400)
            fmt=fc03_one(ser,sid,0x020D)
            originals[sid]=fmt
            print(f"ID{sid}: status={status} alarm={alarm} rpm={rpm:+d} NET-IN=0x{netin:04X} 02-14={fmt}")
            if alarm!=0 or rpm!=0 or (netin & 0x0080):
                sys.exit(f"BLOCKED: ID{sid} is not safely stopped/disabled")
            if fmt not in (0,1):
                sys.exit(f"BLOCKED: ID{sid} unexpected 02-14={fmt}")

        print("Original formats:", originals)
        if all(v==1 for v in originals.values()):
            print("PASS: all requested drivers already use 02-14=1")
            return

        try:
            print("\n=== WRITE 02-14 = 1 ===")
            for sid in ids:
                fc06(ser,sid,0x020D,1)
                print(f"ID{sid}: EEP 02-14 <- 1")

            print("\n=== CONFIGURATION ===")
            for sid in ids:
                configure(ser,sid)
                print(f"ID{sid}: Configuration complete")

            print("\n=== VERIFY ===")
            for sid in ids:
                fmt=fc03_one(ser,sid,0x020D)
                alarm=fc03_one(ser,sid,0x0003)
                print(f"ID{sid}: 02-14={fmt} alarm={alarm}")
                if fmt!=1 or alarm!=0:
                    raise RuntimeError(f"ID{sid}: verification failed")
        except Exception:
            print("\n=== FAILURE: ATTEMPT ROLLBACK ===", file=sys.stderr)
            for sid in ids:
                try:
                    fc06(ser,sid,0x020D,originals[sid])
                    configure(ser,sid)
                    print(f"ID{sid}: restored 02-14={originals[sid]}", file=sys.stderr)
                except Exception as e:
                    print(f"ID{sid}: ROLLBACK FAILED: {e}", file=sys.stderr)
            raise

        print("\nPASS: all requested drivers report 02-14=1")

if __name__=="__main__":
    main()
