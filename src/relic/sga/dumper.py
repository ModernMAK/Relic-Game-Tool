import os
from collections import Iterable
from os.path import join, splitext
from typing import Tuple, Optional

from relic.sga.archive import Archive
from relic.sga.file import File
from relic.sga.file_collection import ArchiveWalkResult
from relic.sga.magic import ARCHIVE_MAGIC_WALKER
from relic.shared import filter_walk_by_extension, KW_LIST, fix_extension_list, filter_path_by_extension, \
    filter_walk_by_keyword, collapse_walk_on_files


def write_binary(walk: Iterable[Tuple[str, File]], out_directory: str, decompress: bool = True,
                 forced_ext: Optional[str] = None):
    for directory, file in walk:
        full_directory = join(out_directory, directory, file.name)
        if forced_ext:
            full_directory = splitext(full_directory)[0] + forced_ext
        with file.open_readonly_stream(decompress) as read_handle:
            with open(full_directory, "wb") as write_handle:
                write_handle.write(read_handle.read())


def collapse_walk_in_files(walk: Iterable[ArchiveWalkResult]) -> Iterable[Tuple[str, File]]:
    for root, _, files in walk:
        for file in files:
            yield root, file


def filter_archive_files_by_extension(walk: Iterable[ArchiveWalkResult], whitelist: KW_LIST = None, blacklist: KW_LIST = None) -> Iterable[ArchiveWalkResult]:
    whitelist = fix_extension_list(whitelist)
    blacklist = fix_extension_list(blacklist)
    for root, folders, files in walk:
        filtered_files = (filter_path_by_extension(file.name, whitelist, blacklist) for file in files)
        yield root, folders, filtered_files


def walk_archive_files(walk: Iterable[Archive]) -> Iterable[ArchiveWalkResult]:
    for archive in walk:
        for inner_walk in archive.walk():
            yield inner_walk


def walk_archives(walk: Iterable[str]) -> Iterable[Archive]:
    for file_path in walk:
        with open(file_path, "rb") as handle:
            yield Archive.unpack(handle)


# walk all archives in the given directory, custom whitelist, blacklist, and exts will overwrite defaults
#   Defaults: .sga, No *-Med, *-Low archives
def walk_archive_paths(folder: str, exts: KW_LIST = None, whitelist: KW_LIST = None, blacklist: KW_LIST = None) -> \
        Iterable[str]:
    # Default EXT and Blacklist
    exts = exts or ".sga"
    blacklist = blacklist or ["-Low", "-Med"]
    # Flattened long call to make it easy to read
    walk = os.walk(folder)
    walk = filter_walk_by_extension(walk, whitelist=exts)
    walk = filter_walk_by_keyword(walk, whitelist=whitelist, blacklist=blacklist)
    walk = ARCHIVE_MAGIC_WALKER.walk(walk)
    return collapse_walk_on_files(walk)


def dump_archive(input_folder: str, output_folder: str, decompress: bool = True, ext_whitelist: KW_LIST = None, ext_blacklist: KW_LIST = None,        write_ext: Optional[str] = None):
    walk = walk_archive_paths(input_folder)
    walk = walk_archives(walk)
    walk = walk_archive_files(walk)
    walk = filter_archive_files_by_extension(walk, ext_whitelist, ext_blacklist)
    walk = collapse_walk_in_files(walk)
    write_binary(walk, output_folder, decompress, write_ext)


if __name__ == "__main__":
    in_folder = r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Soulstorm"
    # in_folder = r"D:\Steam\steamapps\common\Dawn of War Soulstorm"
    out_folder = r"D:/Dumps/DOW I/sga"

    dump_archive(in_folder, out_folder)
    # dump_all_sga(root, blacklist=[r"-Low", "-Med"],
    #              out_dir=r"D:/Dumps/DOW I/sga", verbose=True)
