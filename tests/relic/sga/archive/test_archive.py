from typing import BinaryIO

from tests.helpers import get_sga_paths, TF
from relic.sga.archive import Archive, ArchiveMagicWord

archive_paths = get_sga_paths()


def sga_seek_to_start(stream: BinaryIO, include_magic: bool = True):
    if include_magic:
        stream.seek(0)
    else:
        stream.seek(ArchiveMagicWord.layout.size)


def test_archive_unpack():
    for archive in archive_paths:
        with open(archive, "rb") as handle:

            # Read from file, always assume we need to read magic
            for sparse in TF:
                for read_magic in TF:
                    sga_seek_to_start(handle, read_magic)
                    _ = Archive.unpack(handle, read_magic=read_magic, sparse=sparse)
#
#
# @dataclass
# class Archive(DriveCollection):
#     header: ArchiveHeader
#     """Sparse represents whether data was loaded on creation."""
#     _sparse: bool
#
#     def __init__(self, header: ArchiveHeader, drives: List[VirtualDrive], _sparse: bool):
#         self.header = header
#         self._sparse = _sparse
#         self.drives = drives
#
#     def walk(self) -> ArchiveWalk:
#         return walk(self)
#
#     @classmethod
#     def _unpack(cls, stream: BinaryIO, header: ArchiveHeader, sparse: bool = True):
#         from ..toc import ArchiveTableOfContents, ArchiveTableOfContentsPtr, ArchiveTableOfContentsHeaders
#         version = header.version
#         with header.toc_ptr.stream_jump_to(stream) as handle:
#             toc_ptr = ArchiveTableOfContentsPtr.unpack_version(handle, version)
#             toc_headers = ArchiveTableOfContentsHeaders.unpack(handle, toc_ptr, version)
#             toc = ArchiveTableOfContents.create(toc_headers)
#
#         toc.load_toc()
#         toc.build_tree()  # ensures walk is unique; avoiding dupes and speeding things up
#         if not sparse:
#             with header.data_ptr.stream_jump_to(stream) as handle:
#                 toc.load_data(handle)
#
#         return cls(header, toc.drives, sparse)
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO, read_magic: bool = True, sparse: bool = True) -> Archive:
#         header = ArchiveHeader.unpack(stream, read_magic)
#         class_type = _VERSION_MAP[header.version]
#         return class_type._unpack(stream, header, sparse)  # Defer to subclass (ensures packing works as expected)
#
#     def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
#         raise NotImplementedError
#
#
# @dataclass(init=False)
# class DowIArchive(Archive):
#     def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
#         pass
#
#
# @dataclass(init=False)
# class DowIIArchive(Archive):
#     def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
#         pass
#
#
# @dataclass(init=False)
# class DowIIIArchive(Archive):
#     def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
#         pass
#
#
# _VERSION_MAP: Dict[VersionLike, Type[Archive]] = {
#     ArchiveVersion.Dow: DowIArchive,
#     ArchiveVersion.Dow2: DowIIArchive,
#     ArchiveVersion.Dow3: DowIIIArchive
# }
