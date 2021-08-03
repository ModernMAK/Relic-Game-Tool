from dataclasses import dataclass
from typing import List, BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.description import Description
from relic.sga.file_header import FileHeader
from relic.sga.folder_header import FolderHeader


@dataclass
class SparseArchive:
    info: ArchiveInfo
    descriptions: List[Description]
    files: List[FileHeader]
    folders: List[FolderHeader]

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'SparseArchive':
        info = ArchiveInfo.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo) -> 'SparseArchive':
        version = archive_info.header.version
        desc_info = archive_info.table_of_contents.descriptions_info
        stream.seek(desc_info.offset_absolute, 0)
        descriptions = [Description.unpack(stream) for _ in range(desc_info.count)]

        fold_info = archive_info.table_of_contents.folders_info
        stream.seek(fold_info.offset_absolute, 0)
        folders = [FolderHeader.unpack(stream) for _ in range(fold_info.count)]

        file_info = archive_info.table_of_contents.files_info
        stream.seek(file_info.offset_absolute, 0)
        files = [FileHeader.unpack(stream, version) for _ in range(file_info.count)]

        return SparseArchive(archive_info, descriptions, files, folders)
