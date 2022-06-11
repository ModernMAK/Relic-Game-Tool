from __future__ import annotations

import zlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import PosixPath, PurePosixPath
from typing import ClassVar, BinaryIO, Optional, List, Type, Dict, Tuple

from serialization_tools.ioutil import WindowPtr
from serialization_tools.magic import MagicWordIO
from serialization_tools.structx import Struct

MagicWord = MagicWordIO(Struct("< 8s"), "_ARCHIVE".encode("ascii"))


class FileVerificationType(Enum):
    None_ = 0  # unknown real values, assuming incremental
    CRC = 1  # unknown real values, assuming incremental
    CRCBlocks = 2  # unknown real values, assuming incremental
    MD5Blocks = 3  # unknown real values, assuming incremental
    SHA1Blocks = 4  # unknown real values, assuming incremental


class FileStorageType(Enum):
    Store = 0
    StreamCompress = 1  # 16
    BufferCompress = 2  # 32


@dataclass
class Version:
    """ The Major Version; Relic revers to this as the 'Version' """
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
        return self.major << 32 + self.minor

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


class VersionMismatchError(Exception):
    def __init__(self, version: Version = None, expected: Version = None):
        self.version = version
        self.expected = expected

    def __str__(self):
        return _print_mismatch("Version", self.version, self.expected)


class Md5MismatchError(Exception):
    def __init__(self, recieved: bytes = None, expected: bytes = None):
        self.recieved = recieved
        self.expected = expected

    def __str__(self):
        return _print_mismatch("MD5", self.recieved, self.expected)


def _read_names_as_lookup(stream: BinaryIO, name_count_or_size: int, is_count: bool = True):
    BUF_SIZE = 64  # stolen from archive reader
    lookup = {}
    offset = 0
    if not is_count:
        buffer = stream.read(name_count_or_size)  # size
        names = [_.decode("ascii") for _ in buffer.split(b"\0")]
        for name in names:
            lookup[offset] = name
            offset += len(name) + 1
        return lookup
    else:
        # THIS GETS COMPLICATED
        start_pos = stream.tell()
        current_name = b""
        # While we still need to reaad names
        while len(lookup) < name_count_or_size:
            # Read a partial buffer in
            buffer = stream.read(BUF_SIZE)
            if len(buffer) == 0:
                raise Exception("Buffer ran out of data!")
            # Try to do a fast separate on the null byte
            enc_names = buffer.split(b"\0")
            current_name += enc_names[0]
            # Needs more data (no b"\0" was found)
            if len(enc_names) == 1 and len(buffer) == BUF_SIZE:
                continue
            else:
                # Handle [0]
                lookup[offset] = current_name.decode("ascii")
                offset += len(current_name) + 1
                current_name = b""
                # Handle [1,N] by seeking to offset and looping again
                stream.seek(start_pos + offset)
                continue
        return lookup


@dataclass
class BlobPtrs:
    header_pos: int
    header_size: Optional[int]
    data_pos: int
    data_size: Optional[int]


@dataclass
class ToCPtrsABC:
    vdrive_rel_pos: int
    vdrive_count: int
    folder_rel_pos: int
    folder_count: int
    file_rel_pos: int
    file_count: int
    name_rel_pos: int
    name_count_or_size: int  # meaning varies between version

    LAYOUT: ClassVar[Struct]
    """ Only 'counts' are uint16s """
    LAYOUT_UINT16: ClassVar = Struct("<IH IH IH IH")
    LAYOUT_UINT32: ClassVar = Struct("<8I")

    @classmethod
    def unpack(cls, stream: BinaryIO):
        layout: Struct = cls.LAYOUT
        args = layout.unpack_stream(stream)
        return cls(*args)


