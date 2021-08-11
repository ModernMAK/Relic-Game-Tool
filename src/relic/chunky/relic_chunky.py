from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.abstract_relic_chunky import AbstractRelicChunky
from relic.chunky.magic import RelicChunkyMagic
from relic.chunky.relic_chunky_header import RelicChunkyHeader


# Seperate dataclass to hide trick IsInstance

@dataclass
class RelicChunky(AbstractRelicChunky):
    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True):
        from relic.chunky.reader import read_all_chunks  # Causes cyclic dependency, must be included inside unpack
        if read_magic:
            RelicChunkyMagic.assert_magic_word(stream)
        header = RelicChunkyHeader.unpack(stream)
        chunks = read_all_chunks(stream, header.version)
        return RelicChunky(chunks, header)

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        from relic.chunky.reader import write_all_chunks
        written = 0
        if write_magic:
            written += RelicChunkyMagic.write_magic_word(stream)
        written += self.header.pack(stream)
        written += write_all_chunks(stream, self.chunks, self.header.version)
        return written
