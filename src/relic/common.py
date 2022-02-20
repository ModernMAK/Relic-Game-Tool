from dataclasses import dataclass
from enum import Enum
from typing import Union, Optional

from archive_tools.structx import Struct


class VersionEnum(Enum):

    def __eq__(self, other):
        if isinstance(other, VersionEnum):
            return self.value == other.value
        elif isinstance(other, Version):
            return self.value == other
        else:
            super().__eq__(other)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return self.value.__hash__()



@dataclass
class Version:
    major: int
    minor: Optional[int] = 0

    _32 = Struct("< H H")
    _64 = Struct("< L L")

    def __str__(self) -> str:
        return f"Version {self.major}.{self.minor}"

    def __eq__(self, other):
        if other is None:
            return False
        elif isinstance(other, VersionEnum):
            return self.major == other.value.major and self.minor == other.value.minor
        elif isinstance(other, Version):
            return self.major == other.major and self.minor == other.minor
        else:
            return super().__eq__(other)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        # Realistically; Version will always be <256
        # But we could manually set it to something much bigger by accident; and that may cause collisions
        return self.major << 32 + self.minor
    #
    # @classmethod
    # def unpack_32(cls, stream: BinaryIO):
    #     return Version(*cls.__32.unpack_stream(stream))
    #
    # @classmethod
    # def unpack_64(cls, stream: BinaryIO):
    #     return Version(*cls.__64.unpack_stream(stream))
    #
    # def pack_32(self, stream: BinaryIO) -> int:
    #     args = self.minor, self.minor
    #     return self.__32.pack_stream(stream, *args)
    #
    # def pack_64(self, stream: BinaryIO) -> int:
    #     args = self.minor, self.minor
    #     return self.__64.pack_stream(stream, *args)


VersionLike = Union[Version, VersionEnum]