import struct
from dataclasses import dataclass
from io import BytesIO

from relic.chunky import DataChunk

_DATA = struct.Struct("< l l")


@dataclass
class HeadChunk:
    image_format: int
    unk_a: int

    @classmethod
    def create(cls, chunk: DataChunk) -> 'HeadChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(_DATA.size)
            args = _DATA.unpack(buffer)
            return HeadChunk(*args)
