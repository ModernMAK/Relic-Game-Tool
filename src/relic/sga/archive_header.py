from dataclasses import dataclass, fields, astuple
from struct import Struct
from typing import BinaryIO, Optional

from relic.sga.magic import ARCHIVE_MAGIC
# Version, 4 Unks, Name (fixed 128 char buffer), 4 Unks
from relic.sga.version import Version
from relic.shared import unpack_from_stream, pack_into_stream



_NAME_SIZE = 128
_VERSION_LAYOUT = Struct(f"< 2H")
_v2_LAYOUT = Struct(f"< 16s {_NAME_SIZE}s 16s")
_v5_LAYOUT = _v2_LAYOUT
_v9_LAYOUT = Struct(f"< {_NAME_SIZE}s")

# V9 Uses a different HEADER!?! (No checksums?)
#   Version (2 shorts)
#   Name (128)


@dataclass
class ArchiveHeader:
    version: Version
    name: str
    checksum_a: Optional[bytes] = None
    checksum_b: Optional[bytes] = None

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveHeader':
        if read_magic:
            ARCHIVE_MAGIC.assert_magic_word(stream, True)
        version_args = unpack_from_stream(_VERSION_LAYOUT, stream)
        version = Version(*version_args)
        if version == Version.DowIII_Version():
            args = unpack_from_stream(_v9_LAYOUT, stream)
            name = args[0].decode("utf-16-le").rstrip("\x00")
            return ArchiveHeader(version,name)

        elif version in [Version.DowII_Version(), Version.DowI_Version()]:
            args = unpack_from_stream(_v2_LAYOUT, stream)
            md5_a = args[0]
            name = args[1].decode("utf-16-le").rstrip("\x00")
            md5_b = args[2]
            return ArchiveHeader(version, name, md5_a, md5_b)
        else:
            raise NotImplementedError(version)

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
