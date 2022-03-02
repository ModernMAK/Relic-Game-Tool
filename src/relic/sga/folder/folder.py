from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, List, Optional, TYPE_CHECKING

from ..hierarchy import DriveChild, FolderCollection, FileCollection, FolderChild, walk

if TYPE_CHECKING:
    from ..file.file import File
    from ..toc.toc import ArchiveTableOfContents
    from ..vdrive.virtual_drive import VirtualDrive
    from .header import FolderHeader
    from ..hierarchy import ArchiveWalk


@dataclass
class Folder(FolderCollection, FileCollection, FolderChild, DriveChild):
    header: FolderHeader
    name: str

    def __init__(self, header: FolderHeader, name: str, sub_folders: List[Folder], files: List[File], parent_folder: Optional[Folder] = None, drive: Optional[VirtualDrive] = None):
        self.header = header
        self.name = name
        self.sub_folders = sub_folders
        self.files = files
        self._drive = drive
        self._parent = parent_folder

    @property
    def full_path(self) -> PurePosixPath:
        if self._drive:
            return self._drive.full_path / self.name
        else:
            return PurePosixPath(self.name)

    def walk(self) -> ArchiveWalk:
        return walk(self)

    @classmethod
    def create(cls, header: FolderHeader) -> Folder:
        name = None
        folders = [None] * header.sub_folder_range.size
        files = [None] * header.file_range.size
        # noinspection PyTypeChecker
        return Folder(header, name, folders, files)

    def load_toc(self, toc: ArchiveTableOfContents):
        self.load_folders(toc.folders)
        self.load_files(toc.files)
        self.load_name_from_lookup(toc.names)

    def load_name_from_lookup(self, name_lookup: Dict[int, str]):
        self.name = name_lookup[self.header.name_offset]

    def load_folders(self, folders: List[Folder]):
        if self.header.sub_folder_range.start < len(folders):
            for folder_index in self.header.sub_folder_range:
                sub_folder_index = folder_index - self.header.sub_folder_range.start
                f = self.sub_folders[sub_folder_index] = folders[folder_index]
                f._parent = self

    def load_files(self, files: List[File]):
        if self.header.file_range.start < len(files):
            for file_index in self.header.file_range:
                sub_file_index = file_index - self.header.file_range.start
                f = self.files[sub_file_index] = files[file_index]
                f._parent = self
