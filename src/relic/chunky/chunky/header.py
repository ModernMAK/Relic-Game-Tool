from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Dict, Type, Optional, ClassVar

from serialization_tools.magic import MagicWordIO, MagicWord
from serialization_tools.structx import Struct


@dataclass
class Version:
    """ The Major Version; Relic refers to this as the 'Version' """
    major: int
    """ The Minor Version; Relic refers to this as the 'Product' """
    minor: Optional[int] = 0

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


# class ChunkyVersion(VersionEnum):
#     Unsupported = None
#     v0101 = Version(1, 1)
#     Dow = v0101  # ALIAS for Prettiness
#     v0301 = Version(3, 1)
#     Dow2 = v0301  # ALIAS for Prettiness
#     v4010 = Version(4, 1)
#
#     @classmethod
#     def unpack_version(cls, stream: BinaryIO) -> Version:
#         return Version(*ChunkyVersionLayout.unpack_stream(stream))
#
#     @classmethod
#     def pack_version(cls, stream: BinaryIO, version: VersionLike) -> int:
#         if isinstance(version, VersionEnum):
#             version = version.value
#         return ChunkyVersionLayout.pack_stream(stream, version.major, version.minor)
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO) -> ChunkyVersion:
#         return ChunkyVersion(cls.unpack_version(stream))
#
#     def pack(self, stream: BinaryIO) -> int:
#         return self.pack_version(stream, self)

ChunkyMagic = MagicWordIO(Struct("< 12s"), "Relic Chunky".encode("ascii"))
MultiBR_Magic = MagicWord(Struct("< 4s"), "".encode("ascii"))
# I forgot what the exact value was supposed to be (TODO)





@dataclass
class ChunkyHeaderV0301(ChunkyHeader):
    LAYOUT = Struct("< 3L")
    CONST = (36, 28, 1)

    @property
    def version(self) -> ChunkyVersion:
        return ChunkyVersion.v0301

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ChunkyHeader:
        args = cls.LAYOUT.unpack_stream(stream)
        assert args == cls.CONST, (args, cls.CONST)
        return cls()

    def _pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, *self.CONST)


_VERSION_MAP: Dict[VersionLike, Type[ChunkyHeader]] = {
    ChunkyVersion.v0101: ChunkyHeaderV0101,
    ChunkyVersion.v0301: ChunkyHeaderV0301
}
