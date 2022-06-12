from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from serialization_tools.structx import Struct
from typing import Optional, ClassVar, BinaryIO

from serialization_tools.magic import MagicWordIO


MagicWord = MagicWordIO(Struct("< 8s"), "_ARCHIVE".encode("ascii"))


@dataclass
class Version:
    """ The Major Version; Relic refers to this as the 'Version' """
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



class StorageType(int, Enum):
    Store = 0
    BufferCompress = 1
    StreamCompress = 2


class VerificationType(int, Enum):
    None_ = 0  # unknown real values, assuming incremental
    CRC = 1  # unknown real values, assuming incremental
    CRCBlocks = 2  # unknown real values, assuming incremental
    MD5Blocks = 3  # unknown real values, assuming incremental
    SHA1Blocks = 4  # unknown real values, assuming incremental
