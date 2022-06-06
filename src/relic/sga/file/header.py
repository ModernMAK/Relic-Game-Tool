from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, ClassVar, Type, Dict

from serialization_tools.ioutil import Ptr, WindowPtr
from serialization_tools.structx import Struct

from ..common import ArchiveVersion
from ...common import VersionLike


class FileCompressionFlag(Enum):
    # Compression flag is either 0 (Decompressed) or 16/32 which are both compressed
    # Aside from 0; these appear to be the Window-Sizes for the Zlib Compression (In KibiBytes)
    Decompressed = 0

    Compressed16 = 16
    Compressed32 = 32

    def compressed(self) -> bool:
        return self != FileCompressionFlag.Decompressed


@dataclass
class FileHeader:
    LAYOUT: ClassVar[Struct]
    name_sub_ptr: Ptr  # Sub ptr is expected to be used via window (E.G. 'WindowPtr() as handle', then, 'data_sub_ptr.stream_jump_to(handle)')
    data_sub_ptr: Ptr
    decompressed_size: int
    compressed_size: int

    @property
    def compressed(self):
        raise NotImplementedError

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> FileHeader:
        raise NotImplementedError

    def _pack(self, stream: BinaryIO) -> int:
        raise NotImplementedError

    def pack(self, stream: BinaryIO) -> int:
        return self._pack(stream)

    @classmethod
    def unpack(cls, stream: BinaryIO, version: VersionLike) -> FileHeader:
        header_class = _HEADER_VERSION_MAP.get(version)

        if not header_class:
            raise NotImplementedError(version)

        return header_class._unpack(stream)


@dataclass
class DowIFileHeader(FileHeader):
    # name
    LAYOUT = Struct(f"<5L")
    compression_flag: FileCompressionFlag

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> DowIFileHeader:
        name_offset, compression_flag_value, data_offset, decompressed_size, compressed_size = cls.LAYOUT.unpack_stream(stream)
        compression_flag = FileCompressionFlag(compression_flag_value)
        name_ptr = Ptr(name_offset)
        data_ptr = WindowPtr(data_offset, compressed_size)
        return cls(name_ptr, data_ptr, decompressed_size, compressed_size, compression_flag)

    def _pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.name_sub_ptr.offset, self.compression_flag.value, self.data_sub_ptr.offset, self.decompressed_size, self.compressed_size)

    @property
    def compressed(self):
        return self.compression_flag.compressed()


@dataclass
class DowIIFileHeader(FileHeader):
    LAYOUT = Struct(f"<5L H")
    unk_a: int
    unk_b: int

    @property
    def compressed(self):
        return self.compressed_size < self.decompressed_size

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> DowIIFileHeader:
        name_off, data_off, comp_size, decomp_size, unk_a, unk_b = cls.LAYOUT.unpack_stream(stream)
        # Name, File, Compressed, Decompressed, ???, ???
        name_ptr = Ptr(name_off)
        data_ptr = Ptr(data_off)
        return cls(name_ptr, data_ptr, decomp_size, comp_size, unk_a, unk_b)

    def _pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.name_sub_ptr.offset, self.data_sub_ptr.offset, self.compressed_size, self.decompressed_size, self.unk_a, self.unk_b)


@dataclass
class DowIIIFileHeader(FileHeader):
    LAYOUT = Struct("< 7L H L")
    unk_a: int
    unk_b: int
    unk_c: int
    unk_d: int  # 256?
    unk_e: int

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> DowIIIFileHeader:
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

    def _pack(self, stream: BinaryIO) -> int:
        args = self.name_sub_ptr.offset, self.unk_a, self.data_sub_ptr.offset, self.unk_b, self.compressed_size, self.decompressed_size, self.unk_c, self.unk_d, self.unk_e
        return self.LAYOUT.pack_stream(stream, *args)

    @property
    def compressed(self):
        return self.compressed_size < self.decompressed_size


_HEADER_VERSION_MAP: Dict[VersionLike, Type[FileHeader]] = {
    ArchiveVersion.Dow: DowIFileHeader,
    ArchiveVersion.Dow2: DowIIFileHeader,
    ArchiveVersion.Dow3: DowIIIFileHeader
}
