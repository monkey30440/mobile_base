#!/usr/bin/env python3
import argparse, struct, time, sys
from m1_modbus import serial, frame, check_crc, read_exact, s16

# Manual mapping when 09-26=0:
# Write Index 8 = Multi-drive Lite command, Index 9 = Multi-drive Lite Data1
# Multi-drive Lite CMD 0x01 = JG; Data1 is signed RPM.
CMD_JG=0x0001

def bitmask(ids):
    m=0
    for sid in ids:
        if not 1 <= sid <= 8: raise ValueError('IDs must be 1..8')
        m |= 1 << (sid-1)
    return m

def fc17(ser, ids, rpms):
    mask=bitmask(ids)
    read_addr=0xF000 | mask      # read index 0
    # read Data0..6 plus one Error_Check per driver
    read_count=len(ids)*(7+1)
    write_addr=0xF800 | mask     # write index 8: CMD, index 9: Data1
    write_words=[]
    for sid in sorted(ids):
        rpm=rpms[sid]
        write_words += [CMD_JG, rpm & 0xFFFF]
    write_count=len(write_words)
    body=struct.pack('>BBHHHHB',0x65,0x17,read_addr,read_count,write_addr,write_count,write_count*2)
    body += struct.pack('>'+'H'*write_count,*write_words)
    req=frame(body)
    ser.reset_input_buffer(); ser.write(req); ser.flush()
    head=read_exact(ser,3)
    if head[0]!=0x65: raise RuntimeError(f'unexpected ID 0x{head[0]:02X}')
    if head[1]==0x97:
        tail=read_exact(ser,3); pkt=head+tail; check_crc(pkt); raise RuntimeError(f'FC17 exception 0x{pkt[2]:02X}')
    if head[1]!=0x17: raise RuntimeError(f'unexpected FC 0x{head[1]:02X}')
    tail=read_exact(ser,head[2]+2); pkt=head+tail; check_crc(pkt)
    words=list(struct.unpack('>'+'H'*(head[2]//2),pkt[3:-2]))
    stride=8
    rows=[]
    for i,sid in enumerate(sorted(ids)):
        w=words[i*stride:(i+1)*stride]
        rows.append((sid,w))
    return rows

def show(rows):
    for sid,w in rows:
        if len(w)<8: print(f'ID{sid}: short feedback {w}'); continue
        print(f'ID{sid}: status={w[0]} alarm={w[1]} rpm={s16(w[2]):+d} pos_hi={s16(w[5])} pos_lo={w[6]} err=0x{w[7]:04X}')

p=argparse.ArgumentParser(description='ARMED low-speed Multi-drive 2.0 FC17 motor test')
p.add_argument('--port',default='/dev/ttyUSB0'); p.add_argument('--baud',type=int,required=True)
p.add_argument('--ids',required=True,help='RIGHT_ID,LEFT_ID; e.g. 1,2')
p.add_argument('--right-rpm',type=int,default=0); p.add_argument('--left-rpm',type=int,default=0)
p.add_argument('--seconds',type=float,default=1.0); p.add_argument('--hz',type=float,default=10.0)
p.add_argument('--timeout',type=float,default=.25); p.add_argument('--arm',default='')
a=p.parse_args(); ids=[int(x) for x in a.ids.split(',')]
if len(ids)!=2: sys.exit('--ids must contain exactly RIGHT_ID,LEFT_ID')
if a.arm!='I_UNDERSTAND': sys.exit('Refusing motor command. Re-run with --arm I_UNDERSTAND after wheels are lifted and E-stop/STO is ready.')
if a.seconds<=0 or a.seconds>5: sys.exit('--seconds must be >0 and <=5 for this bring-up script')
if max(abs(a.right_rpm),abs(a.left_rpm))>300: sys.exit('Bring-up safety limit: |rpm| <= 300')
right,left=ids; rpms={right:a.right_rpm,left:a.left_rpm}
print('ARMED TEST')
print(f'RIGHT ID{right}: {a.right_rpm:+d} RPM; LEFT ID{left}: {a.left_rpm:+d} RPM; duration={a.seconds}s')
print('Ctrl-C will attempt to command both motors to 0 RPM.')

with serial.Serial(a.port,a.baud,bytesize=8,parity='N',stopbits=1,timeout=a.timeout) as ser:
    end=time.monotonic()+a.seconds
    try:
        while time.monotonic()<end:
            rows=fc17(ser,ids,rpms); show(rows)
            time.sleep(max(0,1/a.hz))
    finally:
        print('STOP: commanding both motors 0 RPM...')
        stop={right:0,left:0}
        ok=False
        for i in range(3):
            try:
                rows=fc17(ser,ids,stop); show(rows); ok=True; break
            except Exception as e:
                print(f'stop retry {i+1} failed: {e}',file=sys.stderr)
                time.sleep(.1)
        if not ok:
            print('WARNING: software stop was NOT confirmed. Use hardware E-stop/STO immediately.',file=sys.stderr)
