from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.abstract_relic_chunky import AbstractRelicChunky
from relic.chunky.chunk_collection import ChunkCollection
from relic.chunky.magic import RELIC_CHUNKY_MAGIC
from relic.chunky.relic_chunky_header import RelicChunkyHeader


@dataclass
class RelicChunky(AbstractRelicChunky, ChunkCollection):
    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True):
        from relic.chunky.reader import read_all_chunks  # Causes cyclic dependency, must be included inside unpack
        if read_magic:
            RELIC_CHUNKY_MAGIC.assert_magic_word(stream)
        header = RelicChunkyHeader.unpack(stream)
        chunks = read_all_chunks(stream)
        return RelicChunky(chunks, header)
