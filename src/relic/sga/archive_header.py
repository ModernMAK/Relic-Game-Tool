from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO

from relic.sga.magic import ARCHIVE_MAGIC
# Version, 4 Unks, Name (fixed 128 char buffer), 4 Unks
from relic.shared import unpack_from_stream

_HEADER_LAYOUT = Struct("< L 4L 128s 4L")


@dataclass
class ArchiveHeader:
    version: int

    unk_a1: int
    unk_a2: int
    unk_a3: int
    unk_a4: int

    name: str

    unk_b1: int
    unk_b2: int
    unk_b3: int
    unk_b4: int

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveHeader':
        if read_magic:
            ARCHIVE_MAGIC.assert_magic_word(stream, True)
        args = unpack_from_stream(_HEADER_LAYOUT, stream)
        version = args[0]
        unks_a = args[1:5]
        name = args[5].decode("utf-16-le").rstrip("\x00")
        unks_b = args[6:10]
        return ArchiveHeader(version, *unks_a, name, *unks_b)

    # def pack(self, stream: BinaryIO) -> int:
    #     buffer: bytes = bytearray(_HEADER_STRUCT.size)
    #     _HEADER_STRUCT.pack_into(buffer, 0, self._as_tuple())
    #     return stream.write(buffer)
