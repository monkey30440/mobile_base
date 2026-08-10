#!/usr/bin/env python3
"""
Measure real FC17 transaction latency/jitter while commanding ZERO RPM.

This is the evidence needed before choosing ros2_control update_rate and 05-17.
The script enables both drives, but sends only 0 RPM. Wheels should still be lifted
and hardware E-stop/STO available.
"""
import argparse, struct, time, statistics, sys, math
from m1_modbus import serial, frame, check_crc, read_exact, fc03_one, s16

CMD_JG=1; NET_IN=0x1400

def fc06(ser,slave,address,value):
    ser.reset_input_buffer()
    req=frame(struct.pack(">BBHH",slave,0x06,address,value & 0xFFFF))
    ser.write(req); ser.flush()
    resp=read_exact(ser,8); check_crc(resp)
    if resp[:-2]!=req[:-2]: raise RuntimeError("FC06 echo mismatch")

def mask(ids):
    m=0
    for sid in ids: m |= 1<<(sid-1)
    return m

def exchange_zero(ser,ids):
    ordered=sorted(ids); m=mask(ordered)
    read_addr=0xF000|m; read_count=len(ordered)*8
    write_addr=0xF800|m
    words=[]
    for sid in ordered: words += [CMD_JG,0]
    body=struct.pack(">BBHHHHB",0x65,0x17,read_addr,read_count,write_addr,len(words),len(words)*2)
    body+=struct.pack(">"+("H"*len(words)),*words)
    req=frame(body)
    ser.reset_input_buffer()
    t0=time.perf_counter_ns()
    ser.write(req); ser.flush()
    head=read_exact(ser,3)
    if head[0]!=0x65 or head[1]!=0x17: raise RuntimeError(f"unexpected response {head.hex(' ')}")
    tail=read_exact(ser,head[2]+2); pkt=head+tail; check_crc(pkt)
    dt_ms=(time.perf_counter_ns()-t0)/1e6
    return dt_ms

def percentile(xs,p):
    s=sorted(xs)
    if len(s)==1: return s[0]
    k=(len(s)-1)*p
    f=math.floor(k); c=math.ceil(k)
    if f==c:return s[f]
    return s[f]*(c-k)+s[c]*(k-f)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port",default="/dev/ttyUSB0")
    ap.add_argument("--baud",type=int,required=True)
    ap.add_argument("--ids",required=True)
    ap.add_argument("--samples",type=int,default=300)
    ap.add_argument("--hz",type=float,default=50)
    ap.add_argument("--arm",default="")
    a=ap.parse_args()
    if a.arm!="I_UNDERSTAND": sys.exit("Re-run with --arm I_UNDERSTAND")
    ids=[int(x) for x in a.ids.split(",")]
    if len(ids)!=2 or len(set(ids))!=2: sys.exit("--ids must contain two unique IDs")
    if not (10<=a.samples<=5000): sys.exit("--samples must be 10..5000")
    if not (1<=a.hz<=100): sys.exit("--hz must be 1..100")
    original={}
    times=[]

    with serial.Serial(a.port,a.baud,bytesize=8,parity="N",stopbits=1,timeout=.25) as ser:
        for sid in ids:
            alarm=fc03_one(ser,sid,0x0003); rpm=s16(fc03_one(ser,sid,0x0002)); net=fc03_one(ser,sid,NET_IN)
            original[sid]=net
            if alarm!=0 or rpm!=0: sys.exit(f"BLOCKED ID{sid}: alarm={alarm}, rpm={rpm}")
        try:
            for sid in ids: fc06(ser,sid,NET_IN,original[sid]|0x0080)
            time.sleep(.3)
            period=1/a.hz
            for i in range(a.samples):
                loop=time.monotonic()
                dt=exchange_zero(ser,ids); times.append(dt)
                if (i+1)%50==0 or i==0: print(f"{i+1}/{a.samples}: {dt:.3f} ms")
                remain=period-(time.monotonic()-loop)
                if remain>0: time.sleep(remain)
        finally:
            for sid in ids:
                try: fc06(ser,sid,NET_IN,original.get(sid,0))
                except Exception as e: print(f"restore ID{sid} failed: {e}",file=sys.stderr)

    print("\n=== FC17 TIMING RESULT ===")
    print(f"samples={len(times)} requested_rate={a.hz:.1f} Hz")
    print(f"min_ms={min(times):.3f}")
    print(f"mean_ms={statistics.mean(times):.3f}")
    print(f"p50_ms={percentile(times,.50):.3f}")
    print(f"p95_ms={percentile(times,.95):.3f}")
    print(f"p99_ms={percentile(times,.99):.3f}")
    print(f"max_ms={max(times):.3f}")
    print(f"theoretical_max_exchange_rate_from_max_sample={1000/max(times):.1f} Hz")
    print("NOTE: do not set 05-17 from this number alone; leave safety margin and test failure behavior.")

if __name__=="__main__":
    main()
