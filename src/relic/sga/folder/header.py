from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, BinaryIO, Dict, Type

from serialization_tools.structx import Struct

from ...common import VersionLike
from ..common import ArchiveRange, ArchiveVersion


@dataclass
class FolderHeader:
    LAYOUT: ClassVar[Struct]

    name_offset: int
    sub_folder_range: ArchiveRange
    file_range: ArchiveRange

    @classmethod
    def unpack(cls, stream: BinaryIO, version: VersionLike) -> 'FolderHeader':
        header_class = _HEADER_VERSION_MAP.get(version)

        if not header_class:
            raise NotImplementedError(version)

        return header_class._unpack(stream)

    def _pack(self, stream: BinaryIO) -> int:
        args = self.name_offset, self.sub_folder_range.start, self.sub_folder_range.end, \
               self.file_range.start, self.file_range.end
        return self.LAYOUT.pack_stream(stream, *args)

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> 'FolderHeader':
        name_offset, sub_folder_start, sub_folder_end, file_start, file_end = cls.LAYOUT.unpack_stream(stream)
        sub_folder_range = ArchiveRange(sub_folder_start, sub_folder_end)
        file_range = ArchiveRange(file_start, file_end)
        return cls(name_offset, sub_folder_range, file_range)


@dataclass
class DowIFolderHeader(FolderHeader):
    LAYOUT = Struct("< L 4H")


@dataclass
class DowIIFolderHeader(FolderHeader):
    LAYOUT = Struct("< L 4H")


@dataclass
class DowIIIFolderHeader(FolderHeader):
    LAYOUT = Struct("< 5L")


_HEADER_VERSION_MAP: Dict[VersionLike, Type[FolderHeader]] = {
    ArchiveVersion.Dow: DowIFolderHeader,
    ArchiveVersion.Dow2: DowIIFolderHeader,
    ArchiveVersion.Dow3: DowIIIFolderHeader
}
