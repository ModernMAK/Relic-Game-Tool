import os
from typing import Iterable, Tuple

from relic.sga.archive import Archive
from relic.sga.file_header import FileCompressionFlag
from relic.sga.magic import ARCHIVE_MAGIC_WALKER
from relic.shared import filter_walk_by_extension, collapse_walk_on_files

root = r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Soulstorm"


# root = r"D:\Steam\steamapps\common\Dawn of War Soulstorm"

def scan_compression_flag(search_dir: str) -> Iterable[Tuple[str, str, FileCompressionFlag]]:
    for archive_path in collapse_walk_on_files(
            ARCHIVE_MAGIC_WALKER.walk(filter_walk_by_extension(os.walk(search_dir), whitelist="sga"))):
        with open(archive_path, "rb") as handle:
            archive = Archive.unpack(handle)
            for file in archive.walk_files():
                if file.header.compressed:
                    yield archive_path, file.name, file.header.compression_flag


if __name__ == "__main__":
    print("Scanning archive compression flags")
    counter = 0
    for archive, file, flag in scan_compression_flag(root):
        print(archive, "\t", file, "\t", flag)
        if flag == FileCompressionFlag.Compressed16:
            pass
        elif flag == FileCompressionFlag.Compressed32:
            pass
        elif flag == FileCompressionFlag.Decompressed:
            raise NotImplemented()
