from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Dict

from serialization_tools.ioutil import Ptr, WindowPtr
from serialization_tools.structx import Struct

from relic.common import VersionLike
from relic.sga import abc_
from relic.sga.abc_ import VirtualDriveHeaderABC, ArchiveToCPtrABC, FolderHeaderABC, FileHeaderABC, ArchiveABC, ArchiveHeaderABC, ArchiveTableOfContentsHeadersABC, NameBufferABC
from relic.sga.common import ArchiveVersion
from relic.sga.protocols import ArchiveHeader
from relic.sga.vX import APIvX

version = ArchiveVersion.v9


class _V9:
    """Mixin to allow classes to add `version` from the module level to the class level"""
    version = version  # classvar = modulevar


@dataclass
class VirtualDriveHeader(VirtualDriveHeaderABC, _V9):
    LAYOUT = Struct("< 64s 64s 4L 4s")


@dataclass
class ArchiveToCPtr(ArchiveToCPtrABC, _V9):
    LAYOUT = Struct("< 8L")


@dataclass
class FolderHeader(FolderHeaderABC, _V9):
    LAYOUT = Struct("< 5L")


@dataclass
class FileHeader(FileHeaderABC, _V9):
    LAYOUT = Struct("< 7L H L")
    unk_a: int
    unk_b: int
    unk_c: int
    unk_d: int  # 256?
    unk_e: int

    def __eq__(self, other):
        return self.unk_a == other.unk_a and self.unk_b == other.unk_b and self.unk_c == other.unk_c and self.unk_d == other.unk_d and self.unk_e == other.unk_e and super().__eq__(other)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> FileHeader:
        name_off, unk_a, data_off, unk_b, comp_size, decomp_size, unk_c, unk_d, unk_e = cls.LAYOUT.unpack_stream(stream)
        # assert unk_a == 0, (unk_a, 0)
        # assert unk_b == 0, (unk_b, 0)
        # UNK_D is a new compression flag?!
        # if comp_size != decomp_size:
        #     assert unk_d in [256,512], ((comp_size, decomp_size), (unk_d, [256,512]), (name_off, unk_a, data_off, unk_b, comp_size, decomp_size, unk_c, unk_d, unk_e))
        # Pulling stuff out of my ass; but dividing them by the max block size gets you 7, 6 respectively
        # Name, File, Compressed, Decompressed, ???, ???
        name_ptr = Ptr(name_off)
        data_ptr = Ptr(data_off)
        return cls(name_ptr, data_ptr, decomp_size, comp_size, unk_a, unk_b, unk_c, unk_d, unk_e)

    def pack(self, stream: BinaryIO) -> int:
        args = self.name_sub_ptr.offset, self.unk_a, self.data_sub_ptr.offset, self.unk_b, self.compressed_size, self.decompressed_size, self.unk_c, self.unk_d, self.unk_e
        return self.LAYOUT.pack_stream(stream, *args)

    @property
    def compressed(self):
        return self.compressed_size < self.decompressed_size


@dataclass
class ArchiveHeader(ArchiveHeaderABC, _V9):
    # name, TOC_POS, TOC_SIZE, DATA_POS, DATA_SIZE, RESERVED:0?, RESERVED:1, RESERVED:0?, UNK???
    LAYOUT = Struct(f"<128s QL QL 2L 256s")
    toc_ptr: WindowPtr
    data_ptr: WindowPtr

    unk: bytes

    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True) -> bool:
        """
        Dawn of War III does not contain any checksums, and so will always return true.

        :param stream: Ignored
        :param fast: Ignored
        :param _assert: Ignored
        :returns: True
        """
        return True

    @property
    def version(self) -> VersionLike:
        return ArchiveVersion.Dow3

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ArchiveHeader:
        name, toc_pos, toc_size, data_pos, data_size, rsv_0_a, rsv_1, unk = cls.LAYOUT.unpack_stream(stream)

        assert rsv_1 == 1
        assert rsv_0_a == 0
        toc_ptr = WindowPtr(offset=toc_pos, size=toc_size)
        data_ptr = WindowPtr(offset=data_pos, size=data_size)
        name = name.decode("utf-16-le").rstrip("\0")

        return cls(name, toc_ptr, data_ptr, unk)

    def pack(self, stream: BinaryIO) -> int:
        args = self.name.encode("utf-16-le"), self.toc_ptr.offset, self.toc_ptr.size, self.data_ptr.offset, self.data_ptr.size, 0, 1, self.unk
        return self.LAYOUT.pack_stream(stream, *args)

    def __eq__(self, other):
        # TODO make issue to add equality to WindowPtr/Ptr
        return self.name == other.name and self.unk == other.unk \
               and self.toc_ptr.size == other.toc_ptr.size and self.toc_ptr.offset == other.toc_ptr.offset \
               and self.data_ptr.size == other.data_ptr.size and self.data_ptr.offset == other.data_ptr.offset \
               and self.version == other.version


File = abc_.FileABC
Folder = abc_.FolderABC
VirtualDrive = abc_.VirtualDriveABC


class NameBuffer(NameBufferABC):
    @classmethod
    def unpack(cls, stream: BinaryIO, buffer_size: int) -> Dict[int, str]:
        """ Dow III uses a 'buffer size' instead of a 'name count' to unpack names """
        buffer = stream.read(buffer_size)
        parts = buffer.split(b"\0")
        lookup = {}
        offset = 0
        for name in parts:
            lookup[offset] = name.decode("ascii")
            offset += len(name) + 1  # +1 to account for b'\0'
        return lookup


class ArchiveTableOfContentsHeaders(ArchiveTableOfContentsHeadersABC):
    VDRIVE_HEADER_CLS = VirtualDriveHeader
    FOLDER_HEADER_CLS = FolderHeader
    FILE_HEADER_CLS = FileHeader
    NAME_BUFFER_CLS = NameBuffer


@dataclass(init=False)
class Archive(ArchiveABC, _V9):
    TOC_PTR_CLS = ArchiveToCPtr
    TOC_HEADERS_CLS = ArchiveTableOfContentsHeaders

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        raise NotImplementedError


class APIv9(APIvX, _V9):
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
