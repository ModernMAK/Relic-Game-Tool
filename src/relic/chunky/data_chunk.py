from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.abstract_chunk import AbstractChunk
from relic.chunky.chunk_header import ChunkHeader


@dataclass
class DataChunk(AbstractChunk):
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'DataChunk':
        data = stream.read(header.size)
        return DataChunk(header, data)