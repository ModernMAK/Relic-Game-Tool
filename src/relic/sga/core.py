from __future__ import annotations

import zlib
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import PurePath, PureWindowsPath
from typing import ClassVar, BinaryIO, Optional, List, Type, Dict, Tuple, Any, Protocol, Iterable, Union, Generic, TypeVar

from serialization_tools.ioutil import WindowPtr
from serialization_tools.magic import MagicWordIO
from serialization_tools.structx import Struct

MagicWord = MagicWordIO(Struct("< 8s"), "_ARCHIVE".encode("ascii"))
#
# T = TypeVar("T")
# class StreamSerializer(Generic[T], Protocol):
#     def unpack(self, stream:BinaryIO) -> T:
#         raise NotImplementedError
#     def pack(self, stream:BinaryIO, value:T) -> int:
#         raise NotImplementedError
#
# # Dont use dataclass
# class ArchivePathable(Protocol):
#     _parent_path: Optional[ArchivePathable]
#
#     @property
#     def path(self) -> PurePath:
#         raise NotImplementedError
#
#
# class ArchiveWalkable(Protocol):
#     def walk(self) -> ArchiveWalk:
#         raise NotImplementedError
#
#
# class FileVerificationType(Enum):
#     None_ = 0  # unknown real values, assuming incremental
#     CRC = 1  # unknown real values, assuming incremental
#     CRCBlocks = 2  # unknown real values, assuming incremental
#     MD5Blocks = 3  # unknown real values, assuming incremental
#     SHA1Blocks = 4  # unknown real values, assuming incremental
#
#
# class FileStorageType(Enum):
#     Store = 0
#     StreamCompress = 1  # 16 in v2 (old-engine binding)
#     BufferCompress = 2  # 32 in v2 (old-engine binding)


