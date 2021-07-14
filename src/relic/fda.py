# Stolen from https://scratchpad.fandom.com/wiki/Relic_Chunky_files
import dataclasses
import json
import math
import os
import shutil
import struct
import tempfile
from dataclasses import dataclass
from io import BytesIO
from os.path import join, dirname, splitext, exists, basename
from typing import BinaryIO, List

from relic.chunky import DataChunk, FileHeader, RelicChunky
from relic.shared import walk_ext

FIXED = True

from relic import aiffr

_INFO_STRUCT = struct.Struct("< L L L L L L L")
_DATA_STRUCT = struct.Struct("< L")


@dataclass
class FdaInfoChunk:
    channels: int
    sample_size: int
    block_bitrate: int
    sample_rate: int
    begin_loop: int
    end_loop: int
    start_offset: int

    @classmethod
    def create(cls, chunk: DataChunk) -> 'FdaInfoChunk':
        args = _INFO_STRUCT.unpack_from(chunk.data, 0)
        return FdaInfoChunk(*args)


@dataclass
class FdaDataChunk:
    size: int
    data: bytes

    @classmethod
    def create(cls, chunk: DataChunk) -> 'FdaDataChunk':
        args = _DATA_STRUCT.unpack_from(chunk.data, 0)[0]
        data = chunk.data[4:]
        return FdaDataChunk(args, data)


@dataclass
class FdaChunky:
    header: FileHeader
    # fbif: DataChunk
    # fda: FolderChunk
    # info: DataChunk
    # data: DataChunk
    info_block: FdaInfoChunk
    data_block: FdaDataChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'FdaChunky':
        header = chunky.header
        # fbif = chunky.get_chunk("FBIF")
        fda = chunky.get_chunk("FDA ")
        info = fda.get_chunk("INFO")
        data = fda.get_chunk("DATA")

        fda_info = FdaInfoChunk.create(info)
        fda_data = FdaDataChunk.create(data)

        return FdaChunky(header, fda_info, fda_data)


class Converter:
    COMP = "COMP"
    COMP_desc = "Relic Codec v1.6"

    @classmethod
    def Fda2Aiffr(cls, chunky: FdaChunky, stream: BinaryIO, *, use_fixed: bool = False) -> int:
        with BytesIO() as temp:
            aiffr.write_default_FVER(temp)
            info = chunky.info_block
            frames = len(chunky.data_block.data) / math.ceil(info.block_bitrate / 8)
            assert frames == int(frames)
            frames = int(frames)
            # samples = info.block_bitrate / info.sample_size

            aiffr.write_COMM(temp, info.channels, frames, info.sample_size, info.sample_rate,
                             cls.COMP, cls.COMP_desc, use_fixed=use_fixed)
            aiffr.write_SSND(temp, chunky.data_block.data, info.block_bitrate)
            with BytesIO() as marker:
                aiffr.write_default_markers(marker)
                marker.seek(0, 0)
                buffer = marker.read()
                aiffr.write_MARK(temp, 3, buffer)

            temp.seek(0, 0)
            buffer = temp.read()
            return aiffr.write_FORM(stream, buffer)

    @classmethod
    def Aiffr2Fda(cls, stream: BinaryIO) -> FdaChunky:
        buffer = aiffr.read_FORM(stream)
        info = FdaInfoChunk(None, None, None, None, 0, 0xffffffff, 0)
        data = None
        with BytesIO(buffer) as form:
            while form.tell() != len(buffer):
                type = form.read(4).decode("ascii")
                form.seek(-4, 1)

                if type == aiffr.FVER:
                    _ = aiffr.read_FVER(form)
                elif type == aiffr.COMM:
                    info.channels, _, info.sample_size, info.sample_rate, _, _ = aiffr.read_COMM(form)
                elif type == aiffr.SSND:
                    data, info.block_bitrate = aiffr.read_SSND(form)
        header = FileHeader("\r\n\x00\x00", 1, 1)
        return FdaChunky(header, info, FdaDataChunk(len(data), data))


