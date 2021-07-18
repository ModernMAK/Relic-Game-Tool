from dataclasses import dataclass
from typing import List, BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.description import Description
from relic.sga.sparse_file import SparseFile
from relic.sga.sparse_foler import SparseFolder


@dataclass
class SparseArchive:
    info: ArchiveInfo
    descriptions: List[Description]
    folders: List[SparseFolder]
    files: List[SparseFile]

    # names: List[str]

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic:bool=True) -> 'SparseArchive':
        info = ArchiveInfo.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo) -> 'SparseArchive':
        stream.seek(archive_info.descriptions_info.offset_absolute, 0)
        descriptions = [Description.unpack(stream) for _ in range(archive_info.descriptions_info.count)]

        stream.seek(archive_info.folders_info.offset_absolute, 0)
        folders = [SparseFolder.unpack(stream) for _ in range(archive_info.folders_info.count)]

        stream.seek(archive_info.files_info.offset_absolute, 0)
        files = [SparseFile.unpack(stream) for _ in range(archive_info.files_info.count)]

        return SparseArchive(archive_info, descriptions, folders, files)