@dataclass
class DriveDefABC:
    alias: str
    name: str
    # folder/file start/end define the range the folder/file definitions that should be used
    #   This is likely important for archives with multiple vdrives; but I need to find some first
    #       Archive Viewer ignores them completely, so.... ?
    folder_start: int
    folder_end: int
    file_start: int
    file_end: int
    folder_root: int  # This is the 'entry point' folder this drive will become

    LAYOUT_UINT32: ClassVar = Struct("<64s 64s 5I")
    LAYOUT_UINT16: ClassVar = Struct("<64s 64s 5H")
    LAYOUT: ClassVar[Struct]

    @classmethod
    def unpack(cls, stream: BinaryIO):
        alias, name, sf_start, sf_end, f_start, f_end, sf_root = cls.LAYOUT.unpack_stream(stream)
        alias = alias.decode("ascii").rstrip("\0")
        name = name.decode("ascii").rstrip("\0")
        return cls(alias, name, sf_start, sf_end, f_start, f_end, sf_root)


@dataclass
class DriveABC:
    folders: List[FolderABC]
    files: List[FileABC]
    alias: str
    name: str


@dataclass
class FolderDefABC:
    name_rel_pos: int
    folder_start: int
    folder_end: int
    file_start: int
    file_end: int

    LAYOUT: ClassVar[Struct]
    LAYOUT_UINT32: ClassVar = Struct("<I 4I")
    LAYOUT_UINT16: ClassVar = Struct("<I 4H")

    @classmethod
    def unpack(cls, stream: BinaryIO):
        layout: Struct = cls.LAYOUT
        args = layout.unpack_stream(stream)
        return cls(*args)


@dataclass
class FileDefABC:
    name_rel_pos: int
    data_rel_pos: int
    length: int
    store_length: int
    storage_type: FileStorageType
    # modified: datetime  # Unix EPOCH
    # verification_type: FileVerificationType
    # crc: int
    # hash_pos: int
    LAYOUT: ClassVar[Struct]

    # LAYOUT: ClassVar[Struct] = Struct("<5I 2B 2I")

    @classmethod
    def unpack(cls, stream: BinaryIO):
        raise NotImplementedError


@dataclass
class FolderABC:
    name: str
    folders: List[FolderABC]
    files: List[FileABC]


@dataclass
class FileSparseInfo:
    storage_type: FileStorageType  # Redundancy
    abs_data_pos: int  # Absolute data position
    size_on_disk: int
    size_in_archive: int

    def read(self, stream: BinaryIO) -> bytes:
        if self.size_in_archive == 0:
            return b""
        else:
            with WindowPtr(self.abs_data_pos, self.size_in_archive).stream_jump_to(stream) as window:
                file_data = window.read()
                if self.storage_type == FileStorageType.Store:
                    return file_data
                elif self.storage_type in [FileStorageType.StreamCompress, FileStorageType.BufferCompress]:
                    return zlib.decompress(file_data)
                else:
                    raise NotImplementedError(f"Reading a file stored as `{self.storage_type}` is not supported!")


@dataclass
class FileMetaABC:
    storage: FileStorageType


@dataclass
class FileABC:
    name: str
    meta: FileMetaABC
    data: Optional[bytes] = None
    sparse_info: Optional[FileSparseInfo] = None

    def read_data(self, stream: BinaryIO):
        self.data = self.sparse_info.read(stream)


class ArchiveMetaABC:
    ...  # TODO


