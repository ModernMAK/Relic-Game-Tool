from dataclasses import dataclass
from typing import BinaryIO

from archive_tools.structx import Struct

from relic.chunky.abstract_relic_chunky import UnpackableRelicChunky
from relic.chunky.magic import RelicChunkyMagic
from relic.chunky.version import ChunkyVersion
from relic.shared import Version

@dataclass
class RelicChunkyHeader:
    HEADER_LAYOUT = Struct("< 4s 2L")
    LAYOUT_V3_1 = Struct("< 3L")
    V3_CONST = (36, 28, 1)
    TYPE_BR = "\r\n\x1a\0".encode("ascii")  # I forgot what this was supposed to be (TODO)

    version: Version

    @classmethod
    def unpack(cls, stream: BinaryIO):
        type_br, v_major, v_minor = cls.HEADER_LAYOUT.unpack_stream(stream)
        version = Version(v_major, v_minor)
        assert type_br == cls.TYPE_BR

        if version == ChunkyVersion.v3_1:
            # Always these 3 values from what I've looked at so far. Why?
            # 36 is the position of the first chunk  in the ones I've looked at
            # 28 is a pointer to itself (28); perhaps the size of the Header?
            # Reserved 1?
            v3_args = cls.LAYOUT_V3_1.unpack_stream(stream)
            assert v3_args == cls.V3_CONST

        return RelicChunkyHeader(version)

    def pack(self, stream: BinaryIO) -> int:
        written = 0
        written += self.HEADER_LAYOUT.pack_stream(stream, self.TYPE_BR, self.version.major, self.version.minor)

        if self.version == ChunkyVersion.v3_1:
            written += self.LAYOUT_V3_1.pack_stream(stream, *self.V3_CONST)

        return written

    @classmethod
    def default(cls, version: Version = None) -> 'RelicChunkyHeader':
        version = version or Version(1, 1)
        return RelicChunkyHeader(version)

    def copy(self) -> 'RelicChunkyHeader':
        return RelicChunkyHeader(self.version)


@dataclass
class RelicChunky(UnpackableRelicChunky):
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
