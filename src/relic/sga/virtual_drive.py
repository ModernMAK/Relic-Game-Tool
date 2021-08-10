from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO, List, Optional
from relic.sga.file import File
from relic.sga.file_collection import AbstractDirectory, ArchiveWalkResult
from relic.sga.folder import Folder
from relic.sga.shared import Version, ArchiveRange, SgaVersion
from relic.shared import unpack_from_stream

# Are there ever more than one V-Drives?
# Looking at a lua script: the path was structured as 'data:path-to-file'
# Therefore, a 'VirtualDrive' seems more descriptive, RootFolders would also work I suppose
#   I stuck to V-Drive since this does function differently
from relic.util.struct_util import pack_into_stream


@dataclass
class VirtualDriveHeader:
    __v2_LAYOUT = Struct("< 64s 64s 5H")
    __v5_LAYOUT = __v2_LAYOUT
    __v9_LAYOUT = Struct("< 64s 64s 5L")
    __LAYOUT = {SgaVersion.Dow: __v2_LAYOUT, SgaVersion.Dow2: __v5_LAYOUT, SgaVersion.Dow3: __v9_LAYOUT}
    # Th path of the drive (used in resolving archive paths)
    # E.G. 'data'
    path: str
    # The name of the drive (used in viewing assets?)
    # E.G. 'All'
    name: str
    # If this is a root folder; I bet this is first & last; just like Folder
    # first_subfolder: int
    # last_subfolder: int
    # first_file: int
    # last_file: int

    subfolder_range: ArchiveRange
    file_range: ArchiveRange
    # Special field for V_Drive, flags maybe?
    unk_a: int  # 0

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version) -> 'VirtualDriveHeader':
        if version in cls.__LAYOUT:
            args = unpack_from_stream(cls.__LAYOUT[version], stream)
        else:
            raise NotImplementedError(version)

        category = args[0].decode("ascii").rstrip("\x00")
        name = args[1].decode("ascii").rstrip("\x00")
        subfolder_range = ArchiveRange(args[2], args[3])
        file_range = ArchiveRange(args[4], args[5])
        assert args[6] == args[2], args[2:]
        return VirtualDriveHeader(category, name, subfolder_range, file_range, args[6])

    def pack(self, stream: BinaryIO, version: Version) -> int:
        if version in self.__LAYOUT:
            layout = self.__LAYOUT[version]
        else:
            raise NotImplementedError(version)
        args = self.path, self.name, self.subfolder_range.start, self.subfolder_range.end, \
               self.file_range.start, self.file_range.end, self.unk_a
        return pack_into_stream(layout, stream, *args)




@dataclass
class VirtualDrive(AbstractDirectory):
    path: str
    name: str
    _info: VirtualDriveHeader


    @classmethod
    def create(cls, header: VirtualDriveHeader):
        path, name = header.path, header.name
        return VirtualDrive([], [], None, None, path, name, header)

    def load_folders(self, folders: List['Folder']):
        if self._info.subfolder_range.start < len(folders):
            for i in self._info.subfolder_range:
                if not folders[i]._parent_folder:
                    f = folders[i]
                    f._parent_drive = self
                    self.folders.append(f)

    def load_files(self, files: List['File']):
        if self._info.file_range.start < len(files):
            for i in self._info.file_range:
                if not files[i]._parent_folder:
                    f = files[i]
                    f._parent_drive = self
                    self.folders.append(f)

    def walk(self, specify_drive: bool = True) -> ArchiveWalkResult:  # Specify name for
        for root, folders, files in self._walk():
            true_root = f"{self.path}:{root}" if specify_drive else root
            yield true_root, folders, files

    # def build_header(self, ):