@dataclass
class ArchiveABC:
    MAGIC: ClassVar = MagicWord
    VERSION: ClassVar[Version]
    name: str
    meta: ArchiveMetaABC
    drives: List[DriveABC]

    # header_size: int # Not required
    # data_offset: int # Not required

    # header_offset: int

    TOC_PTRS: ClassVar[Type[ToCPtrsABC]]
    VDRIVE_DEF: ClassVar[Type[DriveDefABC]]
    FOLDER_DEF: ClassVar[Type[FolderDefABC]]
    FILE_DEF: ClassVar[Type[FileDefABC]]
    NAME_BUFFER_USES_COUNT: ClassVar[bool] = True

    @classmethod
    def _unpack_meta(cls, stream: BinaryIO) -> Tuple[str, ArchiveMetaABC, BlobPtrs, ToCPtrsABC]:
        raise NotImplementedError

    @classmethod
    def _read_toc(cls, header_stream: BinaryIO, header_pos: int, toc_ptrs: ToCPtrsABC):
        vdrive_stream = header_stream
        vdrive_stream.seek(header_pos + toc_ptrs.vdrive_rel_pos)
        vdrive_defs = [cls.VDRIVE_DEF.unpack(vdrive_stream) for _ in range(toc_ptrs.vdrive_count)]

        folders_stream = header_stream
        folders_stream.seek(header_pos + toc_ptrs.folder_rel_pos)
        folder_defs = [cls.FOLDER_DEF.unpack(folders_stream) for _ in range(toc_ptrs.folder_count)]

        files_stream = header_stream
        files_stream.seek(header_pos + toc_ptrs.file_rel_pos)
        file_defs = [cls.FILE_DEF.unpack(files_stream) for _ in range(toc_ptrs.file_count)]

        name_stream = header_stream
        name_stream.seek(header_pos + toc_ptrs.name_rel_pos)
        names = _read_names_as_lookup(name_stream, toc_ptrs.name_count_or_size, is_count=cls.NAME_BUFFER_USES_COUNT)

        return vdrive_defs, folder_defs, file_defs, names

    @classmethod
    def _assemble_files(cls, file_defs: List[FileDefABC], names: Dict[int, str], data_pos: int):
        raise NotImplementedError

    @classmethod
    def _assemble_folders(cls, folder_defs: List[FolderDefABC], files: List[FileABC], names: Dict[int, str]):
        folders: List[FolderABC] = []
        for f_def in folder_defs:
            full_name = names[f_def.name_rel_pos]
            if full_name != "":
                name = str(PurePosixPath(full_name).parts[-1])  # hack to get last portion of pathed-name
            else:
                name = ""
            folder = FolderABC(name, None, files[f_def.file_start:f_def.file_end + 1])
            folders.append(folder)
        for f_def, folder in zip(folder_defs, folders):
            folder.folders = folders[f_def.folder_start:f_def.folder_end + 1]
        return folders

    @classmethod
    def _assemble_drives(cls, drive_defs: List[DriveDefABC], folders: List[FolderABC]):
        drives: List[DriveABC] = []
        for d_def in drive_defs:
            folder = folders[d_def.folder_root]
            drive = DriveABC(folder.folders, folder.files, d_def.alias, d_def.name)
            drives.append(drive)
        return drives

    @classmethod
    def _assemble_hierarchy(cls, vdrive_defs: List[DriveDefABC], folder_defs: List[FolderDefABC], file_defs: List[FileDefABC], names: Dict[int, str], data_pos: int):
        files = cls._assemble_files(file_defs, names, data_pos)
        folders = cls._assemble_folders(folder_defs, files, names)
        vdrives = cls._assemble_drives(vdrive_defs, folders)
        return vdrives, folders, files

    @classmethod
    def read(cls, stream: BinaryIO, sparse: bool = False):
        cls.MAGIC.read_magic_word(stream)
        archive_version = Version.unpack(stream)
        archive_version.assert_version_matches(cls.VERSION)
        name, meta, blob_ptrs, toc_ptrs = cls._unpack_meta(stream)

        # TOC Block
        vdrive_defs, folder_defs, file_defs, names = cls._read_toc(stream, blob_ptrs.header_pos, toc_ptrs)

        vdrives, _, files = cls._assemble_hierarchy(vdrive_defs, folder_defs, file_defs, names, blob_ptrs.data_pos)

        if not sparse:
            for file in files:
                file.read_data(stream)

        return cls(name, meta, vdrives)

    # def walk(self) -> ArchiveWalk:
    #     for drive in self.drives:
    #         for _ in drive.walk():
    #             yield _
