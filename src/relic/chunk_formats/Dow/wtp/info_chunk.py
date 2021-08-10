import struct
from dataclasses import dataclass
from io import BytesIO

from relic.chunky import DataChunk

_HEADER = struct.Struct("< l l")


@dataclass
class WtpInfoChunk:
    width: int
    height: int

    @classmethod
    def create(cls, chunk: DataChunk) -> 'WtpInfoChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(_HEADER.size)
            height, width = _HEADER.unpack(buffer)  # width and height are swapped?
            return WtpInfoChunk(width, height)
