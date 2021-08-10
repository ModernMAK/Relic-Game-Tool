from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO, Dict, Optional, List

from relic.sga.archive_header import ArchiveInfo
from relic.sga.shared import ArchiveRange, Version, SgaVersion
from relic.sga.file import File
from relic.sga.file_collection import AbstractDirectory, ArchiveWalkResult
from relic.shared import unpack_from_stream
from relic.util.struct_util import pack_into_stream


@dataclass
class FolderHeader:
    __v2_LAYOUT = Struct("< L 4H")  # 12
    __v5_LAYOUT = __v2_LAYOUT  # 12
    __v9_LAYOUT = Struct("< L 4L")  # 20
    __LAYOUT = {SgaVersion.Dow:__v2_LAYOUT, SgaVersion.Dow2:__v5_LAYOUT,SgaVersion.Dow3:__v9_LAYOUT}

    name_offset: int
    subfolder_range: ArchiveRange
    file_range: ArchiveRange

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version) -> 'FolderHeader':
        if version in [SgaVersion.Dow, SgaVersion.Dow2]:
            args = unpack_from_stream(cls.__v2_LAYOUT, stream)
            subfolder_range = ArchiveRange(args[1], args[2])
            file_range = ArchiveRange(args[3], args[4])
            return FolderHeader(args[0], subfolder_range, file_range)
        elif version == SgaVersion.Dow3:
            args = unpack_from_stream(cls.__v9_LAYOUT, stream)
            subfolder_range = ArchiveRange(args[1], args[2])
            file_range = ArchiveRange(args[3], args[4])
            return FolderHeader(args[0], subfolder_range, file_range)
        else:
            raise NotImplementedError(version)

    def pack(self, stream: BinaryIO, version: Version) -> int:
        args = self.name_offset, self.subfolder_range.start, self.subfolder_range.end, \
               self.file_range.start, self.file_range.end
        if version in self.__LAYOUT:
            layout = self.__LAYOUT[version]
        else:
            raise NotImplementedError(version)

        return pack_into_stream(layout, stream, *args)


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
    _parent_folder: Optional['Folder'] = None
    _parent_drive: Optional['VirtualDrive'] = None

    @classmethod
    def create(cls, info: FolderHeader, name_lookup: Dict[int, str]) -> 'Folder':
        name = info.read_name_from_lookup(name_lookup)
        folders: List['Folder'] = [None] * info.subfolder_range.size
        files: List[File] = [None] * info.file_range.size
        return Folder(folders, files, None, None, info, name)

    def load_folders(self, folders: List['Folder']):
        if self._info.subfolder_range.start < len(folders):
            for i in self._info.subfolder_range:
                i_0 = i - self._info.subfolder_range.start
                self.folders[i_0] = folders[i]
                folders[i]._parent_folder = self.folders[i_0]

    def load_files(self, files: List['File']):
        if self._info.file_range.start < len(files):
            for i in self._info.file_range:
                i_0 = i - self._info.file_range.start
                self.files[i_0] = files[i]
                files[i]._parent_folder = self.files[i_0]

    def walk(self) -> ArchiveWalkResult:  # Specify name for
        return self._walk(self.name)
