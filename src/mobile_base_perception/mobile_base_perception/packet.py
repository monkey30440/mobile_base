"""Bounded HandBoard V1 wire conversion; no board fusion is consumed."""
import struct
import math
from functools import reduce
from operator import xor


def decode(packet, acceleration_scale, gyro_scale, axes):
    if len(packet) != 59 or packet[:2] != b'\xaa\x55':
        raise ValueError('packet length/header invalid')
    if reduce(xor, packet[:-1], 0) != packet[-1]:
        raise ValueError('packet checksum invalid')
    values = struct.unpack('<14f', packet[2:58])
    if not all(math.isfinite(value) for value in values):
        raise ValueError('packet contains nonfinite data')
    def convert(vector, scale):
        return tuple(vector[abs(axis)-1] * (1 if axis > 0 else -1) * scale
                     for axis in axes)
    return convert(values[:3], acceleration_scale), convert(values[5:8], gyro_scale)
