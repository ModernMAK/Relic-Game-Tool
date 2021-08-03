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
        folders: List['Folder'] = [None] * (info.last_sub - info.first_sub)
        files: List[File] = [None] * (info.last_filename - info.first_filename)
        return Folder(folders, files, info, name)

    def load_folders(self, folders: List['Folder']):
        if self._info.first_sub < len(folders):
            for i in range(self._info.first_sub, self._info.last_sub):
                i_0 = i - self._info.first_sub
                self.folders[i_0] = folders[i]

    def load_files(self, files: List['File']):
        if self._info.first_filename < len(files):
            for i in range(self._info.first_filename, self._info.last_filename):
                i_0 = i - self._info.first_filename
                self.files[i_0] = files[i]

    def walk(self) -> ArchiveWalkResult: # Specify name for
        return self._walk(self.name)