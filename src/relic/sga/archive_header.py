from dataclasses import dataclass, fields, astuple
from struct import Struct
from typing import BinaryIO

from relic.sga.magic import ARCHIVE_MAGIC
# Version, 4 Unks, Name (fixed 128 char buffer), 4 Unks
from relic.shared import unpack_from_stream, pack_into_stream

_NAME_SIZE = 128
_HEADER_LAYOUT = Struct(f"< L 4L {_NAME_SIZE}s 4L")


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

    def repack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        written = 0
        if write_magic:
            written += ARCHIVE_MAGIC.write_magic_word(stream)
        args = astuple(self)
        pre = args[0:5]
        name = args[5].encode("utf-16-le")
        # padding_size = _NAME_SIZE - len(name)
        # name += bytes([0x00] * padding_size)
        post = args[6:10]
        written += pack_into_stream(_HEADER_LAYOUT, stream, *pre, name, *post)
        return written
