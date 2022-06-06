from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Dict, Type

from serialization_tools.magic import MagicWordIO, MagicWord
from serialization_tools.structx import Struct

from relic.common import VersionEnum, Version, VersionLike, VersionError

ChunkyVersionLayout = Struct("< 2L")


class ChunkyVersion(VersionEnum):
    Unsupported = None
    v0101 = Version(1, 1)
    Dow = v0101  # ALIAS for Prettiness
    v0301 = Version(3, 1)
    Dow2 = v0301  # ALIAS for Prettiness
    v4010 = Version(4, 1)

    @classmethod
    def unpack_version(cls, stream: BinaryIO) -> Version:
        return Version(*ChunkyVersionLayout.unpack_stream(stream))

    @classmethod
    def pack_version(cls, stream: BinaryIO, version: VersionLike) -> int:
        if isinstance(version, VersionEnum):
            version = version.value
        return ChunkyVersionLayout.pack_stream(stream, version.major, version.minor)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ChunkyVersion:
        return ChunkyVersion(cls.unpack_version(stream))

    def pack(self, stream: BinaryIO) -> int:
        return self.pack_version(stream, self)


ChunkyMagic = MagicWordIO(Struct("< 12s"), "Relic Chunky".encode("ascii"))
MultiBR_Magic = MagicWord(Struct("< 4s"), "\r\n\x1a\0".encode("ascii"))  # I forgot what the exact value was supposed to be (TODO)


@dataclass
class ChunkyHeader:
    @property
    def version(self) -> ChunkyVersion:
        raise NotImplementedError

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ChunkyHeader:
        raise NotImplementedError

    def _pack(self, stream: BinaryIO) -> int:
        raise NotImplementedError

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ChunkyHeader:
        MultiBR_Magic.assert_magic_word(stream)
        version = ChunkyVersion.unpack(stream)

        class_type = _VERSION_MAP.get(version)
        if not class_type:
            raise VersionError(version, list(_VERSION_MAP.keys()))
        return class_type._unpack(stream)

    def pack(self, stream: BinaryIO) -> int:
        written = 0
        written += MultiBR_Magic.write_magic_word(stream)
        written += ChunkyVersion.pack_version(stream, self.version)
        written += self._pack(stream)
        return written


@dataclass
class ChunkyHeaderV0101(ChunkyHeader):
    @property
    def version(self) -> ChunkyVersion:
        return ChunkyVersion.v0101

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ChunkyHeader:
        return cls()

    def _pack(self, stream: BinaryIO) -> int:
        return 0


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
