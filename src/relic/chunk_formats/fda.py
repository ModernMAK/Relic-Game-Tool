# Stolen from https://scratchpad.fandom.com/wiki/Relic_Chunky_files
import math
import os
import struct
from dataclasses import dataclass
from io import BytesIO
from os.path import join, splitext
from typing import BinaryIO, List

from relic.chunky.data_chunk import DataChunk
from relic.chunky.folder_chunk import FolderChunk
from relic.chunky.relic_chunky import RelicChunky
from relic.chunky.relic_chunky_header import RelicChunkyHeader
from relic.file_formats import aiff
from relic.shared import walk_ext

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
        args = _DATA_STRUCT.unpack(chunk.data)[0]
        data = chunk.data[4:]
        return FdaDataChunk(args, data)


@dataclass
class FdaChunky:
    header: RelicChunkyHeader
    info_block: FdaInfoChunk
    data_block: FdaDataChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'FdaChunky':
        header = chunky.header
        # We ignore burn info ~ FBIF
        fda: FolderChunk = chunky.get_chunk(id="FDA ")

        # We fetch 'FDA ' and get the Info/Data block from FDA
        info = fda.get_chunk(id="INFO")
        data = fda.get_chunk(id="DATA")

        # parse the blocks
        fda_info = FdaInfoChunk.create(info)
        fda_data = FdaDataChunk.create(data)

        return FdaChunky(header, fda_info, fda_data)


class Converter:
    COMP = "COMP"
    COMP_desc = "Relic Codec v1.6"

    @classmethod
    def Fda2Aiffr(cls, chunky: FdaChunky, stream: BinaryIO) -> int:
        with BytesIO() as temp:
            aiff.write_default_FVER(temp)
            info = chunky.info_block
            frames = len(chunky.data_block.data) / math.ceil(info.block_bitrate / 8)
            assert frames == int(frames)
            frames = int(frames)

            aiff.write_COMM(temp, info.channels, frames, info.sample_size, info.sample_rate, cls.COMP, cls.COMP_desc,
                            use_fixed=True)
            aiff.write_SSND(temp, chunky.data_block.data, info.block_bitrate)
            with BytesIO() as marker:
                aiff.write_default_markers(marker)
                marker.seek(0, 0)
                buffer = marker.read()
                aiff.write_MARK(temp, 3, buffer)

            temp.seek(0, 0)
            buffer = temp.read()
            return aiff.write_FORM(stream, buffer)

    @classmethod
    def Aiffr2Fda(cls, stream: BinaryIO) -> FdaChunky:
        buffer = aiff.read_FORM(stream)
        info = FdaInfoChunk(None, None, None, None, 0, 0xffffffff, 0)
        data = None
        with BytesIO(buffer) as form:
            while form.tell() != len(buffer):
                block_type = form.read(4).decode("ascii")
                form.seek(-4, 1)

                if block_type == aiff.FVER:
                    _ = aiff.read_FVER(form)
                elif block_type == aiff.COMM:
                    info.channels, _, info.sample_size, info.sample_rate, _, _ = aiff.read_COMM(form)
                elif block_type == aiff.SSND:
                    data, info.block_bitrate = aiff.read_SSND(form)

        return FdaChunky(RelicChunkyHeader.default(), info, FdaDataChunk(len(data), data))




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