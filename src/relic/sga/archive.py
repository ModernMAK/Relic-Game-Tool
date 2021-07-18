from dataclasses import dataclass
from typing import List, BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.description import Description
from relic.sga.file import File
from relic.sga.file_collection import FolderCollection, FileCollection
from relic.sga.folder import Folder
from relic.sga.sparse_archive import SparseArchive


@dataclass
class Archive(FolderCollection[Folder], FileCollection[File]):
    info: ArchiveInfo
    descriptions: List[Description]

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'Archive':
        info = SparseArchive.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive: SparseArchive) -> 'Archive':
        info = archive.info
        desc = archive.descriptions
        folders = [Folder.create(stream, info, f) for f in archive.folders]
        files = [File.create(stream, info, f) for f in archive.files]
        for f in folders:
            f.load_folders(folders)
            f.load_files(files)

        return Archive(files, folders, info, desc)

    @classmethod
    def repack(cls, stream: BinaryIO, write_magic:bool=True):
        raise NotImplementedError
