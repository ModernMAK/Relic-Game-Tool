
# Painted Team BD?
import struct
from dataclasses import dataclass
from io import BytesIO

from relic.chunky import DataChunk


@dataclass
class PtbdChunk:
    _HEADER = struct.Struct("< f f f f")  # 4 floats?
    # floats are typically positions, uv coordinates?
    # atlas size maybe? IDK
    unk_a: float
    unk_b: float
    unk_c: float
    unk_d: float

    @classmethod
    def create(cls, chunk: DataChunk) -> 'PtbdChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            args = cls._HEADER.unpack(buffer)
            return PtbdChunk(*args)

