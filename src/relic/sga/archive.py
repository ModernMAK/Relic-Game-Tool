from dataclasses import dataclass
from typing import List, BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.description import Description
from relic.sga.file import File
from relic.sga.file_collection import AbstractDirectory
from relic.sga.folder import Folder
from relic.sga.sparse_archive import SparseArchive


@dataclass
class Archive(AbstractDirectory):
    info: ArchiveInfo
    descriptions: List[Description]

    # A helper to know the total # of files without performing a full walk
    _total_files: int = 0

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
        parented_folders = []
        parented_files = []
        for f in folders:
            f.load_folders(folders)
            parented_folders.extend(f.folders)
            f.load_files(files)
            parented_files.extend(f.files)

        total_files = len(files)
        folders = [f for f in folders if f not in parented_folders]
        files = [f for f in files if f not in parented_files]

        return Archive(folders, files, info, desc, total_files)

    @classmethod
    def repack(cls, stream: BinaryIO, write_magic: bool = True):
        raise NotImplementedError
