from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, Tuple, Type, ClassVar

from serialization_tools.ioutil import WindowPtr, Ptr
from serialization_tools.structx import Struct

from relic.common import VersionLike
from relic.sga_old import abc_old_
from relic.sga_old.abc_old_ import ArchiveHeaderABC, ArchiveABC, FileHeaderABC, FolderHeaderABC, VirtualDriveHeaderABC, ArchiveToCPtrABC, ArchiveTableOfContentsHeadersABC
from relic.sga_old.checksums import validate_md5_checksum
from relic.sga_old.common import ArchiveVersion
from relic.sga_old.vX import APIvX

version = None # ArchiveVersion.v2


class _V2:
    """Mixin to allow classes to add `version` from the module level to the class level"""
    version = version  # classvar = modulevar


@dataclass
class ArchiveToCPtr(ArchiveToCPtrABC, _V2):
    LAYOUT = Struct("< LH LH LH LH")


@dataclass
class ArchiveHeader(ArchiveHeaderABC, _V2):
    # hash, name, hash (repeated), TOC_SIZE, DATA_OFFSET
    LAYOUT = Struct(f"< 16s 128s 16s 2L")
    # The eigen value is a guid? also knew that layout looked familiar
    MD5_EIGENVALUES = (b"E01519D6-2DB7-4640-AF54-0A23319C56C3", b"DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF")
    toc_ptr: WindowPtr
    checksums: Tuple[bytes, bytes]

    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True):
        ptrs = [Ptr(self.toc_ptr.offset), self.toc_ptr]
        valid = True
        indexes = (1,) if fast else (0, 1)
        for i in indexes:
            valid &= validate_md5_checksum(stream, ptrs[i], self.MD5_EIGENVALUES[i], self.checksums[i], _assert=_assert)
        return valid

    # @classmethod
    # @property
    # def version(cls) -> VersionLike:
    #     return cls.v

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ArchiveHeader:
        csum_a, name, csum_b, toc_size, data_offset = cls.LAYOUT.unpack_stream(stream)

        name = name.decode("utf-16-le").rstrip("\0")
        toc_ptr = WindowPtr(offset=stream.tell(), size=toc_size)
        data_ptr = WindowPtr(offset=data_offset, size=None)
        return cls(name, toc_ptr, data_ptr, (csum_a, csum_b))

    def pack(self, stream: BinaryIO) -> int:
        args = self.checksums[0], self.name.encode("utf-16-le"), self.checksums[1], self.toc_ptr.size, self.data_ptr.offset
        return self.LAYOUT.pack_stream(stream, *args)

    def __eq__(self, other):
        # TODO make issue to add equality to WindowPtr/Ptr
        return self.name == other.name \
               and self.toc_ptr.size == other.toc_ptr.size and self.toc_ptr.offset == other.toc_ptr.offset \
               and self.data_ptr.size == other.data_ptr.size and self.data_ptr.offset == other.data_ptr.offset \
               and self.version == other.version and self.checksums[0] == other.checksums[0] and self.checksums[1] == other.checksums[1]


class FileCompressionFlag(Enum):
    # Compression flag is either 0 (Decompressed) or 16/32 which are both compressed
    # Aside from 0; these appear to be the Window-Sizes for the Zlib Compression (In KibiBytes)
    Decompressed = 0

    Compressed16 = 16
    Compressed32 = 32

    def compressed(self) -> bool:
        return self != FileCompressionFlag.Decompressed


@dataclass
class FileHeader(FileHeaderABC, _V2):
    # name
    LAYOUT = Struct(f"<5L")
    compression_flag: FileCompressionFlag

    def __eq__(self, other):
        return self.compression_flag == other.compression_flag and super().__eq__(other)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> FileHeader:
        name_offset, compression_flag_value, data_offset, decompressed_size, compressed_size = cls.LAYOUT.unpack_stream(stream)
        compression_flag = FileCompressionFlag(compression_flag_value)
        name_ptr = Ptr(name_offset)
        data_ptr = WindowPtr(data_offset, compressed_size)
        return cls(name_ptr, data_ptr, decompressed_size, compressed_size, compression_flag)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.name_sub_ptr.offset, self.compression_flag.value, self.data_sub_ptr.offset, self.decompressed_size, self.compressed_size)

    @property
    def compressed(self):
        return self.compression_flag.compressed()


@dataclass
class FolderHeader(FolderHeaderABC, _V2):
    LAYOUT = Struct("< L 4H")


@dataclass
class VirtualDriveHeader(VirtualDriveHeaderABC, _V2):
    LAYOUT = Struct("< 64s 64s 4H 2s")


class ArchiveTableOfContentsHeaders(ArchiveTableOfContentsHeadersABC):
    VDRIVE_HEADER_CLS = VirtualDriveHeader
    FOLDER_HEADER_CLS = FolderHeader
    FILE_HEADER_CLS = FileHeader


@dataclass(init=False)
class Archive(ArchiveABC, _V2):
    TOC_PTR_CLS: ClassVar[Type[ArchiveToCPtrABC]] = ArchiveToCPtr
    TOC_HEADERS_CLS: ClassVar[Type[ArchiveTableOfContentsHeadersABC]] = ArchiveTableOfContentsHeaders

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        raise NotImplementedError


# Class Aliases; don't need to be inherited
File = abc_.FileABC
Folder = abc_.FolderABC
VirtualDrive = abc_.VirtualDriveABC


class APIv2(APIvX, _V2):
    ArchiveTableOfContentsHeaders = ArchiveTableOfContentsHeaders
    ArchiveHeader = ArchiveHeader
    FileHeader = FileHeader
    FolderHeader = FolderHeader
    VirtualDriveHeader = VirtualDriveHeader
    Archive = Archive
    ArchiveToCPtr = ArchiveToCPtr
    File = File
    Folder = Folder
    VirtualDrive = VirtualDrive
