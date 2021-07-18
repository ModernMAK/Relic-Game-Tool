import struct
from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.abstract_relic_chunky import AbstractRelicChunky
from relic.chunky.chunk_collection import ChunkCollection
from relic.chunky.relic_chunky_header import RelicChunkyHeader

_relic_chunky_magic_word = "Relic Chunky"
_relic_chunky_magic_word_layout = struct.Struct("< 12s")

@dataclass
class RelicChunky(AbstractRelicChunky, ChunkCollection):
    @classmethod
    def unpack(cls, stream: BinaryIO):
        from relic.chunky.reader import read_all_chunks  # Causes cylic dependency, must be included inside unpack

        buffer = stream.read(_relic_chunky_magic_word_layout.size)
        magic = _relic_chunky_magic_word_layout.unpack_from(buffer)[0].decode("ascii")
        if magic != _relic_chunky_magic_word:
            raise ValueError((magic, _relic_chunky_magic_word))
        header = RelicChunkyHeader.unpack(stream)
        chunks = read_all_chunks(stream)
        return RelicChunky(chunks,header)
