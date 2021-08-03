from dataclasses import dataclass
from typing import List, BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.file import File
from relic.sga.file_collection import AbstractDirectory, ArchiveWalkResult  # FileCollection, FolderCollection,
from relic.sga.folder_header import FolderHeader


@dataclass
class Folder(AbstractDirectory):
    _info: FolderHeader
    name: str

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: FolderHeader) -> 'Folder':
        name = info.read_name(stream, archive_info)
        folders: List['Folder'] = [None] * info.subfolder_range.size
        files: List[File] = [None] * info.file_range.size
        return Folder(folders, files, info, name)

    def load_folders(self, folders: List['Folder']):
        if self._info.subfolder_range.start < len(folders):
            for i in self._info.subfolder_range:
                i_0 = i - self._info.subfolder_range.start
                self.folders[i_0] = folders[i]

    def load_files(self, files: List['File']):
        if self._info.file_range.start < len(files):
            for i in self._info.file_range:
                i_0 = i - self._info.file_range.start
                self.files[i_0] = files[i]

    def walk(self) -> ArchiveWalkResult:  # Specify name for
        return self._walk(self.name)
