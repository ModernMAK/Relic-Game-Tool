from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Dict, Type, ClassVar, Tuple

from serialization_tools.ioutil import Ptr
from serialization_tools.structx import Struct

from ...common import VersionLike
from ..archive import ArchiveVersion


@dataclass
class TocItemPtr(Ptr):
    def __init__(self, offset: int, count: int, whence: int = 0):
        super().__init__(offset, whence)
        self.count = count


@dataclass
class ArchiveTableOfContentsPtr:
    # Virtual Drives (offset, count), Folder (offset, count), File (offset, count), Names (offset, count)
    LAYOUT: ClassVar[Struct]
    virtual_drive_ptr: TocItemPtr
    folder_ptr: TocItemPtr
    file_ptr: TocItemPtr
    name_ptr: TocItemPtr

    @property
    def version(self) -> ArchiveVersion:
        raise NotImplementedError

    @classmethod
    def _unpack_tuple(cls, stream: BinaryIO) -> Tuple[TocItemPtr, TocItemPtr, TocItemPtr, TocItemPtr]:
        vd_offset, vd_count, fold_offset, fold_count, file_offset, file_count, name_offset, name_count = cls.LAYOUT.unpack_stream(stream)
        vd_ptr = TocItemPtr(vd_offset, vd_count)
        fold_ptr = TocItemPtr(fold_offset, fold_count)
        file_ptr = TocItemPtr(file_offset, file_count)
        name_ptr = TocItemPtr(name_offset, name_count)
        return vd_ptr, fold_ptr, file_ptr, name_ptr

    def _pack_tuple(self) -> Tuple[int, int, int, int, int, int, int, int]:
        return self.virtual_drive_ptr.offset, self.virtual_drive_ptr.count, \
               self.folder_ptr.offset, self.folder_ptr.count, \
               self.file_ptr.offset, self.file_ptr.count, \
               self.name_ptr.offset, self.name_ptr.count

    @classmethod
    def unpack_version(cls, stream: BinaryIO, version: VersionLike) -> 'ArchiveTableOfContentsPtr':
        toc_ptr_class = _ToCPtr_VERSION_MAP.get(version)

        if not toc_ptr_class:
            raise NotImplementedError(version)

        return toc_ptr_class.unpack(stream)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ArchiveTableOfContentsPtr':
        args = cls._unpack_tuple(stream)
        return cls(*args)

    def pack(self, stream: BinaryIO) -> int:
        args = self._pack_tuple()
        return self.LAYOUT.pack_stream(stream, *args)


# Alias
ArchiveToCPtr = ArchiveTableOfContentsPtr


@dataclass
class DowIArchiveToCPtr(ArchiveToCPtr):
    @property
    def version(self) -> ArchiveVersion:
        return ArchiveVersion.Dow

    LAYOUT = Struct("< LH LH LH LH")


@dataclass
class DowIIArchiveToCPtr(ArchiveToCPtr):
    LAYOUT = DowIArchiveToCPtr.LAYOUT

    @property
    def version(self) -> ArchiveVersion:
        return ArchiveVersion.Dow2


@dataclass
class DowIIIArchiveToCPtr(ArchiveToCPtr):
    LAYOUT = Struct("< 8L")

    @property
    def version(self) -> ArchiveVersion:
        return ArchiveVersion.Dow3


_ToCPtr_VERSION_MAP: Dict[VersionLike, Type[ArchiveToCPtr]] = {
    ArchiveVersion.Dow: DowIArchiveToCPtr,
    ArchiveVersion.Dow2: DowIIArchiveToCPtr,
    ArchiveVersion.Dow3: DowIIIArchiveToCPtr
}
