from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterator, BinaryIO

from serialization_tools.structx import Struct

from ..common import VersionEnum, Version, VersionLike

ArchiveVersionLayout = Struct("< 2H")


class ArchiveVersion(VersionEnum):
    Unsupported = None
    Dow = Version(2)
    Dow2 = Version(5)
    Dow3 = Version(9)

    @classmethod
    def unpack_version(cls, stream: BinaryIO) -> Version:
        return Version(*ArchiveVersionLayout.unpack_stream(stream))

    @classmethod
    def pack_version(cls, stream: BinaryIO, version: VersionLike) -> int:
        if isinstance(version, VersionEnum):
            version = version.value
        return ArchiveVersionLayout.pack_stream(stream, version.major, version.minor)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ArchiveVersion:
        return ArchiveVersion(cls.unpack_version(stream))

    def pack(self, stream: BinaryIO) -> int:
        return self.pack_version(stream, self)


@dataclass
class ArchiveRange:
    start: int
    end: int
    __iterable: Optional[Iterator] = None

    @property
    def size(self) -> int:
        return self.end - self.start

    # We don't use iterable to avoid x
    def __iter__(self) -> ArchiveRange:
        self.__iterable = iter(range(self.start, self.end))
        return self

    def __next__(self) -> int:
        return next(self.__iterable)
