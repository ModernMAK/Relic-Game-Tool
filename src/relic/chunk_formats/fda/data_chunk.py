import struct
from dataclasses import dataclass

from relic.chunky import DataChunk

_DATA_STRUCT = struct.Struct("< L")


@dataclass
class FdaDataChunk:
    size: int
    data: bytes

    @classmethod
    def create(cls, chunk: DataChunk) -> 'FdaDataChunk':
        args = _DATA_STRUCT.unpack(chunk.data[:4])[0]
        data = chunk.data[4:]
        return FdaDataChunk(args, data)
