from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, BinaryIO, Dict, Type

from serialization_tools.structx import Struct

from ...common import VersionLike
from ..common import ArchiveVersion, ArchiveRange


@dataclass
class VirtualDriveHeader:
    LAYOUT: ClassVar[Struct]

    path: str
    name: str

    sub_folder_range: ArchiveRange
    file_range: ArchiveRange
    unk: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, version: VersionLike) -> 'VirtualDriveHeader':
        header_class = _HEADER_VERSION_MAP.get(version)

        if not header_class:
            raise NotImplementedError(version)

        return header_class._unpack(stream)

    def _pack(self, stream: BinaryIO) -> int:
        args = self.path.encode("ascii"), self.name.encode("ascii"), self.sub_folder_range.start, self.sub_folder_range.end, \
               self.file_range.start, self.file_range.end, 0
        return self.LAYOUT.pack_stream(stream, *args)

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> 'VirtualDriveHeader':
        path, name, sub_folder_start, sub_folder_end, file_start, file_end, unk = cls.LAYOUT.unpack_stream(stream)
        path, name = path.decode("ascii").rstrip("\00"), name.decode("ascii").rstrip("\00")
        sub_folder_range = ArchiveRange(sub_folder_start, sub_folder_end)
        file_range = ArchiveRange(file_start, file_end)
        return cls(path, name, sub_folder_range, file_range, unk)


@dataclass
class DowIVirtualDriveHeader(VirtualDriveHeader):
    LAYOUT = Struct("< 64s 64s 4H 2s")


@dataclass
class DowIIVirtualDriveHeader(VirtualDriveHeader):
    LAYOUT = Struct("< 64s 64s 4H 2s")


@dataclass
class DowIIIVirtualDriveHeader(VirtualDriveHeader):
    LAYOUT = Struct("< 64s 64s 4L 4s")


_HEADER_VERSION_MAP: Dict[VersionLike, Type[VirtualDriveHeader]] = {
    ArchiveVersion.Dow: DowIVirtualDriveHeader,
    ArchiveVersion.Dow2: DowIIVirtualDriveHeader,
    ArchiveVersion.Dow3: DowIIIVirtualDriveHeader
}
