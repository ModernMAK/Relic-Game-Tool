

# Painted Team Layer Data?
import struct
from dataclasses import dataclass
from io import BytesIO

from relic.chunky import DataChunk


@dataclass
class PtldChunk:
    _HEADER = struct.Struct("< l l")
    # flag or counter, incriments, probably the 'layer' being painted, trim, weapon, etc
    layer: int
    image: bytes

    @classmethod
    def create(cls, chunk: DataChunk) -> 'PtldChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            unk_a, size = cls._HEADER.unpack(buffer)  # width and height are swapped?
            image = stream.read(size)
            return PtldChunk(unk_a, image)

