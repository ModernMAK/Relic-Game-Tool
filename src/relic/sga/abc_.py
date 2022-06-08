from __future__ import annotations

import zlib
from abc import ABC
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import List, BinaryIO, Optional, Dict, ClassVar, Tuple, Type

from serialization_tools.ioutil import Ptr, WindowPtr
from serialization_tools.size import KiB
from serialization_tools.structx import Struct

# import relic.sga.io
from relic.common import VersionLike
from relic.sga.common import ArchiveRange, ArchiveVersion
# from relic.sga.io import walk
from relic.sga.protocols import ArchiveHeader, Archive, FileCollection, FolderCollection, Folder, File, VirtualDrive, ArchiveWalk

_NULL = b"\0"
_BUFFER_SIZE = 64 * KiB


def walk(self):
    raise NotImplementedError  # Currently causes cyclic dependencies; needs a fix


@dataclass
class ArchiveTableOfContentsABC:
    drives: List[VirtualDriveABC]
    folders: List[FolderABC]
    files: List[FileABC]
    names: Dict[int, str]

    @classmethod
    def create(cls, toc_headers: ArchiveTableOfContentsHeadersABC) -> ArchiveTableOfContentsABC:

        drives = [VirtualDriveABC.create(header) for header in toc_headers.drives]
        folders = [FolderABC.create(header) for header in toc_headers.folders]
        files = [FileABC.create(header) for header in toc_headers.files]

        return ArchiveTableOfContentsABC(drives, folders, files, toc_headers.names)

    def load_data(self, stream: BinaryIO):
        for _ in self.files:
            _.load_data(stream)

    def load_toc(self):
        for _ in self.drives:
            _.load_toc(self)
        for _ in self.folders:
            _.load_toc(self)
        for _ in self.files:
            _.load_toc(self)

    def build_tree(self):
        for _ in self.drives:
            _.build_tree()


@dataclass
class ArchiveTableOfContentsHeadersABC:
    drives: List[VirtualDriveHeaderABC]
    folders: List[FolderHeaderABC]
    files: List[FileHeaderABC]
    names: Dict[int, str]
    VDRIVE_HEADER_CLS: ClassVar[Type[VirtualDriveHeaderABC]]
    FOLDER_HEADER_CLS: ClassVar[Type[FolderHeaderABC]]
    FILE_HEADER_CLS: ClassVar[Type[FileHeaderABC]]

    @classmethod
    def old_unpack(cls, stream: BinaryIO, ptr: ArchiveTableOfContentsPtrABC, version: VersionLike = None) -> ArchiveTableOfContentsHeadersABC:
        version = version or ptr.version  # abusing the fact that the classes know their own version to avoid explicitly passing it in

        local_ptr = ptr.virtual_drive_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            virtual_drives = [VirtualDriveHeaderABC.old_unpack(handle, version) for _ in range(local_ptr.count)]

        local_ptr = ptr.folder_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            folders = [FolderHeaderABC.old_unpack(handle, version) for _ in range(local_ptr.count)]

        local_ptr = ptr.file_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            files = [FileHeaderABC.old_unpack(handle, version) for _ in range(local_ptr.count)]

        # This gets a bit wierd
        local_ptr = ptr.name_ptr
        names: Dict[int, str] = {}
        with local_ptr.stream_jump_to(stream) as handle:
            start = stream.tell()  # use stream to avoid invalidating window
            while len(names) < local_ptr.count:
                remaining = local_ptr.count - len(names)
                current = stream.tell()  # Get relative pos to start
                buffer = handle.read(_BUFFER_SIZE)
                terminal_null = buffer.endswith(_NULL)
                parts = buffer.split(_NULL, remaining)

                offset = 0
                for i, p in enumerate(parts):
                    if i == len(parts) - 1:
                        break
                    names[current - start + offset] = p.decode("ascii")
                    offset += len(p) + 1  # +1 to include null terminal

                if not terminal_null:
                    stream.seek(current + offset)

        return ArchiveTableOfContentsHeadersABC(virtual_drives, folders, files, names)

    @classmethod
    def unpack(cls, stream: BinaryIO, ptr: ArchiveTableOfContentsPtrABC) -> ArchiveTableOfContentsHeadersABC:
        local_ptr = ptr.virtual_drive_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            virtual_drives = [cls.VDRIVE_HEADER_CLS.unpack(handle) for _ in range(local_ptr.count)]

        local_ptr = ptr.folder_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            folders = [cls.FOLDER_HEADER_CLS.unpack(handle) for _ in range(local_ptr.count)]

        local_ptr = ptr.file_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            files = [cls.FILE_HEADER_CLS.unpack(handle) for _ in range(local_ptr.count)]

        # This gets a bit wierd
        local_ptr = ptr.name_ptr
        names: Dict[int, str] = {}
        with local_ptr.stream_jump_to(stream) as handle:
            start = stream.tell()  # use stream to avoid invalidating window
            while len(names) < local_ptr.count:
                remaining = local_ptr.count - len(names)
                current = stream.tell()  # Get relative pos to start
                buffer = handle.read(_BUFFER_SIZE)
                terminal_null = buffer.endswith(_NULL)
                parts = buffer.split(_NULL, remaining)

                offset = 0
                for i, p in enumerate(parts):
                    if i == len(parts) - 1:
                        break
                    names[current - start + offset] = p.decode("ascii")
                    offset += len(p) + 1  # +1 to include null terminal

                if not terminal_null:
                    stream.seek(current + offset)

        return ArchiveTableOfContentsHeadersABC(virtual_drives, folders, files, names)


