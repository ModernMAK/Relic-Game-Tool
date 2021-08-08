import struct
from dataclasses import dataclass

from relic.chunky import DataChunk

_INFO_STRUCT = struct.Struct("< 7L")


@dataclass
class FdaInfoChunk:
    channels: int
    sample_size: int
    block_bitrate: int
    sample_rate: int
    begin_loop: int
    end_loop: int
    start_offset: int

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'FdaInfoChunk':
        args = _INFO_STRUCT.unpack_from(chunk.data, 0)
        return FdaInfoChunk(*args)
