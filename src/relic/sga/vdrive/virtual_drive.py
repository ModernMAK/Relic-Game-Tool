from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import List, TYPE_CHECKING

from ..hierarchy import FileCollection, FolderCollection, ArchiveWalk, walk

if TYPE_CHECKING:
    from ..file.file import File
    from ..folder.folder import Folder
    from ..vdrive.header import VirtualDriveHeader
    from ..toc.toc import ArchiveTableOfContents


@dataclass
class VirtualDrive(FolderCollection, FileCollection):
    header: VirtualDriveHeader

    def __init__(self, header: VirtualDriveHeader, sub_folders: List[Folder], files: List[File]):
        self.header = header
        self.sub_folders = sub_folders
        self.files = files

    @property
    def path(self) -> str:
        return self.header.path

    @property
    def name(self) -> str:
        return self.header.name

    def walk(self) -> ArchiveWalk:
        return walk(self)

    @property
    def full_path(self) -> PurePosixPath:
        return PurePosixPath(self.path + ":")

    @classmethod
    def create(cls, header: VirtualDriveHeader) -> VirtualDrive:
        folders = [None] * header.sub_folder_range.size
        files = [None] * header.file_range.size
        # noinspection PyTypeChecker
        return VirtualDrive(header, folders, files)

    def load_toc(self, toc: ArchiveTableOfContents):
        self.load_folders(toc.folders)
        self.load_files(toc.files)

    def load_folders(self, folders: List[Folder]):
        if self.header.sub_folder_range.start < len(folders):
            for folder_index in self.header.sub_folder_range:
                sub_folder_index = folder_index - self.header.sub_folder_range.start
                f = self.sub_folders[sub_folder_index] = folders[folder_index]
                f._drive = self

    def load_files(self, files: List[File]):
        if self.header.file_range.start < len(files):
            for file_index in self.header.file_range:
                sub_file_index = file_index - self.header.file_range.start
                f = self.files[sub_file_index] = files[file_index]
                f._drive = self

    def build_tree(self):
        self.sub_folders = [f for f in self.sub_folders if not f._parent]
        self.files = [f for f in self.files if not f._parent]