@dataclass
class TocItemPtrABC(Ptr):
    def __init__(self, offset: int, count: int, whence: int = 0):
        super().__init__(offset, whence)
        self.count = count


@dataclass
class ArchiveTableOfContentsPtrABC:
    # Virtual Drives (offset, count), Folder (offset, count), File (offset, count), Names (offset, count)
    LAYOUT: ClassVar[Struct]
    virtual_drive_ptr: TocItemPtrABC
    folder_ptr: TocItemPtrABC
    file_ptr: TocItemPtrABC
    name_ptr: TocItemPtrABC

    @property
    def version(self) -> ArchiveVersion:
        raise NotImplementedError

    @classmethod
    def _unpack_tuple(cls, stream: BinaryIO) -> Tuple[TocItemPtrABC, TocItemPtrABC, TocItemPtrABC, TocItemPtrABC]:
        vd_offset, vd_count, fold_offset, fold_count, file_offset, file_count, name_offset, name_count = cls.LAYOUT.unpack_stream(stream)
        vd_ptr = TocItemPtrABC(vd_offset, vd_count)
        fold_ptr = TocItemPtrABC(fold_offset, fold_count)
        file_ptr = TocItemPtrABC(file_offset, file_count)
        name_ptr = TocItemPtrABC(name_offset, name_count)
        return vd_ptr, fold_ptr, file_ptr, name_ptr

    def _pack_tuple(self) -> Tuple[int, int, int, int, int, int, int, int]:
        return self.virtual_drive_ptr.offset, self.virtual_drive_ptr.count, \
               self.folder_ptr.offset, self.folder_ptr.count, \
               self.file_ptr.offset, self.file_ptr.count, \
               self.name_ptr.offset, self.name_ptr.count

    @classmethod
    def unpack_version(cls, stream: BinaryIO, version: VersionLike) -> 'ArchiveTableOfContentsPtrABC':
        raise TypeError("Use APIs[version].ArchiveTableOfContentsPtr.unpack(stream)")
        # toc_ptr_class = _ToCPtr_VERSION_MAP.get(version)
        #
        # if not toc_ptr_class:
        #     raise NotImplementedError(version)
        #
        # return relic.sga.io.unpack_archive(stream)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ArchiveTableOfContentsPtrABC':
        args = cls._unpack_tuple(stream)
        return cls(*args)

    def pack(self, stream: BinaryIO) -> int:
        args = self._pack_tuple()
        return self.LAYOUT.pack_stream(stream, *args)

    def __str__(self):
        parts = [f"{k}={v}" for k, v in self.__dict__.items()]
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def __repr__(self):
        return str(self)


