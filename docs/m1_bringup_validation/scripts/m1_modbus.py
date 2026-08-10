#!/usr/bin/env python3
import serial, struct, time

BAUDS = [9600, 19200, 38400, 57600, 115200, 230400]

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if (crc & 1) else (crc >> 1)
    return crc & 0xFFFF

def frame(payload: bytes) -> bytes:
    c = crc16(payload)
    return payload + bytes((c & 0xFF, (c >> 8) & 0xFF))

def check_crc(pkt: bytes):
    if len(pkt) < 4:
        raise RuntimeError(f"short response: {pkt.hex(' ')}")
    got = pkt[-2] | (pkt[-1] << 8)
    want = crc16(pkt[:-2])
    if got != want:
        raise RuntimeError(f"CRC mismatch got=0x{got:04X} want=0x{want:04X}: {pkt.hex(' ')}")

def read_exact(ser, n):
    data = ser.read(n)
    if len(data) != n:
        raise TimeoutError(f"timeout: expected {n} bytes, got {len(data)} ({data.hex(' ')})")
    return data

def fc03_one(ser, slave, address):
    ser.reset_input_buffer()
    req = frame(struct.pack('>BBHH', slave, 0x03, address, 1))
    ser.write(req); ser.flush()
    head = read_exact(ser, 3)
    if head[0] != slave:
        raise RuntimeError(f"unexpected slave {head[0]}")
    if head[1] == 0x83:
        tail = read_exact(ser, 3)
        pkt = head + tail
        check_crc(pkt)
        raise RuntimeError(f"Modbus exception 0x{pkt[2]:02X}")
    if head[1] != 0x03 or head[2] != 2:
        raise RuntimeError(f"unexpected header: {head.hex(' ')}")
    tail = read_exact(ser, 4)
    pkt = head + tail
    check_crc(pkt)
    return struct.unpack('>H', pkt[3:5])[0]

def s16(v):
    return v - 65536 if v & 0x8000 else v
