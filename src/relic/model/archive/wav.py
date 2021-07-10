import os
import shutil
import tempfile
from os.path import splitext, join, dirname, basename, exists
from time import sleep
from typing import List, Tuple


def walk_ext(folder: str, ext: str) -> Tuple[str, str]:
    ext = ext.lower()
    for root, _, files in os.walk(folder):
        for file in files:
            _, x = splitext(file)
            if x.lower() != ext:
                continue
            yield root, file


def shared_dump(file: str, name: str, out_dir: str = None):
    out_dir = out_dir or "gen/fda/shared_dump"
    full = join(out_dir, name)
    path = "../../../dll/dec.exe"
    path = os.path.abspath(path)
    try:
        os.makedirs(dirname(full))
    except FileExistsError:
        pass

    #TODO wrap all subprocess calls by copying the source to a temp, and the dest to a temp
    # then copy the temp-dest to the actual location to avoid arbitrary path errors / read errors
    import subprocess

    def create_temporary_copy(path) -> str:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, basename(path))
        shutil.copy2(path, temp_path)
        return temp_path

    temp_src = create_temporary_copy(file)
    temp_dst = temp_src + ".wav"
    subprocess.call([path, f"{temp_src}", f"{temp_dst}"])
    if exists(temp_dst):
        shutil.copy2(temp_dst,full)


def dump_all_aifc(folder: str, out_dir: str = None, blacklist: List[str] = None, verbose: bool = False):
    blacklist = blacklist or []
    for root, file in walk_ext(folder, ".aifc"):
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
        shared_dump(full, f + ".wav", out_dir)


if __name__ == "__main__":
    dump_all_aifc(r"D:/Dumps/DOW I/fda",
                  out_dir=r"D:/Dumps/DOW I/wav", verbose=True)
