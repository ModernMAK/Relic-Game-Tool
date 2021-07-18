import json
import os
from os.path import join
from typing import List, Iterable, Tuple

from relic.sga.flat_archive import FlatArchive
from relic.sga.full_archive import FullArchive
from relic.sga.shared import walk_sga_paths
from relic.shared import EnhancedJSONEncoder, walk_ext


def walk_sga_archive(folder: str, blacklist: List[str] = None) -> Iterable[Tuple[str, 'FlatArchive']]:
    for root, file in walk_sga_paths(folder, blacklist):
        full = join(root, file)
        with open(full, "rb") as handle:
            archive = FullArchive.unpack(handle)
            yield full, archive

def dump_all_sga(folder: str, out_dir: str = None, blacklist: List[str] = None, verbose: bool = False):
    blacklist = blacklist or []
    for root, file in walk_ext(folder, ".sga"):
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
        archive = FlatArchive.unpack(handle)
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


def shared_dump(file: str, out_dir: str = None, verbose: bool = False):
    out_dir = out_dir or "gen/sga/shared_dump"
    with open(file, "rb") as handle:
        archive = FlatArchive.unpack(handle)
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


def run():
    root = r"G:\Clients\Steam\Launcher\steamapps\common"
    game = r"Dawn of War Soulstorm\W40k"
    files = [
        r"Locale\English\W40kDataKeys.sga",
        r"Locale\English\W40kDataLoc.sga",
        r"Locale\English\W40kData-Sound-Speech.sga",

        "W40kData-Sound-Low.sga",
        "W40kData-Sound-Med.sga",
        "W40kData-Sound-Full.sga",

        "W40kData-Whm-Low.sga",
        "W40kData-Whm-Medium.sga",
        "W40kData-Whm-High.sga",

        "W40kData.sga",

        "W40kData-SharedTextures-Full.sga",
    ]
    root = "gen/sga/"
    shared_dump = root + "shared_dump"
    single_dump = root + "dump"
    meta_dump = root + "meta"

    for i, file in enumerate(files):
        full = join(root, game, file)
        print(full)
        print("\tUnpacking...")
        with open(full, "rb") as handle:
            # archive = SGArchive.unpack(handle)
            archive = FlatArchive.unpack(handle)
            # print("\t", archive)
            meta = json.dumps(archive, indent=4, cls=EnhancedJSONEncoder)
            print("\t\t", meta)

            print("\tWriting Assets...")
            for f in archive.files:
                shared_path = join(shared_dump, f.name)
                dir_path = os.path.dirname(shared_path)
                try:
                    os.makedirs(dir_path)
                except FileExistsError:
                    pass
                with open(shared_path, "wb") as writer:
                    writer.write(f.data)

                own_path = join(single_dump, file, f.name)
                dir_path = os.path.dirname(own_path)
                try:
                    os.makedirs(dir_path)
                except FileExistsError:
                    pass
                with open(own_path, "wb") as writer:
                    writer.write(f.data)

            print("\tWriting Meta...")
            meta_path = join(meta_dump, file + ".json")
            dir_path = os.path.dirname(meta_path)
            try:
                os.makedirs(dir_path)
            except FileExistsError:
                pass
            with open(meta_path, "w") as writer:
                writer.write(meta)
if __name__ == "__main__":
    # root = r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Soulstorm"
    root = r"D:\Steam\steamapps\common\Dawn of War Soulstorm"

    dump_all_sga(root, blacklist=[r"-Low", "-Med"],
                 out_dir=r"D:/Dumps/DOW I/sga", verbose=True)
