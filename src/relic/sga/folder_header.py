from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.archive_range import ArchiveRange
from relic.sga.shared import read_name
from relic.shared import unpack_from_stream


@dataclass
class FolderHeader:
    __FOLDER_HEADER_LAYOUT = Struct("< L H H H H")

    name_offset: int
    subfolder_range: ArchiveRange
    file_range: ArchiveRange

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'FolderHeader':
        args = unpack_from_stream(cls.__FOLDER_HEADER_LAYOUT, stream)
        subfolder_range = ArchiveRange(args[1], args[2])
        file_range = ArchiveRange(args[3], args[4])
        return FolderHeader(args[0], subfolder_range, file_range)

    def read_name(self, stream: BinaryIO, offset: ArchiveInfo) -> str:
        return read_name(stream, offset, self.name_offset)
