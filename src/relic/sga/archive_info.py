from dataclasses import dataclass
from typing import BinaryIO

from relic.sga.archive_header import ArchiveHeader
from relic.sga.data_offset_info import DataOffsetInfo
from relic.sga.offset_info import OffsetInfo


@dataclass
class ArchiveInfo:
    header: ArchiveHeader
    data_info: DataOffsetInfo
    descriptions_info: OffsetInfo
    folders_info: OffsetInfo
    files_info: OffsetInfo
    filenames_info: OffsetInfo

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveInfo':
        header = ArchiveHeader.unpack(stream, read_magic=read_magic)
        data_info = DataOffsetInfo.unpack(stream)
        descriptions_info = OffsetInfo.unpack(stream)
        folders_info = OffsetInfo.unpack(stream)
        files_info = OffsetInfo.unpack(stream)
        filenames_info = OffsetInfo.unpack(stream)
        return ArchiveInfo(header, data_info, descriptions_info, folders_info, files_info, filenames_info)
