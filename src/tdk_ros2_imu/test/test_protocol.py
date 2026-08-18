# Copyright 2026 FIH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import struct

import pytest

from tdk_ros2_imu.protocol import PacketStreamParser
from tdk_ros2_imu.protocol import parse_packet


VALUES = (
    0.1, -0.2, 1.0,
    1.0, 2.0,
    3.0, -4.0, 5.0,
    6.0, 7.0, 8.0,
    9.0, -10.0, 11.0,
)


def make_packet(values=VALUES):
    packet_without_checksum = b'\xaa\x55' + struct.pack('<14f', *values)
    checksum = 0
    for byte in packet_without_checksum:
        checksum ^= byte
    return packet_without_checksum + bytes((checksum,))


def test_parse_packet_maps_all_measurement_groups():
    sample = parse_packet(make_packet())

    assert sample.acceleration_g == pytest.approx((0.1, -0.2, 1.0))
    assert sample.accel_rp_deg == pytest.approx((1.0, 2.0))
    assert sample.angular_velocity_dps == pytest.approx((3.0, -4.0, 5.0))
    assert sample.gyro_rpy_deg == pytest.approx((6.0, 7.0, 8.0))
    assert sample.fusion_rpy_deg == pytest.approx((9.0, -10.0, 11.0))


def test_parse_packet_rejects_bad_checksum():
    packet = bytearray(make_packet())
    packet[-1] ^= 0xff

    with pytest.raises(ValueError, match='checksum'):
        parse_packet(bytes(packet))


def test_stream_parser_waits_for_complete_packet():
    packet = make_packet()
    parser = PacketStreamParser()

    assert parser.feed(packet[:20]) == []
    samples = parser.feed(packet[20:])

    assert len(samples) == 1
    assert samples[0].fusion_rpy_deg == pytest.approx((9.0, -10.0, 11.0))


def test_stream_parser_resynchronizes_after_noise_and_bad_packet():
    bad_packet = bytearray(make_packet())
    bad_packet[-1] ^= 0xff
    parser = PacketStreamParser()

    samples = parser.feed(b'\x00\xaa\x00noise' + bad_packet + make_packet())

    assert len(samples) == 1
    assert parser.checksum_error_count == 1


def test_stream_parser_returns_multiple_packets_from_one_read():
    parser = PacketStreamParser()

    samples = parser.feed(make_packet() + make_packet())

    assert len(samples) == 2
