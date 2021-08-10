from dataclasses import dataclass
from os.path import join
from typing import List, BinaryIO
from relic.sga.archive_header import ArchiveInfo
from relic.sga.file import File, FileHeader
from relic.sga.file_collection import AbstractDirectory, ArchiveWalkResult
from relic.sga.folder import Folder, FolderHeader
from relic.sga.virtual_drive import VirtualDriveHeader, VirtualDrive


@dataclass
class SparseArchive:
    info: ArchiveInfo
    drives: List[VirtualDriveHeader]
    files: List[FileHeader]
    folders: List[FolderHeader]

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'SparseArchive':
        info = ArchiveInfo.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo) -> 'SparseArchive':
        version = archive_info.header.version
        desc_info = archive_info.table_of_contents.drive_info
        stream.seek(desc_info.offset_absolute, 0)
        descriptions = [VirtualDriveHeader.unpack(stream, version) for _ in range(desc_info.count)]

        fold_info = archive_info.table_of_contents.folders_info
        stream.seek(fold_info.offset_absolute, 0)
        folders = [FolderHeader.unpack(stream, version) for _ in range(fold_info.count)]

        file_info = archive_info.table_of_contents.files_info
        stream.seek(file_info.offset_absolute, 0)
        files = [FileHeader.unpack(stream, version) for _ in range(file_info.count)]

        return SparseArchive(archive_info, descriptions, files, folders)


@dataclass
class Archive:
    info: ArchiveInfo
    drives: List[VirtualDrive]

    # A helper to know the total # of files without performing a full walk
    _total_files: int = 0

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'Archive':
        info = SparseArchive.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive: SparseArchive) -> 'Archive':
        info = archive.info
        name_lookup = info.table_of_contents.filenames_info.get_name_lookup(stream, use_absolute=False)
        folders = [Folder.create(f, name_lookup) for f in archive.folders]
        files = [File.create(stream, info, f, name_lookup) for f in archive.files]
        for f in folders:
            f.load_folders(folders)
            f.load_files(files)

        drives = [VirtualDrive.create(d) for d in archive.drives]
        for d in drives:
            d.load_folders(folders)
            d.load_files(files)

        total_files = len(files)

        return Archive(info, drives, total_files)

    @classmethod
    def repack(cls, stream: BinaryIO, write_magic: bool = True):
        raise NotImplementedError

    def walk(self, specify_drive: bool = False) -> ArchiveWalkResult:
        for drive in self.drives:
            for root, folders, files in drive.walk(specify_drive):
                yield root, folders, files

    def get_from_path(self, *parts: str):
        if len(parts) > 1:
            if parts[0][-1] == ":":  # If the first part is a drive
                full_path = parts[0] + join(*parts[1:])
            else:
                full_path = join(*parts)
        else:
            full_path = parts[0]
        drive_split = full_path.split(":", 1)

        if len(drive_split) > 1:
            drive_path, path_to_file = drive_split
            for drive in self.drives:
                if drive.path == drive_path:
                    return drive.get_from_path(path_to_file)
        else:
            path_to_file = drive_split[0]
            for drive in self.drives:
                result = drive.get_from_path(path_to_file)
                if result:
                    return result