@dataclass
class ArchiveHeaderABC(ArchiveHeader, ABC):
    name: str
    toc_ptr: Ptr
    data_ptr: WindowPtr


@dataclass
class ArchiveABC(Archive):
    header: ArchiveHeader
    """Sparse represents whether data was loaded on creation."""
    _sparse: bool

    def __init__(self, header: ArchiveHeader, drives: List[VirtualDriveABC], _sparse: bool):
        self.header = header
        self._sparse = _sparse
        self.drives = drives

    def walk(self) -> ArchiveWalk:
        return walk(self)

    TOC_PTR_CLS: ClassVar[Type[ArchiveToCPtrABC]] = ArchiveTableOfContentsPtrABC
    TOC_HEADERS_CLS: ClassVar[Type[ArchiveTableOfContentsHeadersABC]] = ArchiveTableOfContentsHeadersABC
    TOC_CLS: ClassVar[Type[ArchiveTableOfContentsABC]] = ArchiveTableOfContentsABC

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ArchiveHeader, sparse: bool = True):
        # version = header.version
        with header.toc_ptr.stream_jump_to(stream) as handle:
            toc_ptr = cls.TOC_PTR_CLS.unpack(handle)
            toc_headers = cls.TOC_HEADERS_CLS.unpack(handle, toc_ptr)
            toc = cls.TOC_CLS.create(toc_headers)

        toc.load_toc()
        toc.build_tree()  # ensures walk is unique; avoiding dupes and speeding things up
        if not sparse:
            with header.data_ptr.stream_jump_to(stream) as handle:
                toc.load_data(handle)

        return cls(header, toc.drives, sparse)

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        raise NotImplementedError


@dataclass
class FileABC(File):
    header: FileHeaderABC
    name: str
    data: Optional[bytes] = None
    _decompressed: bool = False
    parent_folder: Optional[FolderABC] = None
    parent_drive: Optional[VirtualDriveABC] = None

    @property
    def data_loaded(self) -> bool:
        return self.data is not None

    @property
    def expects_decompress(self) -> bool:
        return self.header.compressed

    @property
    def decompressed(self) -> bool:
        if self.data_loaded:
            return self._decompressed or not self.expects_decompress
        else:
            return False

    @property
    def full_path(self) -> PurePosixPath:
        if self.parent_folder:
            return self.parent_folder.full_path / self.name
        elif self.parent_drive:
            return self.parent_drive.full_path / self.name
        else:
            return PurePosixPath(self.name)

    @classmethod
    def create(cls, header: FileHeaderABC) -> FileABC:
        _decompressed = False
        # noinspection PyTypeChecker
        return FileABC(header, None, None, _decompressed)

    def load_name_from_lookup(self, name_lookup: Dict[int, str]):
        self.name = name_lookup[self.header.name_sub_ptr.offset]

    def load_toc(self, toc: ArchiveTableOfContentsABC):
        self.load_name_from_lookup(toc.names)

    def read_data(self, stream: BinaryIO, decompress: bool = False) -> bytes:
        with self.header.data_sub_ptr.stream_jump_to(stream) as handle:
            buffer = handle.read(self.header.compressed_size)
            if decompress and self.expects_decompress:
                return zlib.decompress(buffer)
            else:
                return buffer

    def load_data(self, stream: BinaryIO, decompress: bool = False):
        self.data = self.read_data(stream, decompress)
        self._decompressed = decompress

    def get_decompressed_data(self) -> bytes:
        if self.decompressed:
            return self.data
        else:
            # zlib_header = Struct("2B").unpack(self.data[:2])
            # full_zlib_header = (zlib_header[0] & 0xF0) >> 4, zlib_header[0] & 0xF, \
            #                    (zlib_header[1] & 0b11000000) >> 6, (zlib_header[1] >> 5) & 0b1, zlib_header[1] & 0b11111
            # convert = {7: 32, 6: 16}
            # assert convert[full_zlib_header[0]] == self.header.compression_flag.value
            return zlib.decompress(self.data)

    def decompress(self):
        self.data = self.get_decompressed_data()
        self._decompressed = True


