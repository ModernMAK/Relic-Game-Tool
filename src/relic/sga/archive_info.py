from dataclasses import dataclass
from typing import BinaryIO

from relic.sga.archive_header import ArchiveHeader
from relic.sga.data_offset_info import ArchiveSubHeader
from relic.sga.offset_info import OffsetInfo


# Saw this name in Corsix's writeup
#   Felt it was an apt description of this block of files
@dataclass
class ArchiveTableOfContents:  # 24 bytes
    # Knowing my luck this is also subject to change
    descriptions_info: OffsetInfo
    folders_info: OffsetInfo
    files_info: OffsetInfo
    filenames_info: OffsetInfo

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ArchiveTableOfContents':
        toc_offset = stream.tell()
        descriptions_info = OffsetInfo.unpack(stream, toc_offset)
        folders_info = OffsetInfo.unpack(stream, toc_offset)
        files_info = OffsetInfo.unpack(stream, toc_offset)
        filenames_info = OffsetInfo.unpack(stream, toc_offset)
        return ArchiveTableOfContents(descriptions_info, folders_info, files_info, filenames_info)


# Alias
ArchiveToC = ArchiveTableOfContents


@dataclass
class ArchiveInfo:
    header: ArchiveHeader
    sub_header: ArchiveSubHeader
    table_of_contents: ArchiveToC

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveInfo':
        header = ArchiveHeader.unpack(stream, read_magic=read_magic)
        sub_header = ArchiveSubHeader.unpack(stream, header.version)
        stream.seek(sub_header.toc_offset)
        toc = ArchiveToC.unpack(stream)
        return ArchiveInfo(header, sub_header, toc)
