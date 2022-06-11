from __future__ import annotations

from pathlib import PurePath, PurePosixPath
from typing import BinaryIO, Protocol, runtime_checkable, List, Optional, Iterable, Tuple

from serialization_tools.ioutil import Ptr, WindowPtr

from relic.common import VersionLike


@runtime_checkable
class ArchiveHeader(Protocol):
    name: str
    toc_ptr: Ptr
    data_ptr: WindowPtr

    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True) -> bool:
        """
        Validates header checksums against the content's of the stream.

        The stream should return to its original position when it was passed in.

        :param stream: The binary stream to read from
        :param fast: When true, slow checksums may be skipped
        :param _assert: When true, an assertion is raised instead of returning False
        :returns: True if all checksums match (or the type does not have checksums to validate)
        :raises AssertionError: if a checksum does not match and _assert is True
        """
        raise NotImplementedError

    # @classmethod
    # @property
    # def version(self) -> VersionLike:
    #     raise NotImplementedError

    @classmethod
    def unpack(cls, stream: BinaryIO) -> ArchiveHeader:
        raise NotImplementedError

    def pack(self, stream: BinaryIO) -> int:
        raise NotImplementedError


@runtime_checkable
class ArchiveWalkable(Protocol):
    def walk(self) -> ArchiveWalk:
        raise NotImplementedError


@runtime_checkable
class DriveCollection(Protocol):
    drives: List[VirtualDrive]


@runtime_checkable
class FolderCollection(Protocol):
    sub_folders: List[Folder]


@runtime_checkable
class FileCollection(Protocol):
    files: List[File]


@runtime_checkable
class FolderChild(Protocol):
    parent_folder: Optional[Folder]


@runtime_checkable
class DriveChild(Protocol):
    parent_drive: Optional[VirtualDrive]


@runtime_checkable
class VirtualDrive(FolderCollection, FileCollection, ArchiveWalkable, Protocol):
    ...


@runtime_checkable
class Folder(FolderCollection, FileCollection, FolderChild, DriveChild, ArchiveWalkable, Protocol):
    ...


@runtime_checkable
class File(FolderChild, DriveChild, Protocol):
    ...

    @property
    def full_path(self) -> PurePosixPath:
        raise NotImplementedError

    def read_data(self, data_stream, param):
        raise NotImplementedError


@runtime_checkable
class Archive(DriveCollection, ArchiveWalkable, Protocol):
    header: ArchiveHeader
    """Sparse represents whether data was loaded on creation."""
    _sparse: bool

    def walk(self) -> ArchiveWalk:
        raise NotImplementedError
        # return walk(self)

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ArchiveHeader, sparse: bool = True):
        raise NotImplementedError
        # version = header.version
        # with header.toc_ptr.stream_jump_to(stream) as handle:
        #     toc_ptr = ArchiveTableOfContentsPtrABC.unpack_version(handle, version)
        #     toc_headers = ArchiveTableOfContentsHeadersABC.unpack(handle, toc_ptr, version)
        #     toc = ArchiveTableOfContentsABC.create(toc_headers)
        #
        # toc.load_toc()
        # toc.build_tree()  # ensures walk is unique; avoiding dupes and speeding things up
        # if not sparse:
        #     with header.data_ptr.stream_jump_to(stream) as handle:
        #         toc.load_data(handle)

        # return cls(header, toc.drives, sparse)

    def pack(self, stream: BinaryIO) -> int:
        raise NotImplementedError


ArchiveWalk = Iterable[Tuple[Optional[VirtualDrive], Optional[Folder], Iterable[Folder], Iterable[File]]]
ArchivePath = PurePath
