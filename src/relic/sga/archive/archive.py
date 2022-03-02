from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, List, Type, Dict, TYPE_CHECKING

from .header import ArchiveHeader
from ..common import ArchiveVersion
from ..hierarchy import DriveCollection, ArchiveWalk, walk
from ...common import VersionLike

if TYPE_CHECKING:
    from ..toc.toc import ArchiveTableOfContents
    from ..toc.toc_headers import ArchiveTableOfContentsHeaders
    from ..toc.toc_ptr import ArchiveTableOfContentsPtr
    from ..vdrive.virtual_drive import VirtualDrive


@dataclass
class Archive(DriveCollection):
    header: ArchiveHeader
    """Sparse represents whether data was loaded on creation."""
    _sparse: bool

    def __init__(self, header: ArchiveHeader, drives: List[VirtualDrive], _sparse: bool):
        self.header = header
        self._sparse = _sparse
        self.drives = drives

    def walk(self) -> ArchiveWalk:
        return walk(self)

    @classmethod
    def _unpack(cls, stream: BinaryIO, header: ArchiveHeader, sparse: bool = True):
        from ..toc import ArchiveTableOfContents, ArchiveTableOfContentsPtr, ArchiveTableOfContentsHeaders
        version = header.version
        with header.toc_ptr.stream_jump_to(stream) as handle:
            toc_ptr = ArchiveTableOfContentsPtr.unpack_version(handle, version)
            toc_headers = ArchiveTableOfContentsHeaders.unpack(handle, toc_ptr, version)
            toc = ArchiveTableOfContents.create(toc_headers)

        toc.load_toc()
        toc.build_tree()  # ensures walk is unique; avoiding dupes and speeding things up
        if not sparse:
            with header.data_ptr.stream_jump_to(stream) as handle:
                toc.load_data(handle)

        return cls(header, toc.drives, sparse)

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True, sparse: bool = True, *, validate: bool = True) -> Archive:
        header = ArchiveHeader.unpack(stream, read_magic)
        if validate:
            header.validate_checksums(stream)
        class_type = _VERSION_MAP[header.version]
        return class_type._unpack(stream, header, sparse)  # Defer to subclass (ensures packing works as expected)

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        raise NotImplementedError


@dataclass(init=False)
class DowIArchive(Archive):
    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        pass


@dataclass(init=False)
class DowIIArchive(Archive):
    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        pass


@dataclass(init=False)
class DowIIIArchive(Archive):
    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        pass


_VERSION_MAP: Dict[VersionLike, Type[Archive]] = {
    ArchiveVersion.Dow: DowIArchive,
    ArchiveVersion.Dow2: DowIIArchive,
    ArchiveVersion.Dow3: DowIIIArchive
}
