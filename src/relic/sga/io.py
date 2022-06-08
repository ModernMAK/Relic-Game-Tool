from __future__ import annotations

from typing import Dict, Type, BinaryIO, Union, Any

from relic.common import VersionLike
from relic.sga.vX import APIvX
from relic.sga.abc_ import DriveCollection, FolderCollectionABC, FileCollectionABC, ArchiveABC
from relic.sga.common import ArchiveMagicWord, ArchiveVersion
from relic.sga.protocols import ArchiveHeader, Archive, ArchiveWalk, VirtualDrive, Folder


def unpack_archive_header(versions: Dict[VersionLike, Type[ArchiveHeader]], stream: BinaryIO, read_magic: bool = True) -> ArchiveHeader:
    if read_magic:
        ArchiveMagicWord.assert_magic_word(stream, True)

    version = ArchiveVersion.unpack_version(stream)
    try:
        header_class = versions[version]
    except KeyError as e:
        raise NotImplementedError(version) from e

    return header_class.unpack(stream)


def pack_archive_header(header: ArchiveHeader, stream: BinaryIO, write_magic: bool = True) -> int:
    written = 0

    if write_magic:
        written += ArchiveMagicWord.write_magic_word(stream)

    written += ArchiveVersion.pack_version(stream, header.version)
    written += header.pack(stream)
    return written


def pack_archive(archive: Archive, stream: BinaryIO, write_magic: bool = True) -> int:
    raise NotImplementedError


def unpack_archive(stream: BinaryIO, sparse: bool = True, versions: Dict[VersionLike, APIvX] = None, *, validate: bool = True) -> ArchiveABC:
    ArchiveMagicWord.assert_magic_word(stream, True)
    version = ArchiveVersion.unpack_version(stream)
    api = versions[version]
    header = api.ArchiveHeader.unpack(stream)
    if validate:
        header.validate_checksums(stream)
    return api.Archive.unpack(stream, header, sparse)  # Defer to subclass (ensures packing works as expected)


def walk(collection: Union[DriveCollection, FolderCollectionABC, FileCollectionABC]) -> ArchiveWalk:
    drives = collection.drives if isinstance(collection, DriveCollection) else []
    sub_folders = collection.sub_folders if isinstance(collection, FolderCollectionABC) else []
    files = collection.files if isinstance(collection, FileCollectionABC) and not isinstance(collection, VirtualDrive) else []

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
        yield root_drive, root_folder, sub_folders, files  # at least one of these isn't None/Empty so we yield iti

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
