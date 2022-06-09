from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Tuple, ClassVar, Type, List, Dict

from serialization_tools.ioutil import Ptr, WindowPtr
from serialization_tools.structx import Struct

from relic.common import VersionLike
from relic.sga import v2
from relic.sga.abc_ import VirtualDriveHeaderABC, FolderHeaderABC, FileHeaderABC, ArchiveHeaderABC, ArchiveABC, ArchiveTableOfContentsHeadersABC, ArchiveTableOfContentsABC, VirtualDriveABC, NameBufferABC
from relic.sga.checksums import validate_md5_checksum
from relic.sga.common import ArchiveVersion
from relic.sga.protocols import Archive, ArchiveWalk
from relic.sga.v2 import ArchiveToCPtrABC
from relic.sga import abc_
from relic.sga.vX import APIvX

version = ArchiveVersion.v7


class _V7:
    """Mixin to allow classes to add `version` from the module level to the class level"""
    version = version  # classvar = modulevar # THIS IS A COPY; NOT A REFERENCE!


@dataclass
class VirtualDriveHeader(VirtualDriveHeaderABC, _V7):
    LAYOUT = Struct("< 64s 64s 5L")


@dataclass
class ArchiveToCPtr(ArchiveToCPtrABC, _V7):
    LAYOUT = Struct("< 8I")


@dataclass
class FolderHeader(FolderHeaderABC, _V7):
    LAYOUT = Struct("< L 4I")


@dataclass
class FileHeader(FileHeaderABC, _V7):
    LAYOUT = Struct(f"<5L H 2L")
    unk_a: int
    unk_b: int
    unk_c: int
    unk_d: int

    @property
    def compressed(self):
        return self.compressed_size < self.decompressed_size

    @classmethod
    def unpack(cls, stream: BinaryIO) -> FileHeader:
        name_off, data_off, comp_size, decomp_size, unk_a, unk_b, unk_c, unk_d = cls.LAYOUT.unpack_stream(stream)
        # Name, File, Compressed, Decompressed, ???, ???
        name_ptr = Ptr(name_off)
        data_ptr = Ptr(data_off)
        return cls(name_ptr, data_ptr, decomp_size, comp_size, unk_a, unk_b, unk_c, unk_d)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.name_sub_ptr.offset, self.data_sub_ptr.offset, self.compressed_size, self.decompressed_size, self.unk_a, self.unk_b, self.unk_c, self.unk_d)

    def __eq__(self, other):
        return self.unk_a == other.unk_a and self.unk_b == other.unk_b and super().__eq__(other)


@dataclass
class ArchiveHeader(ArchiveHeaderABC, _V7):
    LAYOUT = Struct("< 128s 3L")
    LAYOUT_2 = Struct("< 2L")
    TOC_HEADER_SIZE = ArchiveToCPtr.LAYOUT.size
    toc_ptr: WindowPtr
    unk_a: int
    unk_b: int

    # This may not mirror DowI one-to-one, until it's verified, it stays here
    # noinspection DuplicatedCode
    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True):
        return True

    def __eq__(self, other):
        # TODO make issue to add equality to WindowPtr/Ptr
        return self.name == other.name and (self.unk_a, self.unk_b) == (other.unk_a, other.unk_b) \
               and self.toc_ptr.size == other.toc_ptr.size and self.toc_ptr.offset == other.toc_ptr.offset \
               and self.data_ptr.size == other.data_ptr.size and self.data_ptr.offset == other.data_ptr.offset

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ArchiveHeader:
        name, unk_a, data_offset, rsv_1 = cls.LAYOUT.unpack_stream(stream)
        toc_pos = stream.tell()
        stream.seek(cls.TOC_HEADER_SIZE, 1)
        toc_size, unk_b = cls.LAYOUT_2.unpack_stream(stream)

        # assert toc_size == toc_size_2, (toc_size, toc_size_2)
        assert rsv_1 == 1
        name = name.decode("utf-16-le").rstrip("\0")
        toc_ptr, data_ptr = WindowPtr(toc_pos, toc_size), WindowPtr(data_offset)
        return cls(name, toc_ptr, data_ptr, unk_a,unk_b)

    def pack(self, stream: BinaryIO) -> int:
        name, toc_size, data_offset = self.name.encode("utf-16-le"), self.toc_ptr.size, self.data_ptr.offset
        written = self.TOC_HEADER_SIZE  # count
        written += self.LAYOUT.pack_stream(stream, name, self.unk_a, data_offset, 1)
        stream.seek(self.TOC_HEADER_SIZE, 1)  # this will write \0 when seeking past files (unless python api/system api changes)
        written += self.LAYOUT.pack_stream(stream, toc_size, self.unk_b)
        return written


class ArchiveTableOfContentsHeaders(ArchiveTableOfContentsHeadersABC):
    VDRIVE_HEADER_CLS = VirtualDriveHeader
    FOLDER_HEADER_CLS = FolderHeader
    FILE_HEADER_CLS = FileHeader
    # NAME_BUFFER_CLS = NameBuffer


@dataclass(init=False)
class Archive(Archive, _V7):
    header: ArchiveHeader
    _sparse: bool

    def __init__(self, header: ArchiveHeader, drives: List[VirtualDriveABC], _sparse: bool):
        self.header = header
        self._sparse = _sparse
        self.drives = drives

    # redefine function
    walk = ArchiveABC.walk

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ArchiveHeader, sparse: bool = True):
        with header.toc_ptr.stream_jump_to(stream) as handle:
            toc_ptr = ArchiveToCPtr.unpack(handle)
        with header.toc_ptr.stream_jump_to(stream) as handle:
            toc_headers = ArchiveTableOfContentsHeaders.unpack(handle, toc_ptr)
            toc = ArchiveTableOfContentsABC.create(toc_headers)

        toc.load_toc()
        toc.build_tree()  # ensures walk is unique; avoiding dupes and speeding things up
        if not sparse:
            with header.data_ptr.stream_jump_to(stream) as handle:
                toc.load_data(handle)

        return cls(header, toc.drives, sparse)

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        raise NotImplementedError


File = abc_.FileABC
Folder = abc_.FolderABC
VirtualDrive = abc_.VirtualDriveABC


class APIv7(APIvX, _V7):
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
