from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, ClassVar

from serialization_tools.magic import MagicWordIO
from serialization_tools.structx import Struct


class ChunkType(str, Enum):
    Folder = "FOLD"
    Data = "DATA"


class ChunkFourCC:
    def __init__(self, code: str):
        if len(code) != 4:
            raise NotImplementedError
        self.code = code

    def __str__(self):
        return self.code

    def __eq__(self, other):
        return self.code == other.code


class ChunkFourCCPath:
    def __init__(self, *parts: ChunkFourCC):
        self.parts = parts

    @property
    def parent(self):
        parent_parts = self.parts[:-1]
        return ChunkFourCCPath(*parent_parts)

    def __truediv__(self, value: ChunkFourCC):
        return ChunkFourCCPath(*self.parts, value)

    def __rtruediv__(self, value: ChunkFourCC):
        return ChunkFourCCPath(value, *self.parts)

    def __str__(self):
        part_str = [str(cc) for cc in self.parts]
        return ".".join(part_str)

    def __eq__(self, other):
        return self.parts == other.parts


@dataclass
class Version:
    """
    A `Chunky Version`
    """
    """ The Major Version """
    major: int
    """ The Minor Version, this is typically `1` """
    minor: int = 1

    LAYOUT: ClassVar[Struct] = Struct("<2I")

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


MagicWord = MagicWordIO(Struct("< 16s"), b"Relic Chunky\r\n\x1a\0")  # We include \r\n\x1a\0 because it signals a properly formatted file
