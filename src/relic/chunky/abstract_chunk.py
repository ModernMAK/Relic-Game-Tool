from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.chunk_header import ChunkHeader


@dataclass
class AbstractChunk:
    """A base class for all chunks."""
    header: ChunkHeader

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'AbstractChunk':
        """Unpacks the chunk from the stream, using the chunk header provided."""
        raise NotImplementedError