@dataclass
class Version:
    """ The Major Version; Relic refers to this as the 'Version' """
    major: int
    """ The Minor Version; Relic refers to this as the 'Product' """
    minor: Optional[int] = 0

    LAYOUT: ClassVar[Struct] = Struct("<2H")

    def __str__(self) -> str:
        return f"Version {self.major}.{self.minor}"

    def __eq__(self, other):
        if isinstance(other, Version):
            return self.major == other.major and self.minor == other.minor
        else:
            return super().__eq__(other)

    def __hash__(self):
        # Realistically; Version will always be <256
        # But we could manually set it to something much bigger by accident; and that may cause collisions
        return self.major << (self.LAYOUT.size // 2) + self.minor

    @classmethod
    def unpack(cls, stream: BinaryIO):
        layout: Struct = cls.LAYOUT
        args = layout.unpack_stream(stream)
        return cls(*args)

    def pack(self, stream: BinaryIO):
        layout: Struct = self.LAYOUT
        args = (self.major, self.minor)
        return layout.pack_stream(stream, *args)

    def assert_version_matches(self, expected: Version):
        if self != expected:
            raise VersionMismatchError(self, expected)


def _print_mismatch(name: str, received, expected):
    msg = f"Unexpected {name}"
    if received or expected:
        msg += ";"
    if received:
        msg += f" got `{str(received)}`"
    if received and expected:
        msg += ","
    if expected:
        msg += f" expected `{str(expected)}`"
    return msg + "!"


class MismatchError(Exception):
    def __init__(self, name: str, received: Any = None, expected: Any = None):
        self.name = name
        self.received = received
        self.expected = expected

    def __str__(self):
        return _print_mismatch(self.name, self.received, self.expected)


class VersionMismatchError(MismatchError):
    def __init__(self, received: Version = None, expected: Version = None):
        super().__init__("Version", received, expected)


class MD5MismatchError(MismatchError):
    def __init__(self, received: bytes = None, expected: bytes = None):
        super().__init__("MD5", received, expected)


class VersionNotSupportedError(Exception):
    def __init__(self, received: Version, allowed: List[Version]):
        self.received = received
        self.allowed = allowed

    def __str__(self):
        def str_ver(v: Version) -> str:  # dont use str(version); too verbose
            return f"{v.major}.{v.minor}"

        allowed_str = [str_ver(_) for _ in self.allowed]
        return f"Version `{str_ver(self.received)}` is not supported. Versions supported: `{allowed_str}`"


# def _read_names_as_lookup(stream: BinaryIO, name_count_or_size: int, is_count: bool = True):
#     BUF_SIZE = 64  # stolen from archive reader
#     lookup = {}
#     offset = 0
#     if not is_count:
#         buffer = stream.read(name_count_or_size)  # size
#         names = [_.decode("ascii") for _ in buffer.split(b"\0")]
#         for name in names:
#             lookup[offset] = name
#             offset += len(name) + 1
#         return lookup
#     else:
#         # THIS GETS COMPLICATED
#         start_pos = stream.tell()
#         current_name = b""
#         # While we still need to reaad names
#         while len(lookup) < name_count_or_size:
#             # Read a partial buffer in
#             buffer = stream.read(BUF_SIZE)
#             if len(buffer) == 0:
#                 raise Exception("Buffer ran out of data!")
#             # Try to do a fast separate on the null byte
#             enc_names = buffer.split(b"\0")
#             current_name += enc_names[0]
#             # Needs more data (no b"\0" was found)
#             if len(enc_names) == 1 and len(buffer) == BUF_SIZE:
#                 continue
#             else:
#                 # Handle [0]
#                 lookup[offset] = current_name.decode("ascii")
#                 offset += len(current_name) + 1
#                 current_name = b""
#                 # Handle [1,N] by seeking to offset and looping again
#                 stream.seek(start_pos + offset)
#                 continue
#         return lookup
#
#
# @dataclass
# class BlobPtrs:
#     header_pos: int
#     header_size: Optional[int]
#     data_pos: int
#     data_size: Optional[int]
#
#
# @dataclass
# class ToCPtrsABC:
#     vdrive_rel_pos: int
#     vdrive_count: int
#     folder_rel_pos: int
#     folder_count: int
#     file_rel_pos: int
#     file_count: int
#     name_rel_pos: int
#     name_count_or_size: int  # meaning varies between version
#
#     LAYOUT: ClassVar[Struct]
#     """ Only 'counts' are uint16s """
#     LAYOUT_UINT16: ClassVar = Struct("<IH IH IH IH")
#     LAYOUT_UINT32: ClassVar = Struct("<8I")
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO):
#         layout: Struct = cls.LAYOUT
#         args = layout.unpack_stream(stream)
#         return cls(*args)
#
#
# @dataclass
# class DriveDefABC:
#     alias: str
#     name: str
#     # folder/file start/end define the range the folder/file definitions that should be used
#     #   This is likely important for archives with multiple vdrives; but I need to find some first
#     #       Archive Viewer ignores them completely, so.... ?
#     folder_start: int
#     folder_end: int
#     file_start: int
#     file_end: int
#     folder_root: int  # This is the 'entry point' folder this drive will become
#
#     LAYOUT_UINT32: ClassVar = Struct("<64s 64s 5I")
#     LAYOUT_UINT16: ClassVar = Struct("<64s 64s 5H")
#     LAYOUT: ClassVar[Struct]
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO):
#         alias, name, sf_start, sf_end, f_start, f_end, sf_root = cls.LAYOUT.unpack_stream(stream)
#         alias = alias.decode("ascii").rstrip("\0")
#         name = name.decode("ascii").rstrip("\0")
#         return cls(alias, name, sf_start, sf_end, f_start, f_end, sf_root)
#
#
# @dataclass
# class DriveABC(ArchivePathable):
#     folders: List[FolderABC]
#     files: List[FileABC]
#     alias: str
#     name: str
#     _parent_path: Optional[ArchivePathable] = None
#     __ignore__ = ["_parent_path"]
#
#     @property
#     def path(self) -> PurePath:
#         return PurePath(f"{self.alias}:/")
#
#     def walk(self) -> ArchiveWalk:
#         yield self, self.folders, self.files
#         for folder in self.folders:
#             for _, local_folder, sub_folders, files in folder.walk():
#                 yield self, local_folder, sub_folders, files
#
#
# @dataclass
# class FolderDefABC:
#     name_rel_pos: int
#     folder_start: int
#     folder_end: int
#     file_start: int
#     file_end: int
#
#     LAYOUT: ClassVar[Struct]
#     LAYOUT_UINT32: ClassVar = Struct("<I 4I")
#     LAYOUT_UINT16: ClassVar = Struct("<I 4H")
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO):
#         layout: Struct = cls.LAYOUT
#         args = layout.unpack_stream(stream)
#         return cls(*args)
#
#
# @dataclass
# class FileDefABC:
#     name_rel_pos: int
#     data_rel_pos: int
#     length: int
#     store_length: int
#     storage_type: FileStorageType
#     # modified: datetime  # Unix EPOCH
#     # verification_type: FileVerificationType
#     # crc: int
#     # hash_pos: int
#     LAYOUT: ClassVar[Struct]
#
#     # LAYOUT: ClassVar[Struct] = Struct("<5I 2B 2I")
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO):
#         raise NotImplementedError
#
#
# @dataclass
# class FolderABC(ArchivePathable, ArchiveWalkable):
#     name: str
#     folders: List[FolderABC]
#     files: List[FileABC]
#     _parent_path: Optional[ArchivePathable] = None
#     _flat_name: Optional[str] = None  # The flattened name read directly from the archive buffer
#
#     @property
#     def path(self) -> PurePath:
#         if self._parent_path:
#             return self._parent_path.path / self.name
#         else:
#             return PurePath(self.name)
#
#     def walk(self) -> ArchiveWalk:
#         yield self, self.folders, self.files
#         for folder in self.folders:
#             for _ in folder.walk():
#                 yield _
#
#
# @dataclass
# class FileSparseInfo:
#     storage_type: FileStorageType  # Redundancy
#     abs_data_pos: int  # Absolute data position
#     size_on_disk: int
#     size_in_archive: int
#
#     def read(self, stream: BinaryIO) -> bytes:
#         if self.size_in_archive == 0:
#             return b""
#         else:
#             with WindowPtr(self.abs_data_pos, self.size_in_archive).stream_jump_to(stream) as window:
#                 file_data = window.read()
#                 if self.storage_type == FileStorageType.Store:
#                     return file_data
#                 elif self.storage_type in [FileStorageType.StreamCompress, FileStorageType.BufferCompress]:
#                     return zlib.decompress(file_data)
#                 else:
#                     raise NotImplementedError(f"Reading a file stored as `{self.storage_type}` is not supported!")
#
#
# @dataclass
# class FileMetaABC:
#     storage: FileStorageType
#
#
# @dataclass
# class FileABC(ArchivePathable):
#     name: str
#     meta: FileMetaABC
#     data: Optional[bytes] = None
#     sparse_info: Optional[FileSparseInfo] = None
#     _parent_path: Optional[ArchivePathable] = None
#
#     @property
#     def path(self) -> PurePath:
#         if self._parent_path:
#             return self._parent_path.path / self.name
#         else:
#             return PurePath(self.name)
#
#     def read_data(self, stream: BinaryIO):
#         self.data = self.sparse_info.read(stream)
#
#
# class ArchiveMetaABC:
#     ...  # TODO
#
#
# class ArchiveFlattener:
#     # FILE_DEF_CLS: Type[FileDefABC] = FileDefABC
#     FOLDER_DEF_CLS: Type[FolderDefABC] = FolderDefABC
#     DRIVE_DEF_CLS: Type[DriveDefABC] = DriveDefABC
#
#     def __init__(self, name_stream: BinaryIO, data_stream: BinaryIO, drive_def_cls: Optional[Type[DriveDefABC]] = None, folder_def_cls: Optional[Type[FolderDefABC]] = None):
#         if drive_def_cls is not None:
#             self.DRIVE_DEF_CLS = drive_def_cls
#         if folder_def_cls is not None:
#             self.FOLDER_DEF_CLS = folder_def_cls
#
#         self.files: List[FileDefABC] = []
#         self.folders: List[FolderDefABC] = []
#         self.drives: List[DriveDefABC] = []
#         self.name_stream: BinaryIO = name_stream
#         self._name_stream_offset: int = 0
#         self._data_stream_offset: int = 0
#         self.data_stream: BinaryIO = data_stream
#         self._name_lookup: Dict[str, int] = {}
#
#     def get_name_rel_pos(self, name: str) -> int:
#         if name in self._name_lookup:
#             return self._name_lookup[name]
#         else:
#             this_name_offset = self._name_lookup[name] = self._name_stream_offset
#             self._name_stream_offset += self.name_stream.write(name.encode("ascii") + b"\0")
#             return this_name_offset
#
#     def get_name_rel_pos_from_path(self, pathable: ArchivePathable, root: DriveABC) -> int:
#         path = pathable.path
#         root_path = root.path
#         rel_path = path.relative_to(root_path)
#         name = str(rel_path)
#         if name == "." and root_path == path:
#             name = ""
#         return self.get_name_rel_pos(name)
#
#     @staticmethod
#     def repackage_data(data: bytes, storage: FileStorageType) -> Tuple[bytes, int, int]:
#         if storage == storage.Store:
#             return data, len(data), len(data)
#         else:
#             comp_data = zlib.compress(data)
#             return comp_data, len(data), len(comp_data)
#
#     def get_data_rel_pos(self, data: bytes) -> int:
#         offset = self._data_stream_offset
#         self.data_stream.write(data)
#         return offset
#
#     @abstractmethod
#     def build_file_def(self, file: FileABC, name_rel_pos: int, data_rel_pos: int, length: int, store_length: int, storage: FileStorageType) -> FileDefABC:
#         raise NotImplementedError
#         # return FileDefABC(name_rel_pos, data_rel_pos, length, store_length, storage)
#
#     def flatten_file(self, file: FileABC):
#         name_rel_pos = self.get_name_rel_pos(file.name)  # files use name-only
#         data_buffer, length, store_length = self.repackage_data(file.data, file.meta.storage)
#         data_rel_pos = self.get_data_rel_pos(data_buffer)
#         file_def = self.build_file_def(file, name_rel_pos, data_rel_pos, length, store_length, file.meta.storage)  # FileDefABC(name_rel_pos,data_rel_pos,length,store_length,file.meta.storage)
#         return file_def
#
#     def flatten_folder(self, folder: FolderABC, root: DriveABC):
#         folder_def_cls:Type[FolderDefABC] = self.FOLDER_DEF_CLS
#         name_rel_pos = self.get_name_rel_pos_from_path(folder, root)
#         folder_start = len(self.folders)
#         file_start = len(self.files)
#         folder_def = folder_def_cls(name_rel_pos, folder_start, folder_start + len(folder.folders), file_start, file_start + len(folder.files))
#
#         self.folders.extend([None] * len(folder.folders))  # Reserve space for sub-folders
#         self.files.extend([None] * len(folder.files))  # Reserve space for subfiles
#
#         for i, sub_folder in enumerate(folder.folders):
#             self.folders[folder_start + i] = self.flatten_folder(sub_folder, root)
#         for i, file in enumerate(folder.files):
#             self.files[file_start + i] = self.flatten_file(file)
#         return folder_def
#
#     def flatten_drive(self, drive: DriveABC) -> DriveDefABC:
#         drive_def_cls: Type[DriveDefABC] = self.DRIVE_DEF_CLS
#         drive_folder_root = len(self.folders)
#         drive_file_start = len(self.files)
#         drive_def = drive_def_cls(drive.alias, drive.name, drive_folder_root, None, drive_file_start, None, drive_folder_root)
#
#         self.folders.extend([None])  # Reserve space for root
#
#         self.folders[drive_folder_root] = self.flatten_folder(drive, drive)  # drive is technically a folder; but this should be fixed for better type-safety
#
#         drive_def.folder_end = len(self.folders)
#         drive_def.file_end = len(self.files)
#         return drive_def
#
#     def flatten_archive(self, archive: ArchiveABC):
#         for drive in archive.drives:
#             drive_def = self.flatten_drive(drive)
#             self.drives.append(drive_def)
#
# @dataclass
# class ArchiveABC(ArchiveWalkable):
#     MAGIC: ClassVar = MagicWord
#     VERSION: ClassVar[Version]
#     name: str
#     meta: ArchiveMetaABC
#     drives: List[DriveABC]
#
#     # header_size: int # Not required
#     # data_offset: int # Not required
#
#     # header_offset: int
#
#     TOC_PTRS: ClassVar[Type[ToCPtrsABC]]
#     VDRIVE_DEF: ClassVar[Type[DriveDefABC]]
#     FOLDER_DEF: ClassVar[Type[FolderDefABC]]
#     FILE_DEF: ClassVar[Type[FileDefABC]]
#     NAME_BUFFER_USES_COUNT: ClassVar[bool] = True
#
#     @classmethod
#     def _unpack_meta(cls, stream: BinaryIO) -> Tuple[str, ArchiveMetaABC, BlobPtrs, ToCPtrsABC]:
#         raise NotImplementedError
#
#     def _pack_meta(self, stream:BinaryIO, ):
#         raise NotImplementedError
#
#     @classmethod
#     def _read_toc(cls, header_stream: BinaryIO, header_pos: int, toc_ptrs: ToCPtrsABC):
#         vdrive_stream = header_stream
#         vdrive_stream.seek(header_pos + toc_ptrs.vdrive_rel_pos)
#         vdrive_defs = [cls.VDRIVE_DEF.unpack(vdrive_stream) for _ in range(toc_ptrs.vdrive_count)]
#
#         folders_stream = header_stream
#         folders_stream.seek(header_pos + toc_ptrs.folder_rel_pos)
#         folder_defs = [cls.FOLDER_DEF.unpack(folders_stream) for _ in range(toc_ptrs.folder_count)]
#
#         files_stream = header_stream
#         files_stream.seek(header_pos + toc_ptrs.file_rel_pos)
#         file_defs = [cls.FILE_DEF.unpack(files_stream) for _ in range(toc_ptrs.file_count)]
#
#         name_stream = header_stream
#         name_stream.seek(header_pos + toc_ptrs.name_rel_pos)
#         names = _read_names_as_lookup(name_stream, toc_ptrs.name_count_or_size, is_count=cls.NAME_BUFFER_USES_COUNT)
#
#         return vdrive_defs, folder_defs, file_defs, names
#
#     @classmethod
#     def _write_toc(cls, header_stream:BinaryIO, drives:List[DriveDefABC], folders:List[FolderDefABC], files:List[FileDefABC], name_buffer:bytes, name_count_or_size:int) -> ToCPtrsABC:
#         # The order shouldn't matter; but I follow the generally used format (that I've seen) of drive/folder/file/names
#         drive_rel_pos, drive_count = header_stream.tell(), len(drives)
#         for drive in drives:
#             drive.pack(header_stream)
#
#         folder_rel_pos, folder_count = header_stream.tell(), len(folders)
#         for folder in folders:
#             folder.pack(header_stream)
#
#         file_rel_pos, file_count = header_stream.tell(), len(files)
#         for file in files:
#             file.pack(header_stream)
#
#         name_rel_pos, name_count = header_stream.tell(), name_count_or_size
#         header_stream.write(name_buffer)
#         return cls.TOC_PTRS(drive_rel_pos,drive_count,folder_rel_pos,folder_count,file_rel_pos,file_count,name_rel_pos,name_count)
#
#     @classmethod
#     def _assemble_files(cls, file_defs: List[FileDefABC], names: Dict[int, str], data_pos: int):
#         raise NotImplementedError
#
#     @classmethod
#     def _assemble_folders(cls, folder_defs: List[FolderDefABC], files: List[FileABC], names: Dict[int, str]):
#         folders: List[FolderABC] = []
#         for f_def in folder_defs:
#             full_name = names[f_def.name_rel_pos]
#             if full_name != "":
#                 name = str(PureWindowsPath(full_name).parts[-1])  # hack to get last portion of pathed-name
#             else:
#                 name = ""
#             folder = FolderABC(name, None, files[f_def.file_start:f_def.file_end + 1], _flat_name=full_name)
#             folders.append(folder)
#
#             for file in folder.files:  # Link files to parent
#                 file._parent_path = folder
#
#         for f_def, folder in zip(folder_defs, folders):
#             folder.folders = folders[f_def.folder_start:f_def.folder_end + 1]
#
#             for subfolder in folder.folders:  # Link folders to parent
#                 subfolder._parent_path = folder
#
#         return folders
#
#     @classmethod
#     def _assemble_drives(cls, drive_defs: List[DriveDefABC], folders: List[FolderABC]):
#         drives: List[DriveABC] = []
#         for d_def in drive_defs:
#             folder = folders[d_def.folder_root]
#             drive = DriveABC(folder.folders, folder.files, d_def.alias, d_def.name)
#             drives.append(drive)
#
#             # Relink folders/files to drive (instead of folder)
#             for file in drive.files:
#                 file._parent_path = drive
#             for folder in drive.folders:
#                 folder._parent_path = drive
#
#         return drives
#
#     @classmethod
#     def _assemble_hierarchy(cls, vdrive_defs: List[DriveDefABC], folder_defs: List[FolderDefABC], file_defs: List[FileDefABC], names: Dict[int, str], data_pos: int):
#         files = cls._assemble_files(file_defs, names, data_pos)
#         folders = cls._assemble_folders(folder_defs, files, names)
#         vdrives = cls._assemble_drives(vdrive_defs, folders)
#         return vdrives, folders, files
#
#     @classmethod
#     def _read(cls, stream: BinaryIO, sparse: bool = False):
#         name, meta, blob_ptrs, toc_ptrs = cls._unpack_meta(stream)
#
#         # TOC Block
#         vdrive_defs, folder_defs, file_defs, names = cls._read_toc(stream, blob_ptrs.header_pos, toc_ptrs)
#
#         vdrives, _, files = cls._assemble_hierarchy(vdrive_defs, folder_defs, file_defs, names, blob_ptrs.data_pos)
#
#         if not sparse:
#             for file in files:
#                 file.read_data(stream)
#
#         return cls(name, meta, vdrives)
#
#     def _write_parts(self,out_stream:BinaryIO,):
#
#     def _write(self, stream: BinaryIO) -> int:
#             with BytesIO() as data_stream:
#                 with BytesIO() as name_stream:
#                     flattener = ArchiveFlattener(name_stream,data_stream,drive_def_cls=self.VDRIVE_DEF,folder_def_cls=self.FOLDER_DEF)
#                     flattener.flatten_archive(self)
#                     name_stream.seek(0)
#                     name_buffer = name_stream.read()
#                 with BytesIO() as header_stream:
#                     name_count_or_size = len(flattener._name_lookup) if self.NAME_BUFFER_USES_COUNT else len(name_buffer)
#                     toc = self._write_toc(header_stream,flattener.drives,flattener.folders,flattener.files,name_buffer,name_count_or_size)
#
#                 with BytesIO() as meta_stream:
#         raise NotImplementedError
#
#     @classmethod
#     def read(cls, stream: BinaryIO, sparse: bool = False):
#         magic: MagicWordIO = cls.MAGIC
#         magic.read_magic_word(stream)
#         archive_version = Version.unpack(stream)
#         archive_version.assert_version_matches(cls.VERSION)
#         return cls._read(stream, sparse)
#
#     def write(self, stream: BinaryIO) -> int:
#         magic: MagicWordIO = self.MAGIC
#         version: Version = self.VERSION
#         written = 0
#         written += magic.write_magic_word(stream)
#         written += version.pack(stream)
#         written += self._write(stream)
#         return written
#
#     def walk(self) -> ArchiveWalk:
#         for drive in self.drives:
#             for _ in drive.walk():
#                 yield _
#
#
#
# ArchiveWalk = Tuple[Union[DriveABC, FolderABC], Iterable[FolderABC], Iterable[FileABC]]
