from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import List, Optional, Union, Tuple, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from .file import File
    from .folder import Folder
    from .vdrive import VirtualDrive


@dataclass
class DriveCollection:
    drives: List[VirtualDrive]


@dataclass
class FolderCollection:
    sub_folders: List[Folder]


@dataclass
class FileCollection:
    files: List[File]


@dataclass
class FolderChild:
    _parent: Optional[Folder]


@dataclass
class DriveChild:
    _drive: Optional[VirtualDrive]


ArchivePath = PurePath

if TYPE_CHECKING:
    ArchiveWalk = Iterable[Tuple[Optional[VirtualDrive], Optional[Folder], Iterable[Folder], Iterable[File]]]
else:
    ArchiveWalk = Iterable[Tuple['VirtualDrive', Optional['Folder'], Iterable['Folder'], Iterable['File']]]


def walk(collection: Union[DriveCollection, FolderCollection, FileCollection]) -> ArchiveWalk:
    from .folder import Folder
    from .vdrive import VirtualDrive

    drives = collection.drives if isinstance(collection, DriveCollection) else []
    sub_folders = collection.sub_folders if isinstance(collection, FolderCollection) else []
    files = collection.files if isinstance(collection, FileCollection) and not isinstance(collection,VirtualDrive) else []

    root_drive = collection if isinstance(collection, VirtualDrive) else None
    root_folder = collection if isinstance(collection, Folder) else None

    # TODO optimize
    #   logically, we can only walk folder OR drive
    if root_drive is None and root_folder is None and len(sub_folders) == 0 and len(files) == 0:
        # I don't think we need to return ANYTHING if we won't be iterating over it
        pass
        # if len(drives) == 0: # We will only yield this item, so we return this to always iterate over something
        #     yield root_drive, root_folder, sub_folders, files
    else:
        yield root_drive, root_folder, sub_folders, files # at least one of these isn't None/Empty so we yield iti

    for drive in drives:
        for d, f, folds, files, in walk(drive):
            d = d or drive or root_drive
            f = f or root_folder
            yield d, f, folds, files

    for folder in sub_folders:
        for d, f, folds, files in walk(folder):
            d = d or root_drive
            f = f or folder or root_folder
            yield d, f, folds, files
