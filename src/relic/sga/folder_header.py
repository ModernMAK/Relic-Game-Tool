from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO, Dict, Optional

from relic.sga.archive_info import ArchiveInfo
from relic.sga.archive_range import ArchiveRange
from relic.sga.shared import read_name
from relic.sga.version import Version
from relic.shared import unpack_from_stream


@dataclass
class FolderHeader:
    __v2_LAYOUT = Struct("< L 4H")  # 12
    __v5_LAYOUT = __v2_LAYOUT  # 12
    __v9_LAYOUT = Struct("< L 4L")  # 20

    name_offset: int
    subfolder_range: ArchiveRange
    file_range: ArchiveRange

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version) -> 'FolderHeader':
        if version in [Version.DowI_Version(), Version.DowII_Version()]:
            args = unpack_from_stream(cls.__v2_LAYOUT, stream)
            subfolder_range = ArchiveRange(args[1], args[2])
            file_range = ArchiveRange(args[3], args[4])
            return FolderHeader(args[0], subfolder_range, file_range)
        elif version == version.DowIII_Version():
            args = unpack_from_stream(cls.__v9_LAYOUT, stream)
            subfolder_range = ArchiveRange(args[1], args[2])
            file_range = ArchiveRange(args[3], args[4])
            return FolderHeader(args[0], subfolder_range, file_range)
        else:
            raise NotImplementedError(version)

    def read_name(self, stream: BinaryIO, offset: ArchiveInfo) -> str:
        return read_name(stream, offset, self.name_offset)

    def read_name_from_lookup(self, lookup: Dict[int, str], info: Optional[ArchiveInfo] = None) -> str:
        # If info is provided; use absolute values
        if info:
            offset = info.sub_header.toc_offset + info.table_of_contents.filenames_info.offset_relative + self.name_offset
        else:
            offset = self.name_offset
        return lookup[offset]
