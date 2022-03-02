import os
from os.path import splitext, dirname, basename
from pathlib import Path
from typing import Iterable

from serialization_tools.walkutil import BlackList, WhiteList, filter_by_path, filter_by_file_extension, collapse_walk_on_files

from relic.config import DowIIIGame, DowIIGame, DowGame, filter_latest_dow_game, get_dow_root_directories

from relic.sga.archive import ArchiveMagicWord, Archive


def __safe_makedirs(path: str, use_dirname: bool = True):
    if use_dirname:
        path = dirname(path)
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


# walk all archives in the given directory, custom whitelist, blacklist, and extensions will overwrite defaults
#   Defaults: .sga, No *-Med, *-Low archives
def walk_archive_paths(folder: os.PathLike, extensions: WhiteList = None, whitelist: WhiteList = None, blacklist: BlackList = None) -> Iterable[str]:
    # Default EXT and Blacklist
    extensions = extensions or "sga"  # Default to sga, it shouldn't ever be different, so I could probably
    blacklist = blacklist or ["-Low", "-Med"]  # Typically, beside -High files, we only want the biggest
    # Flattened long call to make it easy to read
    walk = os.walk(folder)
    walk = filter_by_path(walk, whitelist=whitelist, blacklist=blacklist, prune=True)
    walk = filter_by_file_extension(walk, whitelist=extensions)
    walk = ArchiveMagicWord.walk(walk)
    return collapse_walk_on_files(walk)


def dump_archive(input_folder: os.PathLike, output_folder: os.PathLike, overwrite: bool = False, update: bool = False):
    if overwrite and update:
        raise NotImplementedError("Both write options selected, would you like to overwrite files? Or only update non-matching files?")

    output_folder_path = Path(output_folder)
    for input_file_path in walk_archive_paths(input_folder):
        with open(input_file_path, "rb") as in_handle:
            archive = Archive.unpack(in_handle)
            archive_name = splitext(basename(input_file_path))[0]
            with archive.header.data_ptr.stream_jump_to(in_handle) as data_stream:
                print(f"\tDumping '{archive_name}'")
                for _, _, _, files in archive.walk():
                    for file in files:
                        relative_file_path = file.full_path

                        if ':' in relative_file_path.parts[0]:
                            relative_file_path = str(relative_file_path).replace(":", "")

                        output_file_path = output_folder_path / archive_name / relative_file_path

                        msg = f"Writing '{relative_file_path}'"
                        skip = False
                        if output_file_path.exists():
                            if update:
                                if output_file_path.stat().st_size == file.header.decompressed_size:
                                    msg = f"Skipping (Up to date - Decompressed Size Match)"
                                    skip = True
                                elif output_file_path.stat().st_size == file.header.compressed_size:
                                    msg = f"Skipping (Up to date - Compressed Size Match)"
                                    skip = True
                                else:
                                    msg = f"Updating"
                            elif not overwrite:
                                msg = f"Skipping (Exists)"
                                skip = True

                        print(f"\t\t{msg} '{relative_file_path}'")
                        if skip:
                            continue
                        __safe_makedirs(str(output_file_path))
                        with open(output_file_path, "wb") as out_handle:
                            data = file.read_data(data_stream, True)
                            out_handle.write(data)
                        print(f"\t\t\tWrote to '{output_file_path}'")

    # write_binary(walk, output_folder, decompress, write_ext)


if __name__ == "__main__":
    # A compromise between an automatic location and NOT the local directory
    #   PyCharm will hang trying to reload the files (just to update the hierarchy, not update references)
    #       To avoid that, we DO NOT use a local directory, but an external directory
    #           TODO add a persistent_data path to archive tools
    Root = Path(r"~\Appdata\Local\ModernMAK\ArchiveTools\Relic-SGA").expanduser()
    dump_type = "SGA_DUMP"
    path_lookup = {
        DowIIIGame: Root / r"DOW_III",
        DowIIGame: Root / r"DOW_II",
        DowGame: Root / r"DOW_I"
    }
    series = DowGame
    out_path = path_lookup[series] / dump_type
    r = filter_latest_dow_game(get_dow_root_directories(), series=series)
    if r:
        game, in_path = r
    else:
        raise FileNotFoundError("Couldn't find any suitable DOW games!")
    print(f"Dumping game '{game}' from '{in_path}' to '{out_path}'\n")
    dump_archive(in_path, out_path, update=True)
    print(f"\nDumped game '{game}' from '{in_path}' to '{out_path}'")
    # dump_all_sga(root, blacklist=[r"-Low", "-Med"],
    #              out_dir=r"D:/Dumps/DOW I/sga", verbose=True)
