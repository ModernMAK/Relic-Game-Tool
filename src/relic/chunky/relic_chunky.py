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
    def read_magic_word(cls, stream: BinaryIO, advance: bool = True) -> str:
        buffer = stream.read(_relic_chunky_magic_word_layout.size)
        magic = _relic_chunky_magic_word_layout.unpack_from(buffer)[0].decode("ascii")
        if not advance:  # Useful for checking the header before reading it
            stream.seek(-_relic_chunky_magic_word_layout.size, 1)
        return magic

    @classmethod
    def assert_magic_word(cls, stream: BinaryIO, advance: bool = True):
        magic = cls.read_magic_word(stream, advance=advance)
        assert magic == _relic_chunky_magic_word, (magic, _relic_chunky_magic_word)

    @classmethod
    def check_magic_word(cls, stream: BinaryIO, advance: bool = True) -> bool:
        magic = cls.read_magic_word(stream, advance=advance)
        return magic == _relic_chunky_magic_word

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True):
        from relic.chunky.reader import read_all_chunks  # Causes cyclic dependency, must be included inside unpack
        if read_magic:
            cls.assert_magic_word(stream)
        header = RelicChunkyHeader.unpack(stream)
        chunks = read_all_chunks(stream)
        return RelicChunky(chunks, header)
