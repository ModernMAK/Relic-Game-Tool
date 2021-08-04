from dataclasses import dataclass
from typing import List, BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.virtual_drive_header import VirtualDriveHeader
from relic.sga.file import File
from relic.sga.file_collection import AbstractDirectory, ArchiveWalkResult
from relic.sga.folder import Folder
from relic.sga.sparse_archive import SparseArchive


@dataclass
class Archive(AbstractDirectory):
    info: ArchiveInfo
    virtual_drives: List[VirtualDriveHeader]

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
        name_lookup = info.table_of_contents.filenames_info.get_name_lookup(stream, use_absolute=False)
        folders = [Folder.create(f, name_lookup) for f in archive.folders]
        files = [File.create(stream, info, f, name_lookup) for f in archive.files]
        for f in folders:
            f.load_folders(folders)
            f.load_files(files)

        total_files = len(files)
        # In is expensive for large lists, so we use a 'flag' instead
        #   The 'flag' is actually a reference to the parent; not a bool
        folders = [f for f in folders if not f._parent]
        files = [f for f in files if not f._parent]

        return Archive(folders, files, info, desc, total_files)

    @classmethod
    def repack(cls, stream: BinaryIO, write_magic: bool = True):
        raise NotImplementedError

    def walk(self) -> ArchiveWalkResult:
        return self._walk("")
