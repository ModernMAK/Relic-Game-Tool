
# Painted Team BN?
# Looks identical to PTBD
import struct
from dataclasses import dataclass
from io import BytesIO

from relic.chunky import DataChunk


@dataclass
class PtbnChunk:
    _HEADER = struct.Struct("< f f f f")  # 4 floats?
    unk_a: float
    unk_b: float
    unk_c: float
    unk_d: float

    @classmethod
    def create(cls, chunk: DataChunk) -> 'PtbnChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            args = cls._HEADER.unpack(buffer)
            return PtbnChunk(*args)
