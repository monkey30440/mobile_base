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

"""HandBoard IMU V1 binary protocol parsing."""

from dataclasses import dataclass
import struct


HEADER = b'\xaa\x55'
PACKET_LENGTH = 59
_PAYLOAD_FORMAT = '<14f'


@dataclass(frozen=True)
class ImuSample:
    """One decoded HandBoard IMU V1 sample in device-native units."""

    acceleration_g: tuple[float, float, float]
    accel_rp_deg: tuple[float, float]
    angular_velocity_dps: tuple[float, float, float]
    gyro_rpy_deg: tuple[float, float, float]
    fusion_rpy_deg: tuple[float, float, float]


def _xor_checksum(data: bytes) -> int:
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum


def parse_packet(packet: bytes) -> ImuSample:
    """Validate and decode one complete 59-byte packet."""
    if len(packet) != PACKET_LENGTH:
        raise ValueError(f'packet length must be {PACKET_LENGTH} bytes')
    if not packet.startswith(HEADER):
        raise ValueError('packet header is invalid')
    if _xor_checksum(packet[:-1]) != packet[-1]:
        raise ValueError('packet checksum is invalid')

    values = struct.unpack(_PAYLOAD_FORMAT, packet[2:-1])
    return ImuSample(
        acceleration_g=values[0:3],
        accel_rp_deg=values[3:5],
        angular_velocity_dps=values[5:8],
        gyro_rpy_deg=values[8:11],
        fusion_rpy_deg=values[11:14],
    )


class PacketStreamParser:
    """Extract complete IMU packets from arbitrary serial byte chunks."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.checksum_error_count = 0

    def feed(self, data: bytes) -> list[ImuSample]:
        """Consume serial bytes and return every complete valid sample."""
        self._buffer.extend(data)
        samples = []

        while True:
            header_index = self._buffer.find(HEADER)
            if header_index < 0:
                self._keep_possible_header_prefix()
                break
            if header_index > 0:
                del self._buffer[:header_index]
            if len(self._buffer) < PACKET_LENGTH:
                break

            packet = bytes(self._buffer[:PACKET_LENGTH])
            try:
                sample = parse_packet(packet)
            except ValueError as error:
                if 'checksum' in str(error):
                    self.checksum_error_count += 1
                del self._buffer[0]
                continue

            samples.append(sample)
            del self._buffer[:PACKET_LENGTH]

        return samples

    def _keep_possible_header_prefix(self) -> None:
        if self._buffer.endswith(HEADER[:1]):
            self._buffer[:] = HEADER[:1]
        else:
            self._buffer.clear()
