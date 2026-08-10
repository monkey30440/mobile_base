#!/usr/bin/env python3
import argparse, time
from m1_modbus import serial, BAUDS, fc03_one

p = argparse.ArgumentParser(description='Read-only scan for M1 Modbus RTU baud and slave IDs')
p.add_argument('--port', default='/dev/ttyUSB0')
p.add_argument('--ids', default='1-8', help='e.g. 1-8 or 1,2')
p.add_argument('--timeout', type=float, default=0.12)
a = p.parse_args()

def ids(spec):
    if '-' in spec:
        x,y = map(int,spec.split('-',1)); return range(x,y+1)
    return [int(x) for x in spec.split(',')]

print('READ-ONLY scan: FC03 register 0x0000 (motor status)')
found=[]
for baud in BAUDS:
    print(f'\n-- baud {baud} --')
    try:
        with serial.Serial(a.port, baudrate=baud, bytesize=8, parity='N', stopbits=1, timeout=a.timeout) as ser:
            for sid in ids(a.ids):
                try:
                    v = fc03_one(ser, sid, 0x0000)
                    print(f'PASS id={sid}: motor_status={v}')
                    found.append((baud,sid,v))
                except Exception as e:
                    print(f'.... id={sid}: no valid reply')
                time.sleep(0.01)
    except Exception as e:
        print(f'cannot open {a.port}: {e}')
        break

print('\n== RESULT ==')
if not found:
    print('No valid M1 reply found.')
else:
    for x in found: print(f'baud={x[0]} id={x[1]} motor_status={x[2]}')
