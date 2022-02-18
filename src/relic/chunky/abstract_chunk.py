from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.chunk_header import ChunkHeader
from relic.shared import Version


@dataclass
class AbstractChunk:
    """A base class for all chunks."""
    header: ChunkHeader


@dataclass
class UnpackableChunk(AbstractChunk):
    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'UnpackableChunk':
        """Unpacks the chunk from the stream, using the chunk header provided."""
        raise NotImplementedError

    def pack(self, stream: BinaryIO, chunky_version: Version) -> int:
        raise NotImplementedError
