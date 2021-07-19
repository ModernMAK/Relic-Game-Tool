import os
from os.path import join, splitext
from typing import List, Iterable

from relic.sga.archive import Archive
from relic.sga.magic import ARCHIVE_MAGIC_WALKER
from relic.chunky.magic import RELIC_CHUNKY_MAGIC
from relic.shared import filter_walk_by_extension, collapse_walk_on_files, KW_LIST, fix_extension_list, \
    filter_walk_by_keyword

root = r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Soulstorm"
# root = r"D:\Steam\steamapps\common\Dawn of War Soulstorm"
blacklist = [r"-Low", "-Med"]

known_supported = ["rsh", "fda", "whm", "wtp"]


# Unimplimented files
# RGD, RTX, WHE, EVENTS, TMP, SGB, SGM, RML

def scan_for_unsupported(search_dir: str, supported_exts: KW_LIST = None, kw_blacklist: KW_LIST = None,
                         ignore_non_chunky: bool = True) -> Iterable[str]:
    supported_exts = fix_extension_list(supported_exts)
    ignored_exts = []
    unsupported_exts = []
    for archive_path in collapse_walk_on_files(
            ARCHIVE_MAGIC_WALKER.walk(
                filter_walk_by_keyword(
                    filter_walk_by_extension(os.walk(search_dir), whitelist="sga"), blacklist=kw_blacklist))):

        with open(archive_path, "rb") as handle:
            archive = Archive.unpack(handle)
            for file in archive.walk_files():
                _, ext = splitext(file.name)
                ext = ext.lower()

                # Dont care, we already matched this ext (either as a supported ext or an unsupported ext)
                if ext in supported_exts or ext in unsupported_exts:
                    continue
                if ignore_non_chunky and ext in ignored_exts:
                    continue

                with file.open_readonly_stream() as handle:
                    if RELIC_CHUNKY_MAGIC.check_magic_word(handle):
                        yield ext
                        unsupported_exts.append(ext)
                    elif ignore_non_chunky:
                        ignored_exts.append(ext)


if __name__ == "__main__":
    print("Scanning for unsupported chunky .extensions")
    counter = 0
    for ext in scan_for_unsupported(root, known_supported, blacklist):
        counter += 1
        print("\t", ext)

    print("\nTotal Unsupported: ", counter)
