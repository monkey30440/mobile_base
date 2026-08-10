#!/usr/bin/env python3
"""
Verify 02-14=1 Multi-drive 2.0 Read Data5/6 behavior.

For the selected wheel this test runs +RPM, stops, then -RPM and verifies:
  * FC17 returns a signed 32-bit position assembled from Data5/Data6.
  * +RPM produces positive native position delta.
  * -RPM produces negative native position delta.
  * the unselected motor remains stopped.
  * alarm remains zero.

This proves direction/delta semantics. It does NOT force the absolute counter across
the int32 sign boundary; int32 wrap must still be handled in production software.
"""
import argparse, struct, time, sys
from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16

CMD_JG=1
NET_IN=0x1400

def fc06(ser,slave,address,value):
    ser.reset_input_buffer()
    req=frame(struct.pack(">BBHH",slave,0x06,address,value & 0xFFFF))
    ser.write(req); ser.flush()
    resp=read_exact(ser,8); check_crc(resp)
    if resp[:-2] != req[:-2]:
        raise RuntimeError("FC06 echo mismatch")

def s32(hi,lo):
    u=((hi & 0xFFFF)<<16)|(lo & 0xFFFF)
    return u-0x100000000 if u & 0x80000000 else u

def mask(ids):
    m=0
    for sid in ids:
        if not 1 <= sid <= 8: raise ValueError("IDs must be 1..8")
        m |= 1<<(sid-1)
    return m

def exchange(ser,ids,rpms):
    ordered=sorted(ids); m=mask(ordered)
    raddr=0xF000|m; rcount=len(ordered)*8
    waddr=0xF800|m
    words=[]
    for sid in ordered: words += [CMD_JG, rpms[sid] & 0xFFFF]
    body=struct.pack(">BBHHHHB",0x65,0x17,raddr,rcount,waddr,len(words),len(words)*2)
    body+=struct.pack(">"+("H"*len(words)),*words)
    req=frame(body)
    ser.reset_input_buffer(); ser.write(req); ser.flush()
    head=read_exact(ser,3)
    if head[0] != 0x65: raise RuntimeError(f"unexpected group ID 0x{head[0]:02X}")
    if head[1]==0x97:
        tail=read_exact(ser,3); pkt=head+tail; check_crc(pkt)
        raise RuntimeError(f"FC17 exception 0x{pkt[2]:02X}")
    if head[1]!=0x17: raise RuntimeError(f"unexpected FC 0x{head[1]:02X}")
    tail=read_exact(ser,head[2]+2); pkt=head+tail; check_crc(pkt)
    vals=list(struct.unpack(">"+("H"*(head[2]//2)),pkt[3:-2]))
    if len(vals) != len(ordered)*8: raise RuntimeError("unexpected response length")
    out={}
    for i,sid in enumerate(ordered):
        w=vals[i*8:(i+1)*8]
        out[sid]={"status":w[0],"alarm":w[1],"rpm":s16(w[2]),
                  "hi":w[5],"lo":w[6],"pos":s32(w[5],w[6])}
    return out

def show(sid,r):
    print(f"ID{sid}: status={r['status']} alarm={r['alarm']} rpm={r['rpm']:+d} "
          f"hi=0x{r['hi']:04X} lo=0x{r['lo']:04X} pos={r['pos']:+d}")

def run_phase(ser, ids, selected, other, rpm, seconds, hz):
    stop={sid:0 for sid in ids}
    cmd=dict(stop); cmd[selected]=rpm
    base=exchange(ser,ids,stop)
    start=base[selected]["pos"]
    end=time.monotonic()+seconds
    last=base[selected]
    while time.monotonic()<end:
        rows=exchange(ser,ids,cmd)
        last=rows[selected]
        show(selected,last)
        if last["alarm"]!=0: raise RuntimeError("alarm during motion")
        if abs(rows[other]["rpm"])>2: raise RuntimeError("other motor moved")
        time.sleep(1.0/hz)
    # stop and allow deceleration
    for _ in range(5):
        rows=exchange(ser,ids,stop)
        if all(abs(r["rpm"])==0 for r in rows.values()): break
        time.sleep(.1)
    final=exchange(ser,ids,stop)[selected]
    delta=final["pos"]-start
    print(f"phase {rpm:+d} RPM delta = {delta:+d} steps")
    if delta==0 or ((delta>0)!=(rpm>0)):
        raise RuntimeError(f"position delta sign mismatch for {rpm:+d} RPM")
    return delta

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port",default="/dev/ttyUSB0")
    ap.add_argument("--baud",type=int,required=True)
    ap.add_argument("--ids",required=True,help="RIGHT_ID,LEFT_ID")
    ap.add_argument("--wheel",choices=("right","left"),required=True)
    ap.add_argument("--rpm",type=int,default=80)
    ap.add_argument("--seconds",type=float,default=.8)
    ap.add_argument("--hz",type=float,default=10)
    ap.add_argument("--arm",default="")
    a=ap.parse_args()
    if a.arm!="I_UNDERSTAND": sys.exit("Re-run with --arm I_UNDERSTAND")
    if not (1 <= abs(a.rpm) <= 300): sys.exit("|rpm| must be 1..300")
    if not (0 < a.seconds <= 3): sys.exit("--seconds must be >0 and <=3")
    ids=[int(x) for x in a.ids.split(",")]
    if len(ids)!=2 or len(set(ids))!=2: sys.exit("--ids must be RIGHT_ID,LEFT_ID")
    right,left=ids; selected=right if a.wheel=="right" else left; other=left if selected==right else right
    original={}

    with serial.Serial(a.port,a.baud,bytesize=8,parity="N",stopbits=1,timeout=.25) as ser:
        print("=== PRECHECK ===")
        for sid in ids:
            fmt=fc03_one(ser,sid,0x020D); alarm=fc03_one(ser,sid,0x0003)
            rpm_now=s16(fc03_one(ser,sid,0x0002)); net=fc03_one(ser,sid,0x1400)
            original[sid]=net
            print(f"ID{sid}: 02-14={fmt} alarm={alarm} rpm={rpm_now:+d} NET-IN=0x{net:04X}")
            if fmt!=1 or alarm!=0 or rpm_now!=0: sys.exit(f"BLOCKED ID{sid}")

        try:
            for sid in ids: fc06(ser,sid,NET_IN,original[sid]|0x0080)
            time.sleep(.3)
            print("\n=== +RPM PHASE ===")
            dpos=run_phase(ser,ids,selected,other,abs(a.rpm),a.seconds,a.hz)
            print("\n=== -RPM PHASE ===")
            dneg=run_phase(ser,ids,selected,other,-abs(a.rpm),a.seconds,a.hz)
            print(f"\npositive delta={dpos:+d}; negative delta={dneg:+d}")
        finally:
            stop={sid:0 for sid in ids}
            for _ in range(5):
                try:
                    rows=exchange(ser,ids,stop)
                    if all(abs(r["rpm"])==0 for r in rows.values()): break
                except Exception: pass
                time.sleep(.1)
            for sid in ids:
                try: fc06(ser,sid,NET_IN,original.get(sid,0))
                except Exception as e: print(f"restore ID{sid} failed: {e}",file=sys.stderr)
            time.sleep(.3)

        print("\nPASS: 02-14=1 FC17 signed position delta verified in both directions")
        print("NOTE: production code must still unwrap int32 rollover if lifetime travel can reach it.")

if __name__=="__main__":
    main()
