from dataclasses import dataclass
from typing import List, BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.description import Description
from relic.sga.file_collection import FileCollection, FolderCollection
from relic.sga.file_header import FileHeader
from relic.sga.folder_header import FolderHeader


@dataclass
class SparseArchive(FolderCollection[FolderHeader], FileCollection[FileHeader]):
    info: ArchiveInfo
    descriptions: List[Description]

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'SparseArchive':
        info = ArchiveInfo.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo) -> 'SparseArchive':
        stream.seek(archive_info.descriptions_info.offset_absolute, 0)
        descriptions = [Description.unpack(stream) for _ in range(archive_info.descriptions_info.count)]

        stream.seek(archive_info.folders_info.offset_absolute, 0)
        folders = [FolderHeader.unpack(stream) for _ in range(archive_info.folders_info.count)]

        stream.seek(archive_info.files_info.offset_absolute, 0)
        files = [FileHeader.unpack(stream) for _ in range(archive_info.files_info.count)]

        return SparseArchive(files, folders,  archive_info, descriptions)
