import os
from typing import Iterable, Tuple

from relic.sga.archive import Archive
from relic.sga.file_header import FileCompressionFlag
from relic.sga.magic import ARCHIVE_MAGIC_WALKER
from relic.shared import filter_walk_by_extension, collapse_walk_on_files
from relic.config import get_latest_dow_game


def scan_compression_flag(search_dir: str) -> Iterable[Tuple[str, str, FileCompressionFlag]]:
    for archive_path in collapse_walk_on_files(
            ARCHIVE_MAGIC_WALKER.walk(filter_walk_by_extension(os.walk(search_dir), whitelist="sga"))):
        with open(archive_path, "rb") as handle:
            archive = Archive.unpack(handle)
            for root, _, files in archive.walk():
                for file in files:
                    if file.header.compressed:
                        yield archive_path, file.name, file.header.compression_flag


if __name__ == "__main__":
    print("Scanning archive compression flags")
    counter = 0
    for archive, file, flag in scan_compression_flag(get_latest_dow_game()[1]):
        print(archive, "\t", file, "\t", flag)
        if flag == FileCompressionFlag.Compressed16:
            pass
        elif flag == FileCompressionFlag.Compressed32:
            pass
        elif flag == FileCompressionFlag.Decompressed:
            raise NotImplemented()
