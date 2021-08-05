from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO, List
from relic.sga.file import File
from relic.sga.file_collection import AbstractDirectory, ArchiveWalkResult
from relic.sga.folder import Folder
from relic.sga.shared import Version, ArchiveRange, DowI_Version, DowII_Version, DowIII_Version
from relic.shared import unpack_from_stream


# Are there ever more than one V-Drives?
# Looking at a lua script: the path was structured as 'data:path-to-file'
# Therefore, a 'VirtualDrive' seems more descriptive, RootFolders would also work I suppose
#   I stuck to V-Drive since this does function differently
@dataclass
class VirtualDriveHeader:
    __v2_LAYOUT = Struct("< 64s 64s 5H")
    __v5_LAYOUT = __v2_LAYOUT
    __v9_LAYOUT = Struct("< 64s 64s 5L")

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
    unk_a5: int  # 0

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version) -> 'VirtualDriveHeader':
        if version == DowIII_Version:
            args = unpack_from_stream(cls.__v9_LAYOUT, stream)
        elif version in [DowII_Version, DowI_Version]:
            args = unpack_from_stream(cls.__v2_LAYOUT, stream)
        else:
            raise NotImplementedError(version)

        category = args[0].decode("ascii").rstrip("\x00")
        name = args[1].decode("ascii").rstrip("\x00")
        subfolder_range = ArchiveRange(args[2], args[3])
        file_range = ArchiveRange(args[4], args[5])
        assert args[6] == args[2], args[2:]
        return VirtualDriveHeader(category, name, subfolder_range, file_range, args[6])

    # def pack(self, stream: BinaryIO) -> int:
    #     args = (self.drive_name, self.name, self.unk_a1, self.folder_count, self.unk_a3)
    #     return pack_into_stream(self.__DESC_LAYOUT, stream, *args)


@dataclass
class VirtualDrive(AbstractDirectory):
    path: str
    name: str
    _info: VirtualDriveHeader

    @classmethod
    def create(cls, header: VirtualDriveHeader):
        path, name = header.path, header.name
        folders: List[Folder] = [None] * header.subfolder_range.size
        files: List[File] = [None] * header.file_range.size
        return VirtualDrive(folders, files, path, name, header)

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
        for root, folders, files in self._walk():
            return f"{self.path}:{root}", folders, files
