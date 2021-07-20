import json
import os
import shutil
import struct
from dataclasses import dataclass
from os.path import join, splitext, basename, dirname
from typing import List

from relic.chunk_formats.whm.msgr_chunk import MsgrChunk
from relic.chunk_formats.whm.mslc_chunk import UnimplementedMslcBlockFormat
from relic.chunk_formats.whm.sshr_chunk import SshrChunk
from relic.chunk_formats.whm.whm_file import WhmChunky
from relic.chunk_formats.whm.writer import write_obj_mtl
from relic.chunky import RelicChunky
from relic.chunky.dumper import dump_all_chunky
from relic.shared import walk_ext, EnhancedJSONEncoder


def raw_dump():
    dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-chunky", [".whm"])


def print_meta(f: str):
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        whm = WhmChunky.create(chunky)
        meta = json.dumps(whm, indent=4, cls=EnhancedJSONEncoder)
        print(meta)


_BufferSize32 = 37
_BufferSize48 = 39


def dump_all_model(f: str, o: str, texture_root: str = None, texture_ext: str = None):
    for root, file in walk_ext(f, ".whm"):
        obj_name, _ = splitext(file)
        full_path = join(root, file)
        dump_path = join(root.replace(f, o, 1), obj_name, obj_name + ".obj")
        try:
            os.makedirs(dirname(dump_path))
        except FileExistsError:
            pass

        try:
            dump_model(full_path, dump_path, texture_root, texture_ext)
        except (NotImplementedError, struct.error, UnicodeDecodeError, Exception) as e:
            print("\t", e)
            try:
                os.remove(dump_path)
            except Exception:
                pass

            # To allow me to examine them closely without manually doing it
            full = join(root, file)
            dump = full.replace(f, o + "-funky", 1)
            try:
                os.makedirs(dump)
            except FileExistsError:
                pass
            print("\t" + full + "\t=>\t" + dump)
            # raise NotImplementedError
            shutil.move(full, dump)

            # raise


def dump_model(f: str, o: str, texture_root: str = None, texture_ext: str = None):
    print(f + "\t=>\t" + o)
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        try:
            whm = WhmChunky.create(chunky)
        except UnimplementedMslcBlockFormat as e:
            if e.format == 55:
                print("Skipping funky vertex buffer?")
                raise
            elif e.format == 48:
                print("Found an invalid index buffer?")
                raise
            else:
                raise
        write_obj_mtl(o, whm.msgr, texture_root, texture_ext)


if __name__ == "__main__":
    # raw_dump()
    # exit()
    # print_meta(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm")
    # dump_model(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm",
    #            r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion\\")
    # dump_full_model(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard\troops\guardsmen.whm",
    #                 r"D:\Dumps\DOW I\whm-model\art\ebps\races\imperial_guard\troops\guardsmen.obj")

    dump_all_model(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-model", r"D:\Dumps\DOW I\textures", ".tga")

    # dump_all_obj(r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion")
    # dump_obj(r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion\aspiring_champion_banner",
    #            r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion\aspiring_champion_banner")
