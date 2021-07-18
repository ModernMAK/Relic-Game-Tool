import struct
from dataclasses import dataclass
from typing import BinaryIO

RELIC_CHUNKY_HEADER_LAYOUT = struct.Struct("< 4s L L")


@dataclass
class RelicChunkyHeader:
    type_br: str
    version_major: int
    version_minor: int

    @classmethod
    def unpack(cls, stream: BinaryIO):
        buffer = stream.read(RELIC_CHUNKY_HEADER_LAYOUT.size)
        type_br, v_major, v_minor = RELIC_CHUNKY_HEADER_LAYOUT.unpack_from(buffer)
        type_br = type_br.decode("ascii")
        return RelicChunkyHeader(type_br, v_major, v_minor)

    @classmethod
    def default(cls) -> 'RelicChunkyHeader':
        return RelicChunkyHeader("\r\n\0\0", 1, 1)
