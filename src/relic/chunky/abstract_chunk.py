from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.chunk_header import ChunkHeader


@dataclass
class AbstractChunk:
    header: ChunkHeader

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'AbstractChunk':
        raise NotImplementedError
