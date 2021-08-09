from typing import BinaryIO, Tuple, List, Any, Dict

from relic.sga import Archive, AbstractDirectory, Folder, File, VirtualDriveHeader, FolderHeader

# Cycles aren't supported (and will crash)
# Multiple parents will be copied

# Flattened is edited IN PLACE
from relic.sga.shared import ArchiveRange
from relic.shared import Version


def flatten_folders(collection: AbstractDirectory, flattened: List[Folder]) -> Tuple[int, int]:
    start = len(flattened)
    flattened.extend(collection.folders)
    stop = len(flattened)
    return start, stop


def flatten_files(collection: AbstractDirectory, flattened: List[File]) -> Tuple[int, int]:
    start = len(flattened)
    flattened.extend(collection.files)
    stop = len(flattened)
    return start, stop


def write_table_of_contents_data_to_stream(stream: BinaryIO, archive: Archive, recalculate_totals: bool = True) -> int:
    drives = []
    folders = []
    files = []

    vdrive_offset = stream.tell()

    fold_offset = stream.tell()


def write_virtual_drives(stream: BinaryIO, archive: Archive, version: Version, recalculate: bool = True) -> int:
    running_folder = 0
    running_file = 0
    written = 0
    for drive in archive.drives:
        folder_count = drive.folder_count(recalculate)
        file_count = drive.file_count(recalculate)

        folder = ArchiveRange(running_folder, running_folder + folder_count)
        files = ArchiveRange(running_file, running_file + file_count)

        running_folder += folder_count
        running_file += file_count

        header = VirtualDriveHeader(drive.path, drive.name, folder, files, folder.start)
        written += header.pack(stream, version)
    return written


# Offset, Count (Items), Size (Bytes)
def write_folders(stream: BinaryIO, archive: Archive, version: Version, name_table:Dict[any,int], recalculate: bool = False) -> Tuple[
    int, int, int]:
    running_folder = 0
    running_file = 0
    written = 0

    offset = stream.tell()
    for drive in archive.drives:
        folder_count = drive.folder_count(recalculate)
        file_count = drive.file_count(recalculate)

        folder = ArchiveRange(running_folder, running_folder + folder_count)
        files = ArchiveRange(running_file, running_file + file_count)

        running_folder += folder_count
        running_file += file_count

        header = VirtualDriveHeader(drive.path, drive.name, folder, files, folder.start)
        written += header.pack(stream, version)

    return offset, len(archive.drives), written


def write_names(stream: BinaryIO, archive: Archive) -> Tuple[int, int, int, Dict[Any, int]]:
    offset = stream.tell()
    running_total = 0
    lookup = {}
    written = 0

    def write_null_terminated(name: str) -> int:
        sub_written = stream.write(name)
        if name[-1] != "\0":
            sub_written += stream.write("\0")
        return sub_written

    # This will not re-use repeated names; we could change it but I wont since my brain is overoptimizing this
    #   By allowing names to repeat, we avoid perform hash checks in a dictionary (or equality comparisons in a list)
    for drive in archive.drives:
        for _, folders, files in drive.walk():
            running_total += len(folders) + len(files)
            for f in folders:
                lookup[f] = stream.tell()
                written += write_null_terminated(f.name)
            for f in files:
                lookup[f] = stream.tell()
                written += write_null_terminated(f.name)

    return offset, running_total, written, lookup


# Offset, Count (Items), Size (Bytes)
def write_folders(stream: BinaryIO, archive: Archive, version: Version, name_lookup:Dict[Any,int], recalculate: bool = False) -> Tuple[
    int, int, int]:
    running_folder = 0
    running_file = 0
    written = 0

    offset = stream.tell()
    for drive in archive.drives:
        for _, folders, _ in drive.walk():
            for folder in folders:
                folder_count = folder.folder_count(recalculate)
                file_count = folder.file_count(recalculate)

                folder_range = ArchiveRange(running_folder, running_folder + folder_count)
                file_range = ArchiveRange(running_file, running_file + file_count)

                running_folder += folder_count
                running_file += file_count

                name_offset = name_lookup[folder]

                header = FolderHeader(name_offset, folder_range, file_range)
                written += header.pack(stream, version)

    return offset, len(archive.drives), written

# Offset, Count (Items), Size (Bytes)
def write_folders(stream: BinaryIO, archive: Archive, version: Version, name_lookup:Dict[Any,int], recalculate: bool = False) -> Tuple[
    int, int, int]:
    running_folder = 0
    running_file = 0
    written = 0

    offset = stream.tell()
    for drive in archive.drives:
        for _, folders, _ in drive.walk():
            for folder in folders:
                folder_count = folder.folder_count(recalculate)
                file_count = folder.file_count(recalculate)

                folder_range = ArchiveRange(running_folder, running_folder + folder_count)
                file_range = ArchiveRange(running_file, running_file + file_count)

                running_folder += folder_count
                running_file += file_count

                name_offset = name_lookup[folder]

                header = FolderHeader(name_offset, folder_range, file_range)
                written += header.pack(stream, version)

    return offset, len(archive.drives), written

# Offset, Count (Items), Size (Bytes)
def write_file_data(stream: BinaryIO, archive: Archive, version: Version) -> Tuple[int, int, int, Dict[File,int]]:
    written = 0

    offset = stream.tell()
    for drive in archive.drives:
        for _, _, files in drive.walk():
            for file in files:
                file.head

                folder_count = folder.folder_count(recalculate)
                file_count = folder.file_count(recalculate)

                folder_range = ArchiveRange(running_folder, running_folder + folder_count)
                file_range = ArchiveRange(running_file, running_file + file_count)

                running_folder += folder_count
                running_file += file_count

                name_offset = name_lookup[folder]

                header = FolderHeader(name_offset, folder_range, file_range)
                written += header.pack(stream, version)

    return offset, len(archive.drives), written


@classmethod
def create(cls, stream: BinaryIO, archive_info: ArchiveInfo) -> 'SparseArchive':
    version = archive_info.header.version
    desc_info = archive_info.table_of_contents.descriptions_info
    stream.seek(desc_info.offset_absolute, 0)
    descriptions = [VirtualDriveHeader.unpack(stream, version) for _ in range(desc_info.count)]

    fold_info = archive_info.table_of_contents.folders_info
    stream.seek(fold_info.offset_absolute, 0)
    folders = [FolderHeader.unpack(stream, version) for _ in range(fold_info.count)]

    file_info = archive_info.table_of_contents.files_info
    stream.seek(file_info.offset_absolute, 0)
    files = [FileHeader.unpack(stream, version) for _ in range(file_info.count)]

    return SparseArchive(archive_info, descriptions, files, folders)
