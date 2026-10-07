import math
import struct
import pytest
from mobile_base_perception.packet import decode


def packet(values):
    data = b'\xaa\x55' + struct.pack('<14f', *values)
    checksum = 0
    for byte in data:
        checksum ^= byte
    return data + bytes([checksum])


def test_documented_packet_converts_units_and_installed_axes():
    acceleration, gyro = decode(packet([1, 2, 3, 0, 0, 90, 180, -90] + [0]*6),
                                9.81, math.pi/180, [2, -1, 3])
    assert acceleration == pytest.approx([19.62, -9.81, 29.43])
    assert gyro == pytest.approx([math.pi, -math.pi/2, -math.pi/2])


@pytest.mark.parametrize('data', [b'', b'xx' + packet([0]*14)[2:],
                                    packet([0]*14)[:-1] + b'\x00',
                                    packet([float('nan')]+[0]*13)])
def test_invalid_packets_never_become_measurements(data):
    with pytest.raises(ValueError):
        decode(data, 9.81, math.pi/180, [1, 2, 3])
