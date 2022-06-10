from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Iterator, BinaryIO, Union

from serialization_tools.magic import MagicWordIO
from serialization_tools.structx import Struct

from relic.common import VersionEnum, Version, VersionLike
from relic.sga.protocols import ArchiveWalk, FileCollection, FolderCollection, DriveCollection, Folder, VirtualDrive

ArchiveVersionLayout = Struct("< 2H")


class FileVerificationType(Enum):
    None_ = 0  # unknown real values, assuming incremental
    CRC = 1  # unknown real values, assuming incremental
    CRCBlocks = 2  # unknown real values, assuming incremental
    MD5Blocks = 3  # unknown real values, assuming incremental
    SHA1Blocks = 4  # unknown real values, assuming incremental


class FileStorageType(Enum):
    Store = 0
    StreamCompress = 1  # 16
    BufferCompress = 2  # 32


class ArchiveVersion(VersionEnum):
    Unsupported = None
    v2 = Version(2)
    Dow = v2
    v5 = Version(5)
    Dow2 = v5
    v7 = Version(7)
    CoH2 = v7
    v9 = Version(9)
    Dow3 = v9

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


ArchiveMagicWord = MagicWordIO(Struct("< 8s"), "_ARCHIVE".encode("ascii"))


def walk(collection: Union[DriveCollection, FolderCollection, FileCollection]) -> ArchiveWalk:
    raise TypeError("Use walk() function on collection!")
    # drives = collection.drives if isinstance(collection, DriveCollection) else []
    # sub_folders = collection.sub_folders if isinstance(collection, FolderCollection) else []
    # files = collection.files if isinstance(collection, FileCollection) and not isinstance(collection, VirtualDrive) else []
    #
    # root_drive = collection if isinstance(collection, VirtualDrive) else None
    # root_folder = collection if isinstance(collection, Folder) else None
    #
    # # TODO optimize
    # #   logically, we can only walk folder OR drive
    # if root_drive is None and root_folder is None and len(sub_folders) == 0 and len(files) == 0:
    #     # I don't think we need to return ANYTHING if we won't be iterating over it
    #     pass
    #     # if len(drives) == 0: # We will only yield this item, so we return this to always iterate over something
    #     #     yield root_drive, root_folder, sub_folders, files
    # else:
    #     yield root_drive, root_folder, sub_folders, files  # at least one of these isn't None/Empty so we yield iti
    #
    # for drive in drives:
    #     for d, f, folds, files, in walk(drive):
    #         d = d or drive or root_drive
    #         f = f or root_folder
    #         yield d, f, folds, files
    #
    # for folder in sub_folders:
    #     for d, f, folds, files in walk(folder):
    #         d = d or root_drive
    #         f = f or folder or root_folder
    #         yield d, f, folds, files
