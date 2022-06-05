from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, Dict, Type, Union

from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct

from ..chunky.header import ChunkyVersion
from ...common import VersionLike, VersionError


class ChunkType(Enum):
    Folder = "FOLD"
    Data = "DATA"

    @classmethod
    def parse(cls, value: Union[str, bytes]) -> ChunkType:
        if isinstance(value, bytes):
            try:
                _ = value.decode("ascii")
            except UnicodeDecodeError:
                raise ChunkTypeError(value)
            value = _
        try:
            return ChunkType(value)
        except ValueError:
            raise ChunkTypeError(value)


class ChunkError(Exception):
    pass


class ChunkTypeError(ChunkError):
    def __init__(self, chunk_type: Union[bytes, str] = None, *args):
        super().__init__(*args)
        self.chunk_type = chunk_type

    def __str__(self):
        msg = f"ChunkType must be {repr(ChunkType.Folder.value)} or {repr(ChunkType.Data.value)}"
        if not self.chunk_type:
            return msg + "!"
        else:
            return msg + f"; got {repr(self.chunk_type)}!"


class ChunkNameError(ChunkError):
    def __init__(self, name: Union[bytes, str] = None, *args):
        super().__init__(*args)
        self.name = name

    def __str__(self):
        msg = f"Chunk name was not parsable ascii text"
        if not self.name:
            return msg + "!"
        else:
            return msg + f"; got {repr(self.name)}!"


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
    def unpack(cls, stream: BinaryIO, chunky_version: ChunkyVersion) -> ChunkHeader:
        class_type = _VERSION_MAP.get(chunky_version)
        if not class_type:
            raise VersionError(chunky_version, list(_VERSION_MAP.keys()))
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
    CHUNK_TYPE_MAGIC_LAYOUT = Struct("< 4s")  # Seperated so we can raise an error before reading vlen
    LAYOUT = VStruct("< 4s 2l v")

    @property
    def chunky_version(self) -> ChunkyVersion:
        return ChunkyVersion.v0101

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ChunkHeader:
        chunk_type = cls.CHUNK_TYPE_MAGIC_LAYOUT.unpack_stream(stream)[0]
        chunk_type = ChunkType.parse(chunk_type)

        chunk_id, version, size, raw_name = cls.LAYOUT.unpack_stream(stream)
        chunk_id = chunk_id.decode("ascii").strip("\x00")
        try:
            name = raw_name.decode("ascii").rstrip("\x00")
        except UnicodeDecodeError as e:
            raise ChunkNameError(raw_name) from e
        return cls(chunk_type, chunk_id, version, size, name)

    def _pack(self, stream: BinaryIO) -> int:
        args = self.type.value, self.id, self.chunky_version, self.size, self.name
        return self.LAYOUT.pack_stream(stream, *args)


@dataclass
class ChunkHeaderV0301(ChunkHeader):
    LAYOUT = VStruct("< 4s 4s 3L 2l")  # 2L v 2L")

    unk_a: int
    unk_b: int

    @property
    def chunky_version(self) -> ChunkyVersion:
        return ChunkyVersion.v0301

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ChunkHeader:
        chunk_type, chunk_id, version, size, name_size, unk_a, unk_b = cls.LAYOUT.unpack_stream(stream)
        chunk_type = ChunkType(chunk_type.decode("ascii"))
        chunk_id = chunk_id.decode("ascii").strip("\x00")
        name = stream.read(name_size).decode("ascii").rstrip("\00")
        return cls(chunk_type, chunk_id, version, size, name, *(unk_a, unk_b))

    def _pack(self, stream: BinaryIO) -> int:
        args = self.type.value, self.id, self.chunky_version, self.size, self.name, self.unk_a, self.unk_b
        return self.LAYOUT.pack_stream(stream, *args)


_VERSION_MAP: Dict[VersionLike, Type[ChunkHeader]] = {
    ChunkyVersion.v0101: ChunkHeaderV0101,
    ChunkyVersion.v0301: ChunkHeaderV0301
}
