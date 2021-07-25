import os
from os.path import splitext
from typing import Iterable

from relic.chunky.magic import RELIC_CHUNKY_MAGIC
from relic.sga.archive import Archive
from relic.sga.magic import ARCHIVE_MAGIC_WALKER
from relic.shared import filter_walk_by_extension, collapse_walk_on_files, KW_LIST, fix_extension_list, \
    filter_walk_by_keyword
from relic.config import get_latest_dow_game

# These are duplicates of -High or -Full
# We skip them to avoid repeating ourselves.
blacklist = [r"-Low", "-Med"]

known_supported = ["rsh", "fda", "whm", "wtp", "rtx"]


# Unimplemented files ([???] means no longer unimplemented)
# RGD, [RTX], WHE, EVENTS, TMP, SGB, SGM, RML

def scan_for_unsupported(search_dir: str, supported_extensions: KW_LIST = None, kw_blacklist: KW_LIST = None,
                         ignore_non_chunky: bool = True) -> Iterable[str]:
    supported_extensions = fix_extension_list(supported_extensions)
    ignored_extensions = []
    unsupported_extensions = []
    for archive_path in collapse_walk_on_files(
            ARCHIVE_MAGIC_WALKER.walk(
                filter_walk_by_keyword(
                    filter_walk_by_extension(os.walk(search_dir), whitelist="sga"), blacklist=kw_blacklist))):

        with open(archive_path, "rb") as handle:
            archive = Archive.unpack(handle)
            for root, _, files in archive.walk():
                for file in files:
                    _, x = splitext(file.name)
                    x = x.lower()

                    # Don't care, we already matched this ext (either as a supported ext or an unsupported ext)
                    if x in supported_extensions or x in unsupported_extensions:
                        continue
                    if ignore_non_chunky and x in ignored_extensions:
                        continue

                    with file.open_readonly_stream() as file_handle:
                        if RELIC_CHUNKY_MAGIC.check_magic_word(file_handle):
                            yield x
                            unsupported_extensions.append(x)
                        elif ignore_non_chunky:
                            ignored_extensions.append(x)


if __name__ == "__main__":
    print("Scanning for unsupported chunky .extensions")
    counter = 0
    for ext in scan_for_unsupported(get_latest_dow_game()[1], known_supported, blacklist):
        counter += 1
        print("\t", ext)

    print("\nTotal Unsupported: ", counter)
