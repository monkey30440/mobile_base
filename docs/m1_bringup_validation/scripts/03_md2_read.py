#!/usr/bin/env python3
import argparse, struct, time
from m1_modbus import serial, frame, check_crc, read_exact, s16, fc03_one

STATUS={0:'STOP',2:'RUN',3:'EBRAKE',4:'FREE',5:'FAULT',6:'WAIT/INHIBIT',7:'MOVING(SERVO ON)',8:'SLIGHT-POS-KEEPING',9:'STO'}

def s32(hi, lo):
    u = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    return u - 0x100000000 if u & 0x80000000 else u

def bitmask(ids):
    m=0
    for sid in ids:
        if not 1 <= sid <= 8: raise ValueError('Multi-drive 2.0 group supports ID 1..8')
        m |= 1 << (sid-1)
    return m

def read_md2(ser, ids, start_index=0, n_items=7):
    mask=bitmask(ids)
    addr=0xF000 | (start_index<<8) | mask
    # manual: Num = drivers * (n_items + 1 error_check)
    count=len(ids)*(n_items+1)
    req=frame(struct.pack('>BBHH',0x65,0x03,addr,count))
    ser.reset_input_buffer(); ser.write(req); ser.flush()
    head=read_exact(ser,3)
    if head[0]!=0x65: raise RuntimeError(f'unexpected ID 0x{head[0]:02X}')
    if head[1]==0x83:
        tail=read_exact(ser,3); pkt=head+tail; check_crc(pkt); raise RuntimeError(f'Modbus exception 0x{pkt[2]:02X}')
    if head[1]!=0x03: raise RuntimeError(f'unexpected FC 0x{head[1]:02X}')
    tail=read_exact(ser,head[2]+2); pkt=head+tail; check_crc(pkt)
    words=list(struct.unpack('>'+'H'*(head[2]//2),pkt[3:-2]))
    expected=len(ids)*(n_items+1)
    if len(words)!=expected: raise RuntimeError(f'expected {expected} words, got {len(words)}')
    out=[]
    stride=n_items+1
    for i,sid in enumerate(sorted(ids)):
        w=words[i*stride:(i+1)*stride]
        out.append((sid,w[:-1],w[-1]))
    return out

p=argparse.ArgumentParser(description='READ-ONLY Multi-drive 2.0 FC03 feedback test')
p.add_argument('--port',default='/dev/ttyUSB0'); p.add_argument('--baud',type=int,required=True)
p.add_argument('--ids',required=True,help='selected IDs 1..8, e.g. 1,2')
p.add_argument('--samples',type=int,default=1); p.add_argument('--hz',type=float,default=2.0); p.add_argument('--timeout',type=float,default=.25)
a=p.parse_args(); ids=[int(x) for x in a.ids.split(',')]

with serial.Serial(a.port,a.baud,bytesize=8,parity='N',stopbits=1,timeout=a.timeout) as ser:
    position_formats = {sid: fc03_one(ser, sid, 0x020D) for sid in ids}
    print('Position formats:', ', '.join(f'ID{sid}={position_formats[sid]}' for sid in ids))
    for sid, fmt in position_formats.items():
        if fmt not in (0, 1):
            raise RuntimeError(f'ID{sid}: unsupported 02-14={fmt}')

    for k in range(a.samples):
        t=time.time()
        rows=read_md2(ser,ids)
        print(f'\n[{k+1}/{a.samples}] {time.strftime("%F %T")}')
        for sid,d,err in rows:
            status=d[0]; alarm=d[1]; rpm=s16(d[2]); busv=d[3]/100.0; current=d[4]/100.0
            if position_formats[sid] == 0:
                pos_text = f'pos_turns={s16(d[5])} pos_pulse={d[6]}'
            else:
                pos_text = f'pos_steps={s32(d[5], d[6]):+d} hi=0x{d[5]:04X} lo=0x{d[6]:04X}'
            print(f'ID{sid}: status={status}({STATUS.get(status,"?")}) alarm={alarm} rpm={rpm:+d} '
                  f'bus={busv:.2f}V current={current:.2f}A {pos_text} errchk=0x{err:04X}')
        dt=time.time()-t
        if k+1<a.samples: time.sleep(max(0,1/a.hz-dt))
