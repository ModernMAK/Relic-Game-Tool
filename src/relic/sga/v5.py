from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Tuple, ClassVar, Type

from serialization_tools.ioutil import Ptr, WindowPtr
from serialization_tools.structx import Struct

from relic.common import VersionLike
from relic.sga import v2
from relic.sga.abc_ import VirtualDriveHeaderABC, FolderHeaderABC, FileHeaderABC, ArchiveHeaderABC, ArchiveABC, ArchiveTableOfContentsHeadersABC
from relic.sga.checksums import validate_md5_checksum
from relic.sga.common import ArchiveVersion
from relic.sga.v2 import ArchiveToCPtrABC
from relic.sga import abc_
from relic.sga.vX import APIvX

version = ArchiveVersion.v5


class _V5:
    """Mixin to allow classes to add `version` from the module level to the class level"""
    version = version  # classvar = modulevar # THIS IS A COPY; NOT A REFERENCE!


@dataclass
class VirtualDriveHeader(VirtualDriveHeaderABC, _V5):
    LAYOUT = Struct("< 64s 64s 4H 2s")


@dataclass
class ArchiveToCPtr(ArchiveToCPtrABC, _V5):
    LAYOUT = v2.ArchiveToCPtr.LAYOUT


@dataclass
class FolderHeader(FolderHeaderABC, _V5):
    LAYOUT = Struct("< L 4H")


@dataclass
class FileHeader(FileHeaderABC, _V5):
    LAYOUT = Struct(f"<5L H")
    unk_a: int
    unk_b: int

    @property
    def compressed(self):
        return self.compressed_size < self.decompressed_size

    @classmethod
    def unpack(cls, stream: BinaryIO) -> FileHeader:
        name_off, data_off, comp_size, decomp_size, unk_a, unk_b = cls.LAYOUT.unpack_stream(stream)
        # Name, File, Compressed, Decompressed, ???, ???
        name_ptr = Ptr(name_off)
        data_ptr = Ptr(data_off)
        return cls(name_ptr, data_ptr, decomp_size, comp_size, unk_a, unk_b)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.name_sub_ptr.offset, self.data_sub_ptr.offset, self.compressed_size, self.decompressed_size, self.unk_a, self.unk_b)

    def __eq__(self, other):
        return self.unk_a == other.unk_a and self.unk_b == other.unk_b and super().__eq__(other)


@dataclass
class ArchiveHeader(ArchiveHeaderABC, _V5):
    # hash, name, hash (repeated), TOC_SIZE, DATA_OFFSET, TOC_POS, RESERVED:1, RESERVED:0?, UNK???
    LAYOUT = Struct(f"< 16s 128s 16s 3L 3L")
    # Copied from DowI, may be different; praying it isn't
    # UGH THIER DIFFERENT! Or the way to calculate them is different
    # First, let's try no eigen # (None, None)  # HAH TROLLED MYSELF, forgot to conert checksum to hex
    MD5_EIGENVALUES = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))
    toc_ptr: WindowPtr
    checksums: Tuple[bytes, bytes]
    unk: int

    # This may not mirror DowI one-to-one, until it's verified, it stays here
    # noinspection DuplicatedCode
    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True):
        # return True
        ptrs = [Ptr(self.toc_ptr.offset), self.toc_ptr]
        valid = True
        indexes = (1,) if fast else (0, 1)
        for i in indexes:
            valid &= validate_md5_checksum(stream, ptrs[i], self.MD5_EIGENVALUES[i], self.checksums[i], _assert=_assert)
        return valid

    def __eq__(self, other):
        # TODO make issue to add equality to WindowPtr/Ptr
        return self.name == other.name and self.unk == other.unk \
               and self.toc_ptr.size == other.toc_ptr.size and self.toc_ptr.offset == other.toc_ptr.offset \
               and self.data_ptr.size == other.data_ptr.size and self.data_ptr.offset == other.data_ptr.offset \
               and self.version == other.version and self.checksums[0] == other.checksums[0] and self.checksums[1] == other.checksums[1]

    @property
    def version(self) -> VersionLike:
        return ArchiveVersion.Dow2

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> 'ArchiveHeader':
        csum_a, name, csum_b, toc_size, data_offset, toc_pos, rsv_1, rsv_0, unk = cls.LAYOUT.unpack_stream(stream)

        assert rsv_1 == 1
        assert rsv_0 == 0

        name = name.decode("utf-16-le").rstrip("\0")
        toc_ptr = WindowPtr(offset=toc_pos, size=toc_size)
        data_ptr = WindowPtr(offset=data_offset)

        return cls(name, toc_ptr, data_ptr, (csum_a, csum_b), unk)

    def _pack(self, stream: BinaryIO) -> int:
        args = self.checksums[0], self.name.encode("utf-16-le"), self.checksums[1], self.toc_ptr.size, self.data_ptr.offset, self.toc_ptr.offset, 1, 0, self.unk
        return self.LAYOUT.pack_stream(stream, *args)


# noinspection DuplicatedCode
# Code is identical; but meaning is completely different; using _V5 instead of _V2
class ArchiveTableOfContentsHeaders(ArchiveTableOfContentsHeadersABC):
    VDRIVE_HEADER_CLS = VirtualDriveHeader
    FOLDER_HEADER_CLS = FolderHeader
    FILE_HEADER_CLS = FileHeader


@dataclass(init=False)
class Archive(ArchiveABC, _V5):
    TOC_PTR_CLS: ClassVar[Type[ArchiveToCPtrABC]] = ArchiveToCPtr
    TOC_HEADERS_CLS: ClassVar[Type[ArchiveTableOfContentsHeadersABC]] = ArchiveTableOfContentsHeaders

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        raise NotImplementedError


File = abc_.FileABC
Folder = abc_.FolderABC
VirtualDrive = abc_.VirtualDriveABC


# noinspection DuplicatedCode
class ArchiveTableOfContentsHeaders(ArchiveTableOfContentsHeadersABC):
    VDRIVE_HEADER_CLS = VirtualDriveHeader
    FOLDER_HEADER_CLS = FolderHeader
    FILE_HEADER_CLS = FileHeader


class APIv5(APIvX, _V5):
    ArchiveHeader = ArchiveHeader
    ArchiveTableOfContentsHeaders = ArchiveTableOfContentsHeaders
    FileHeader = FileHeader
    FolderHeader = FolderHeader
    VirtualDriveHeader = VirtualDriveHeader
    Archive = Archive
    ArchiveToCPtr = ArchiveToCPtr
    File = File
    Folder = Folder
    VirtualDrive = VirtualDrive