def run_old():
    class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            if isinstance(o, bytes):
                l = len(o)
                if len(o) > 16:
                    o = o[0:16]
                    return o.hex(sep=" ") + f" ... [+{l - 16} Bytes]"
                return o.hex(sep=" ")
            return super().default(o)

    in_root = "gen/sga/dump"
    out_root_meta = "gen/fda/meta"
    out_root_dump = "gen/fda/dump"
    out_root_shared = "gen/fda/shared_dump"
    for root, _, files in os.walk(in_root):
        for file in files:
            if ".fda" not in file:
                continue

            full_in = join(root, file)
            full_out_meta = full_in.replace(in_root, out_root_meta)
            full_out_dump = full_in.replace(in_root, out_root_dump)
            print(full_in)
            with open(full_in, "rb") as handle:
                try:
                    chunky = RelicChunky.unpack(handle)
                except ValueError as e:
                    print(f"\tNot Chunky?!\n\t\t'{e}'")
                    continue

            print("\tWriting Meta...")
            meta = json.dumps(chunky, indent=4, cls=EnhancedJSONEncoder)
            print("\t\t", meta)
            meta_name = full_out_meta + ".json"
            try:
                os.makedirs(dirname(meta_name))
            except FileExistsError:
                pass
            with open(meta_name, "w") as writer:
                writer.write(meta)

            print("\tWriting Assets...")
            for name, c in chunky.walk_data():
                print(f"\t\t{name}")
                dump_name = join(full_out_dump, name)
                print(f"\t\t\t{dump_name}")
                try:
                    os.makedirs(dirname(dump_name))
                except FileExistsError:
                    pass
                with open(dump_name, "wb") as writer:
                    writer.write(c.data_block)

                shared_dump_name = join(out_root_shared, name)
                try:
                    os.makedirs(dirname(shared_dump_name))
                except FileExistsError:
                    pass
                with open(shared_dump_name, "wb") as writer:
                    writer.write(c.data_block)


def run_new():
    in_root = "gen/sga/dump"
    out_root_dump = "gen/fda/dump"
    for root, _, files in os.walk(in_root):
        for file in files:
            if ".fda" not in file:
                continue

            full_in = join(root, file)
            print(full_in)
            with open(full_in, "rb") as handle:
                try:
                    chunky = RelicChunky.unpack(handle)
                except ValueError as e:
                    print(f"\tNot Chunky?!\n\t\t'{e}'")
                    continue
                fda_chunky = FdaChunky.create(chunky)

                full_out_dump = full_in.replace(in_root, out_root_dump)
                full_out_dump = splitext(full_out_dump)[0] + ".aifc"
                try:
                    os.makedirs(dirname(full_out_dump))
                except FileExistsError:
                    pass

                print("\tWriting Assets...")
                print(f"\t\t{full_out_dump}")
                with open(full_out_dump, "wb") as writer:
                    Converter.Fda2Aiffr(fda_chunky, writer)



def shared_dump(file: str, name: str, out_dir: str = None):
    out_dir = out_dir or "gen/fda/shared_dump"
    with open(file, "rb") as handle:
        try:
            chunky = RelicChunky.unpack(handle)
        except ValueError as e:
            print(e)
            pass
            # print(f"\tNot Chunky?!\n\t\t'{e}'")

        fda = FdaChunky.create(chunky)
        shared_path = join(out_dir, name)
        dir_path = os.path.dirname(shared_path)
        try:
            os.makedirs(dir_path)
        except FileExistsError:
            pass
        with open(shared_path, "wb") as writer:
            Converter.Fda2Aiffr(fda, writer, use_fixed=FIXED)


def safe_dump(file: str, name: str, out_dir: str = None):
    out_dir = out_dir or "gen/safe_fda/shared_dump"
    full = join(out_dir, name)
    path = "../dll/fda2aifc.exe"
    path = os.path.abspath(path)
    try:
        os.makedirs(dirname(full))
    except FileExistsError:
        pass

    import subprocess

    def create_temporary_copy(path) -> str:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, basename(path))
        shutil.copy2(path, temp_path)
        return temp_path

    temp_src = create_temporary_copy(file)
    temp_dst = temp_src + ".aifc"
    subprocess.call([path, f"{temp_src}", f"{temp_dst}"])
    if exists(temp_dst):
        shutil.copy2(temp_dst, full)


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


def safe_dump_all_fda(folder: str, out_dir: str = None, blacklist: List[str] = None, verbose: bool = False):
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

        safe_dump(full, f + ".aifc", out_dir)


if __name__ == "__main__":
    dump_all_fda(r"D:/Dumps/DOW I/sga",
                 out_dir=r"D:/Dumps/DOW I/fda", verbose=True)

# FDA are chunky files, but they are wierd; they appear to only be 2 chunks INFO and DATA (unnamed) + a named chunk fileburninfo
# 4 bytes; size of DATA
# 256 X; blocks of sound
#   According to the relic tool, this was aifc then converted to fda (I imagined they saved space by having the engine reconstruct it?)
#   https://www.moddb.com/mods/ultimate-apocalypse-mod/tutorials/extracting-the-music-from-dawn-of-war-mods
#       Downloading the tool comes with FDA Specs
