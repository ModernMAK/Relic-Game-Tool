from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.chunk_collection import ChunkCollection
from relic.chunky.relic_chunky import RelicChunkyHeader


# Added to allow specialized chunkies to preserve the header without re-declaring it
@dataclass
class AbstractRelicChunky(ChunkCollection):
    header: RelicChunkyHeader


@dataclass
class UnpackableRelicChunky(AbstractRelicChunky):
    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'UnpackableRelicChunky':
        raise NotImplementedError

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        raise NotImplementedError
