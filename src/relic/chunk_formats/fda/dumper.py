# Stolen from https://scratchpad.fandom.com/wiki/Relic_Chunky_files
import os
from os.path import join, splitext
from typing import List

from relic.chunk_formats.fda.fda_chunky import FdaChunky
from relic.chunky.relic_chunky import RelicChunky
from relic.shared import walk_ext


def shared_dump(file: str, name: str, out_dir: str = None):
    out_dir = out_dir or "gen/fda/shared_dump"
    with open(file, "rb") as handle:
        try:
            chunky = RelicChunky.unpack(handle)
        except ValueError as e:
            print(e)
            pass

        fda = FdaChunky.create(chunky)
        shared_path = join(out_dir, name)
        dir_path = os.path.dirname(shared_path)
        try:
            os.makedirs(dir_path)
        except FileExistsError:
            pass
        with open(shared_path, "wb") as writer:
            Converter.Fda2Aiffr(fda, writer, use_fixed=True)


def dump_all_fda(folder: str, out_dir: str = None, blacklist: List[str] = None, verbose: bool = False):
    blacklist = blacklist or []
    for root, file in walk_ext(folder, ".fda"):
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
        name = full.lstrip(folder).lstrip("\\").lstrip("/")
        f, _ = splitext(name)

        shared_dump(full, f + ".aifc", out_dir)


if __name__ == "__main__":
    dump_all_fda(r"D:/Dumps/DOW I/sga",
                 out_dir=r"D:/Dumps/DOW I/fda", verbose=True)