@dataclass
class FileHeaderABC:
    LAYOUT: ClassVar[Struct]
    name_sub_ptr: Ptr  # Sub ptr is expected to be used via window (E.G. 'WindowPtr() as handle', then, 'data_sub_ptr.stream_jump_to(handle)')
    data_sub_ptr: Ptr
    decompressed_size: int
    compressed_size: int

    def __eq__(self, other):
        # TODO ptr equality
        return self.decompressed_size == other.decompressed_size and self.compressed_size == other.compressed_size

    @property
    def compressed(self):
        raise NotImplementedError

    @classmethod
    def unpack(cls, stream: BinaryIO) -> FileHeaderABC:
        raise NotImplementedError

    def pack(self, stream: BinaryIO) -> int:
        raise NotImplementedError

    @classmethod
    def old_unpack(cls, stream: BinaryIO, version: VersionLike) -> FileHeaderABC:
        raise TypeError("Use APIs[version].FileHeader.unpack(stream)")
        # _VERSION_MAP = None  # TODO move to IO
        # header_class = _FILE_HEADER_VERSION_MAP.get(version)
        #
        # if not header_class:
        #     raise NotImplementedError(version)
        #
        # return header_class.old_unpack(stream)


@dataclass
class FolderCollectionABC(FolderCollection):
    sub_folders: List[Folder]


@dataclass
class FileCollectionABC(FileCollection):
    files: List[File]


@dataclass
class FolderChild:
    parent_folder: Optional[Folder]


@dataclass
class DriveChild:
    parent_drive: Optional[VirtualDrive]


@dataclass
class FolderABC(Folder, FolderCollectionABC, FileCollectionABC, FolderChild, DriveChild):
    header: FolderHeaderABC
    name: str

    def __init__(self, header: FolderHeaderABC, name: str, sub_folders: List[FolderABC], files: List[FileABC], parent_folder: Optional[FolderABC] = None, drive: Optional[VirtualDriveABC] = None):
        self.header = header
        self.name = name
        self.sub_folders = sub_folders
        self.files = files
        self.parent_drive = drive
        self.parent_folder = parent_folder

    @property
    def full_path(self) -> PurePosixPath:
        if self.parent_drive:
            return self.parent_drive.full_path / self.name
        else:
            return PurePosixPath(self.name)

    def walk(self) -> ArchiveWalk:
        return walk(self)

    @classmethod
    def create(cls, header: FolderHeaderABC) -> FolderABC:
        name = None
        folders = [None] * header.sub_folder_range.size
        files = [None] * header.file_range.size
        # noinspection PyTypeChecker
        return FolderABC(header, name, folders, files)

    def load_toc(self, toc: ArchiveTableOfContentsABC):
        self.load_folders(toc.folders)
        self.load_files(toc.files)
        self.load_name_from_lookup(toc.names)

    def load_name_from_lookup(self, name_lookup: Dict[int, str]):
        self.name = name_lookup[self.header.name_offset]

    def load_folders(self, folders: List[FolderABC]):
        if self.header.sub_folder_range.start < len(folders):
            for folder_index in self.header.sub_folder_range:
                sub_folder_index = folder_index - self.header.sub_folder_range.start
                f = self.sub_folders[sub_folder_index] = folders[folder_index]
                f.parent_folder = self

    def load_files(self, files: List[FileABC]):
        if self.header.file_range.start < len(files):
            for file_index in self.header.file_range:
                sub_file_index = file_index - self.header.file_range.start
                f = self.files[sub_file_index] = files[file_index]
                f.parent_folder = self


