from dataclasses import dataclass, fields, astuple
from struct import Struct
from typing import BinaryIO

from relic.sga.magic import ARCHIVE_MAGIC
# Version, 4 Unks, Name (fixed 128 char buffer), 4 Unks
from relic.sga.version import Version
from relic.shared import unpack_from_stream, pack_into_stream

_NAME_SIZE = 128
_HEADER_LAYOUT = Struct(f"< 2H 16s {_NAME_SIZE}s 16s")


@dataclass
class ArchiveHeader:
    version: Version
    checksum_a: bytes
    name: str
    checksum_b: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveHeader':
        if read_magic:
            ARCHIVE_MAGIC.assert_magic_word(stream, True)
        args = unpack_from_stream(_HEADER_LAYOUT, stream)
        version = args[0:1]
        md5_a = args[2]
        name = args[3].decode("utf-16-le").rstrip("\x00")
        md5_b = args[4]
        return ArchiveHeader(Version(*version), md5_a, name, md5_b)

    # def repack(self, stream: BinaryIO, write_magic: bool = True) -> int:
    #     written = 0
    #     if write_magic:
    #         written += ARCHIVE_MAGIC.write_magic_word(stream)
    #     args = astuple(self)
    #     pre = (args[0].major, args[0].minor)
    #     name = args[5].encode("utf-16-le")
    #     # padding_size = _NAME_SIZE - len(name)
    #     # name += bytes([0x00] * padding_size)
    #     post = args[6:10]
    #     written += pack_into_stream(_HEADER_LAYOUT, stream, *pre, name, *post)
    #     return written
