import os
from os.path import join, splitext, dirname
from typing import Tuple, Optional, Iterable

from relic.sga.archive import Archive
from relic.sga.file import File
from relic.sga.file_collection import ArchiveWalkResult
from relic.sga.shared import ARCHIVE_MAGIC_WALKER
from relic.shared import filter_walk_by_extension, KW_LIST, fix_extension_list, filter_path_by_extension, \
    filter_walk_by_keyword, collapse_walk_on_files


def __safe_join(*args: Optional[str]):
    args = [a for a in args if a is not None]
    return join(*args)


def __safe_makedirs(path: str, use_dirname: bool = True):
    if use_dirname:
        path = dirname(path)
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


def __spinner_generator(symbols: Iterable[str]) -> Iterable[str]:
    while True:
        for symbol in symbols:
            yield symbol


def __get_bar_spinner() -> Iterable[str]:
    return __spinner_generator("|\\-/")


def __get_ellipsis_spinner() -> Iterable[str]:
    return __spinner_generator([".", "..", "...", "....", "....."])


def write_binary(walk: Iterable[Tuple[str, File]], out_directory: str, decompress: bool = True,
                 forced_ext: Optional[str] = None):
    spinner = __get_bar_spinner()
    for directory, file in walk:
        write_file_as_binary(directory, file, out_directory, decompress, forced_ext)
        print(f"\r\t({next(spinner)}) Writing Binary Chunks, please wait.", end="")


def write_file_as_binary(directory: str, file: File, out_directory: str, decompress: bool = True,
                         forced_ext: Optional[str] = None):
    full_directory = __safe_join(out_directory, directory, file.name)
    __safe_makedirs(full_directory)
    if forced_ext:
        full_directory = splitext(full_directory)[0] + forced_ext
    with file.open_readonly_stream(decompress) as read_handle:
        with open(full_directory, "wb") as write_handle:
            write_handle.write(read_handle.read())
            # print(f"\r\t({next(spinner)}) Writing Binary Chunks, please wait.", end="")


def collapse_walk_in_files(walk: Iterable[ArchiveWalkResult]) -> Iterable[Tuple[str, File]]:
    for root, _, files in walk:
        for file in files:
            yield root, file


def filter_archive_files_by_extension(walk: Iterable[ArchiveWalkResult], whitelist: KW_LIST = None,
                                      blacklist: KW_LIST = None) -> Iterable[ArchiveWalkResult]:
    whitelist = fix_extension_list(whitelist)
    blacklist = fix_extension_list(blacklist)
    for root, folders, files in walk:
        filtered_files: Iterable[File] = \
            (file for file in files if filter_path_by_extension(file.material_name, whitelist, blacklist))
        yield root, folders, filtered_files


def walk_archive_files(walk: Iterable[Archive]) -> Iterable[ArchiveWalkResult]:
    for archive in walk:
        for inner_walk in archive.walk():
            yield inner_walk


def walk_archives(walk: Iterable[str]) -> Iterable[Archive]:
    for file_path in walk:
        with open(file_path, "rb") as handle:
            # print(f"\nUnpacking Archive =>\t{file_path}")
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


def dump_archive(input_folder: str, output_folder: str, decompress: bool = True, ext_whitelist: KW_LIST = None,
                 ext_blacklist: KW_LIST = None, write_ext: Optional[str] = None):
    walk = walk_archive_paths(input_folder)
    walk = walk_archives(walk)
    walk = walk_archive_files(walk)
    walk = filter_archive_files_by_extension(walk, ext_whitelist, ext_blacklist)
    walk = collapse_walk_in_files(walk)
    write_binary(walk, output_folder, decompress, write_ext)


if __name__ == "__main__":
    # in_folder = r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Soulstorm"
    in_folder = r"D:\Steam\steamapps\common\Dawn of War Soulstorm"
    out_folder = r"D:/Dumps/DOW I/sga"

    dump_archive(in_folder, out_folder)
    # dump_all_sga(root, blacklist=[r"-Low", "-Med"],
    #              out_dir=r"D:/Dumps/DOW I/sga", verbose=True)
