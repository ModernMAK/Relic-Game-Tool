import struct
from dataclasses import dataclass
from typing import BinaryIO

_relic_chunky_header_layout = struct.Struct("< 4s L L")


@dataclass
class RelicChunkyHeader:
    type_br: str
    version_major: int
    version_minor: int

    @classmethod
    def unpack(cls, stream: BinaryIO):
        buffer = stream.read(_relic_chunky_header_layout.size)
        type_br, v_major, v_minor = _relic_chunky_header_layout.unpack_from(buffer)
        type_br = type_br.decode("ascii")
        return RelicChunkyHeader(type_br, v_major, v_minor)
