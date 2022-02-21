from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, Dict

from archive_tools.ioutil import as_hex_adr, abs_tell
from archive_tools.vstruct import VStruct

from ..chunky.header import ChunkyVersion
from ...common import VersionLike


class ChunkType(Enum):
    Folder = "FOLD"
    Data = "DATA"


@dataclass
class ChunkHeader:
    type: ChunkType
    id: str
    version: int
    size: int
    name: str

    @property
    def chunky_version(self) -> ChunkyVersion:
        raise NotImplementedError

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ChunkHeader:
        raise NotImplementedError

    def _pack(self, stream: BinaryIO) -> int:
        raise NotImplementedError

    @classmethod
    def unpack(cls, stream: BinaryIO, chunky_version: ChunkyVersion) -> 'ChunkHeader':
        class_type = _VERSION_MAP[chunky_version]
        return class_type._unpack(stream)

    def pack(self, stream: BinaryIO) -> int:
        return self.pack(stream)

    def copy(self) -> ChunkHeader:
        raise NotImplementedError


# TODO Find a good solution to version in class names
#  OH GOD VERSION NAMES IN THE CLASS, I've tried V(#)p(#), V(hex #)(hex #) and they both look ugly
#  Sticking to hex since it looks less bad

@dataclass
class ChunkHeaderV0101(ChunkHeader):
    LAYOUT = VStruct("< 4s 4s 2L v")

    @property
    def chunky_version(self) -> ChunkyVersion:
        return ChunkyVersion.v0101

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ChunkHeader:
        args = cls.LAYOUT.unpack_stream(stream)
        chunk_type = args[0].decode("ascii")
        _ = as_hex_adr(abs_tell(stream))
        chunk_type = ChunkType(chunk_type)
        chunk_id = args[1].decode("ascii").strip("\x00")
        version, size = args[2:4]
        name = args[4].decode("ascii").rstrip("\x00")
        return cls(chunk_type, chunk_id, version, size, name)

    def _pack(self, stream: BinaryIO) -> int:
        args = self.type.value, self.id, self.chunky_version, self.size, self.name
        return self.LAYOUT.pack_stream(stream, *args)

@dataclass
class ChunkHeaderV0301(ChunkHeader):
    LAYOUT = VStruct("< 4s 4s 2L v 2L")
    unk_a: int
    unk_b: int

    @property
    def chunky_version(self) -> ChunkyVersion:
        return ChunkyVersion.v0301

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ChunkHeader:
        args = cls.LAYOUT.unpack_stream(stream)
        chunk_type = ChunkType(args[0].decode("ascii"))
        chunk_id = args[1].decode("ascii").strip("\x00")
        version, size = args[2:4]
        name = args[4].decode("ascii").rstrip("\x00")
        unks = args[5:6]
        return cls(chunk_type, chunk_id, version, size, name, *unks)

    def _pack(self, stream: BinaryIO) -> int:
        args = self.type.value, self.id, self.chunky_version, self.size, self.name, self.unk_a, self.unk_b
        return self.LAYOUT.pack_stream(stream, *args)


_VERSION_MAP: Dict[VersionLike, ChunkHeader] = {
    ChunkyVersion.v0101: ChunkHeaderV0101,
    ChunkyVersion.v0301: ChunkHeaderV0301
}
