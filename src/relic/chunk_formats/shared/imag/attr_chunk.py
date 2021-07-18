import struct
from dataclasses import dataclass
from io import BytesIO

from relic.chunky import DataChunk

_MIP = struct.Struct("< l")
_HEADER = struct.Struct("< l l l")


@dataclass
class AttrChunk:
    img: int
    width: int
    height: int
    mips: int

    @classmethod
    def create(cls, chunk: DataChunk) -> 'AttrChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(_HEADER.size)
            img, height, width = _HEADER.unpack(buffer)  # width and height are swapped?

            if stream.tell() < len(chunk.data):
                buffer = stream.read(_MIP.size)
                mips = _MIP.unpack(buffer)[0]
            else:
                mips = 0

            return AttrChunk(img, width, height, mips)
