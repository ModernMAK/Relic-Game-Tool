from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO, Dict, Optional, List

from relic.sga.archive_header import ArchiveInfo
from relic.sga.shared import ArchiveRange, Version, DowIII_Version, DowII_Version, DowI_Version
from relic.sga.file import File
from relic.sga.file_collection import AbstractDirectory, ArchiveWalkResult
from relic.shared import unpack_from_stream


@dataclass
class FolderHeader:
    __v2_LAYOUT = Struct("< L 4H")  # 12
    __v5_LAYOUT = __v2_LAYOUT  # 12
    __v9_LAYOUT = Struct("< L 4L")  # 20

    name_offset: int
    subfolder_range: ArchiveRange
    file_range: ArchiveRange

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version) -> 'FolderHeader':
        if version in [DowI_Version, DowII_Version]:
            args = unpack_from_stream(cls.__v2_LAYOUT, stream)
            subfolder_range = ArchiveRange(args[1], args[2])
            file_range = ArchiveRange(args[3], args[4])
            return FolderHeader(args[0], subfolder_range, file_range)
        elif version == DowIII_Version:
            args = unpack_from_stream(cls.__v9_LAYOUT, stream)
            subfolder_range = ArchiveRange(args[1], args[2])
            file_range = ArchiveRange(args[3], args[4])
            return FolderHeader(args[0], subfolder_range, file_range)
        else:
            raise NotImplementedError(version)

    def read_name_from_lookup(self, lookup: Dict[int, str], info: Optional[ArchiveInfo] = None) -> str:
        # If info is provided; use absolute values
        if info:
            offset = info.sub_header.toc_offset + info.table_of_contents.filenames_info.offset_relative + self.name_offset
        else:
            offset = self.name_offset
        return lookup[offset]

@dataclass
class Folder(AbstractDirectory):
    _info: FolderHeader
    name: str
    _parent:Optional['Folder'] = None


    @classmethod
    def create(cls, info: FolderHeader, name_lookup:Dict[int, str]) -> 'Folder':
        name = info.read_name_from_lookup(name_lookup)
        folders: List['Folder'] = [None] * info.subfolder_range.size
        files: List[File] = [None] * info.file_range.size
        return Folder(folders, files, info, name)

    def load_folders(self, folders: List['Folder']):
        if self._info.subfolder_range.start < len(folders):
            for i in self._info.subfolder_range:
                i_0 = i - self._info.subfolder_range.start
                self.folders[i_0] = folders[i]
                folders[i]._parent = self.folders[i_0]

    def load_files(self, files: List['File']):
        if self._info.file_range.start < len(files):
            for i in self._info.file_range:
                i_0 = i - self._info.file_range.start
                self.files[i_0] = files[i]
                files[i]._parent = self.files[i_0]

    def walk(self) -> ArchiveWalkResult:  # Specify name for
        return self._walk(self.name)