@dataclass
class FolderHeaderABC:
    LAYOUT: ClassVar[Struct]

    name_offset: int
    sub_folder_range: ArchiveRange
    file_range: ArchiveRange

    @classmethod
    def old_unpack(cls, stream: BinaryIO, version: VersionLike) -> 'FolderHeaderABC':
        raise TypeError("Use APIs[version].FolderHeader.unpack(stream)")
        # header_class = _FOLDER_HEADER_VERSION_MAP.get(version)
        #
        # if not header_class:
        #     raise NotImplementedError(version)
        #
        # return header_class.unpack(stream)

    def pack(self, stream: BinaryIO) -> int:
        args = self.name_offset, self.sub_folder_range.start, self.sub_folder_range.end, \
               self.file_range.start, self.file_range.end
        return self.LAYOUT.pack_stream(stream, *args)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'FolderHeaderABC':
        name_offset, sub_folder_start, sub_folder_end, file_start, file_end = cls.LAYOUT.unpack_stream(stream)
        sub_folder_range = ArchiveRange(sub_folder_start, sub_folder_end)
        file_range = ArchiveRange(file_start, file_end)
        return cls(name_offset, sub_folder_range, file_range)


@dataclass
class VirtualDriveHeaderABC:
    LAYOUT: ClassVar[Struct]

    path: str
    name: str

    sub_folder_range: ArchiveRange
    file_range: ArchiveRange
    unk: bytes

    @classmethod
    def old_unpack(cls, stream: BinaryIO, version: VersionLike) -> 'VirtualDriveHeaderABC':
        raise TypeError("Use APIs[version].VirtualDriveHeader.unpack(stream)")
        # header_class = _VIRTUAL_DRIVE_HEADER_VERSION_MAP.get(version)
        #
        # if not header_class:
        #     raise NotImplementedError(version)
        #
        # return header_class.unpack(stream)

    def pack(self, stream: BinaryIO) -> int:
        args = self.path.encode("ascii"), self.name.encode("ascii"), self.sub_folder_range.start, self.sub_folder_range.end, \
               self.file_range.start, self.file_range.end, 0
        return self.LAYOUT.pack_stream(stream, *args)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'VirtualDriveHeaderABC':
        path, name, sub_folder_start, sub_folder_end, file_start, file_end, unk = cls.LAYOUT.unpack_stream(stream)
        path, name = path.decode("ascii").rstrip("\00"), name.decode("ascii").rstrip("\00")
        sub_folder_range = ArchiveRange(sub_folder_start, sub_folder_end)
        file_range = ArchiveRange(file_start, file_end)
        return cls(path, name, sub_folder_range, file_range, unk)


@dataclass
class VirtualDriveABC(FolderCollectionABC, FileCollectionABC):
    header: VirtualDriveHeaderABC

    def __init__(self, header: VirtualDriveHeaderABC, sub_folders: List[FolderABC], files: List[FileABC]):
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
    def create(cls, header: VirtualDriveHeaderABC) -> VirtualDriveABC:
        folders = [None] * header.sub_folder_range.size
        files = [None] * header.file_range.size
        # noinspection PyTypeChecker
        return VirtualDriveABC(header, folders, files)

    def load_toc(self, toc: ArchiveTableOfContentsABC):
        self.load_folders(toc.folders)
        self.load_files(toc.files)

    def load_folders(self, folders: List[FolderABC]):
        if self.header.sub_folder_range.start < len(folders):
            for folder_index in self.header.sub_folder_range:
                sub_folder_index = folder_index - self.header.sub_folder_range.start
                f = self.sub_folders[sub_folder_index] = folders[folder_index]
                f.parent_drive = self

    def load_files(self, files: List[FileABC]):
        if self.header.file_range.start < len(files):
            for file_index in self.header.file_range:
                sub_file_index = file_index - self.header.file_range.start
                f = self.files[sub_file_index] = files[file_index]
                f.parent_drive = self

    def build_tree(self):
        self.sub_folders = [f for f in self.sub_folders if not f.parent_folder]
        self.files = [f for f in self.files if not f.parent_folder]


ArchiveTOC = ArchiveTableOfContentsABC
ArchiveToCPtrABC = ArchiveTableOfContentsPtrABC


@dataclass
class DriveCollection:
    drives: List[VirtualDrive]
