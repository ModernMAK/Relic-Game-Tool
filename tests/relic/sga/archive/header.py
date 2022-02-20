# from __future__ import annotations
#
# from dataclasses import dataclass
# from typing import BinaryIO, Dict, Type, Tuple
#
# from archive_tools.structio import WindowPtr, Ptr
# from archive_tools.structx import Struct
# from archive_tools.magic import MagicWordIO
#
# from ...common import VersionLike, Version, VersionEnum
# from ..common import ArchiveVersion
#
# ArchiveMagicWord = MagicWordIO(Struct("< 8s"), "_ARCHIVE".encode("ascii"))
#
# _NAME_CHAR_COUNT = 64  # 64 characters max
# _NAME_CHAR_SIZE = 2  # UTF-16-le ~ 2 bytes per character
# _NAME_BYTE_SIZE = _NAME_CHAR_COUNT * _NAME_CHAR_SIZE
#
#
# @dataclass
# class ArchiveHeader:
#     VERSION_LAYOUT = Struct(f"< 2H")
#     name: str
#
#     toc_ptr: Ptr
#     data_ptr: WindowPtr
#
#     @property
#     def version(self) -> VersionLike:
#         raise NotImplementedError
#
#     @classmethod
#     def _unpack(cls, stream: BinaryIO) -> 'ArchiveHeader':
#         raise NotImplementedError
#
#     def _pack(self, stream: BinaryIO) -> int:
#         raise NotImplementedError
#
#     @classmethod
#     def unpack_version(cls, stream: BinaryIO) -> ArchiveVersion:
#         return ArchiveVersion(Version(*cls.VERSION_LAYOUT.unpack_stream(stream)))
#
#     @classmethod
#     def pack_version(cls, stream: BinaryIO, version: VersionLike) -> int:
#         if isinstance(version, VersionEnum):
#             version = version.value
#         return cls.VERSION_LAYOUT.pack_stream(stream, version.major, version.minor)
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveHeader':
#         if read_magic:
#             ArchiveMagicWord.assert_magic_word(stream, True)
#
#         version = cls.unpack_version(stream)
#         header_class = _HEADER_VERSION_MAP.get(version)
#
#         if not header_class:
#             raise NotImplementedError(version)
#
#         return header_class._unpack(stream)
#
#     def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
#         written = 0
#
#         if write_magic:
#             written += ArchiveMagicWord.write_magic_word(stream)
#
#         written += self.pack_version(stream, self.version)
#         written += self._pack(stream)
#         return written
#
#
# @dataclass
# class DowIArchiveHeader(ArchiveHeader):
#     # hash, name, hash (repeated), TOC_SIZE, DATA_OFFSET
#     LAYOUT = Struct(f"< 16s {_NAME_BYTE_SIZE}s 16s 2L")
#     toc_ptr: WindowPtr
#     checksums: Tuple[int, int]
#
#     @property
#     def version(self) -> VersionLike:
#         return ArchiveVersion.Dow
#
#     @classmethod
#     def _unpack(cls, stream: BinaryIO) -> 'DowIArchiveHeader':
#         csum_a, name, csum_b, toc_size, data_offset = cls.LAYOUT.unpack_stream(stream)
#
#         name = name.decode("utf-16-le")
#         toc_ptr = WindowPtr(offset=stream.tell(), size=toc_size)
#
#         data_ptr = WindowPtr(offset=data_offset, size=None)
#
#         return cls(name, toc_ptr, data_ptr, (csum_a, csum_b))
#
#     def _pack(self, stream: BinaryIO) -> int:
#         args = self.checksums[0], self.name, self.checksums[1]
#         return self.LAYOUT.pack_stream(stream, *args)
#
#
# @dataclass
# class DowIIArchiveHeader(ArchiveHeader):
#     # hash, name, hash (repeated), TOC_SIZE, DATA_OFFSET, TOC_POS, RESERVED:1, RESERVED:0?, UNK???
#     LAYOUT = Struct(f"< 16s {_NAME_BYTE_SIZE}s 16s 3L 3L")
#     toc_ptr: WindowPtr
#     checksum: int
#     unk: int
#
#     @property
#     def version(self) -> VersionLike:
#         return ArchiveVersion.Dow2
#
#     @classmethod
#     def _unpack(cls, stream: BinaryIO) -> 'DowIIArchiveHeader':
#         csum, name, csum_red, toc_size, data_offset, toc_pos, rsv_1, rsv_0, unk = cls.LAYOUT.unpack_stream(stream)
#
#         assert csum == csum_red  # TODO raise an appropriate error
#         assert rsv_1 == 1
#         assert rsv_0 == 0
#
#         name = name.decode("utf-16-le")
#         toc_ptr = WindowPtr(offset=toc_pos, size=toc_size)
#         data_ptr = WindowPtr(offset=data_offset)
#
#         return cls(name, toc_ptr, data_ptr, csum, unk)
#
#     def _pack(self, stream: BinaryIO) -> int:
#         args = self.checksum, self.name, self.checksum, self.toc_ptr.size, self.data_ptr.offset, self.toc_ptr.offset, 1, 0, self.unk
#         return self.LAYOUT.pack_stream(stream, *args)
#
#
# @dataclass
# class DowIIIArchiveHeader(ArchiveHeader):
#     # name, TOC_POS, TOC_SIZE, DATA_POS, DATA_SIZE, RESERVED:0?, RESERVED:1, RESERVED:0?, UNK???
#     LAYOUT = Struct(f"<{_NAME_BYTE_SIZE}s Q L Q 4L 256s")
#     toc_ptr: WindowPtr
#     data_ptr: WindowPtr
#
#     unk: bytes
#
#     @property
#     def version(self) -> VersionLike:
#         return ArchiveVersion.Dow2
#
#     @classmethod
#     def _unpack(cls, stream: BinaryIO) -> ArchiveHeader:
#         name, toc_pos, toc_size, data_pos, data_size, rsv_0_a, rsv_1, rsv_0_b, unk = cls.LAYOUT.unpack_stream(stream)[0]
#
#         assert rsv_1 == 1
#         assert rsv_0_a == 0
#         assert rsv_0_b == 0
#
#         toc_ptr = WindowPtr(offset=toc_pos, size=toc_size)
#         data_ptr = WindowPtr(offset=data_pos, size=data_size)
#         name = name.decode("utf-16-le")
#
#         return cls(name, toc_ptr, data_ptr, unk)
#
#     def _pack(self, stream: BinaryIO) -> int:
#         args = (self.name, self.toc_ptr.offset, self.toc_ptr.size, self.data_ptr.offset, self.data_ptr.size, 0, 1, self.unk)
#         return self.LAYOUT.pack_stream(stream, *args)
#
#
# _HEADER_VERSION_MAP: Dict[VersionLike, Type[ArchiveHeader]] = {
#     ArchiveVersion.Dow: DowIArchiveHeader,
#     ArchiveVersion.Dow2: DowIIArchiveHeader,
#     ArchiveVersion.Dow3: DowIIIArchiveHeader
# }
