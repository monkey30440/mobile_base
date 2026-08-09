#!/usr/bin/env python3
import argparse
from m1_modbus import serial, fc03_one

REGS = [
 ('01-01 motor/sensor type',0x0100),
 ('01-04 no-load full RPM',0x0103),
 ('01-06 encoder resolution pulse/rev',0x0105),
 ('01-10 drive enable',0x0109),
 ('01-11 control mode',0x010A),
 ('02-14 position format',0x020D),
 ('02-15 speed display update rate',0x020E),
 ('05-03 feedback protection',0x0502),
 ('05-04 overspeed alarm RPM',0x0503),
 ('05-17 RS485/CAN timeout ms',0x0510),
 ('05-18 RS485 error count',0x0511),
 ('05-21 communication failure action',0x0514),
 ('09-18 RS485 protocol',0x0911),
 ('09-19 RS485/CAN ID',0x0912),
 ('09-20 RS485/CAN baud selector',0x0913),
 ('09-21 RTU C3.5 selector',0x0914),
 ('09-26 CANOpen/MultiDrive2 PDO mapping',0x0919),
]

p=argparse.ArgumentParser(description='Read-only M1 configuration dump')
p.add_argument('--port',default='/dev/ttyUSB0'); p.add_argument('--baud',type=int,required=True)
p.add_argument('--ids',required=True,help='comma separated, e.g. 1,2'); p.add_argument('--timeout',type=float,default=.2)
a=p.parse_args(); ids=[int(x) for x in a.ids.split(',')]

with serial.Serial(a.port,a.baud,bytesize=8,parity='N',stopbits=1,timeout=a.timeout) as ser:
    for sid in ids:
        print(f'\n===== Driver ID {sid} =====')
        for name,addr in REGS:
            try:
                v=fc03_one(ser,sid,addr)
                print(f'{name:42s} 0x{addr:04X} = {v} (0x{v:04X})')
            except Exception as e:
                print(f'{name:42s} 0x{addr:04X} = ERROR: {e}')
