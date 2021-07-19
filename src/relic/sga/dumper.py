import os
from os.path import join
from typing import List

from relic.sga.archive import Archive
from relic.shared import filter_walk_by_extension


def dump_all_sga(folder: str, out_dir: str = None, blacklist: List[str] = None, verbose: bool = False):
    blacklist = blacklist or []
    for root, _, files in filter_walk_by_extension(os.walk(folder), whitelist=".sga"):
        for file in files:
            full = join(root, file)

            skip = False
            for word in blacklist:
                if word in full:
                    skip = True
                    break

            if skip:
                continue
            if verbose:
                print(full)
            shared_dump(full, out_dir, verbose)


def shared_dump(file: str, out_dir: str = None, verbose: bool = False):
    out_dir = out_dir or "gen/sga/shared_dump"
    with open(file, "rb") as handle:
        archive = Archive.unpack(handle)
        for f in archive.files:
            shared_path = join(out_dir, f.name)
            dir_path = os.path.dirname(shared_path)
            try:
                os.makedirs(dir_path)
            except FileExistsError:
                pass
            if verbose:
                print("\t", shared_path)
            with open(shared_path, "wb") as writer:
                writer.write(f.data)


if __name__ == "__main__":
    root = r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Soulstorm"
    # root = r"D:\Steam\steamapps\common\Dawn of War Soulstorm"

    dump_all_sga(root, blacklist=[r"-Low", "-Med"],
                 out_dir=r"D:/Dumps/DOW I/sga", verbose=True)
