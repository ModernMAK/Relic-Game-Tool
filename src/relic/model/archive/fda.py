# Stolen from https://scratchpad.fandom.com/wiki/Relic_Chunky_files
import aifc
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
from typing import BinaryIO, Union, List, Tuple

FIXED = True

from relic.model.archive import aiffr

_FILE_MAGIC = "Relic Chunky"
_FILE_MAGIC_STRUCT = struct.Struct("< 12s")
_FILE_HEADER_STRUCT = struct.Struct("< 4s L L")

_DATA_MAGIC = "DATA"
_FOLDER_MAGIC = "FOLD"
_HEADER_STRUCT = struct.Struct("< 4s 4s L L L")


@dataclass
class ChunkHeader:
    type: str

    @property
    def is_data(self):
        return self.type == _DATA_MAGIC

    @property
    def is_folder(self):
        return self.type == _FOLDER_MAGIC

    @property
    def type_valid(self):
        return self.is_data or self.is_folder

    id: str
    version: int
    size: int
    name_size: int

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'ChunkHeader':
        buffer = stream.read(_HEADER_STRUCT.size)
        args = _HEADER_STRUCT.unpack(buffer)
        header = ChunkHeader(*args)
        header.id = header.id.decode("ascii")
        header.type = header.type.decode("ascii")
        if validate and not header.type_valid:
            raise TypeError(f"Type not valid! '{header.type}' @{stream.tell() - _HEADER_STRUCT.size} ~ [{buffer}]")
        return header


def read_all_chunks(stream: BinaryIO) -> List[Union['DataChunk', 'FolderChunk']]:
    chunks = []
    while True:
        try:
            header = ChunkHeader.unpack(stream, True)
        except struct.error:
            break

        if header.is_folder:
            c = FolderChunk.unpack(stream, header)
        elif header.is_data:
            c = DataChunk.unpack(stream, header)
        else:
            raise Exception("Header isn't folder or data! This should have been caught earlier!")
        chunks.append(c)
    return chunks


@dataclass
class DataChunk:
    header: ChunkHeader
    name: str
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'DataChunk':
        name = stream.read(header.name_size).decode("ascii").rstrip("\x00")
        data = stream.read(header.size)
        return DataChunk(header, name, data)


def walk_data_chunks(chunks: List[Union[DataChunk, 'FolderChunk']], parent: str = None) -> Tuple[str, DataChunk]:
    parent = parent or ""
    for chunk in chunks:
        if isinstance(chunk, FolderChunk):
            for name, chunk in chunk.walk_data():
                full = join(parent, name)
                yield full, chunk
        elif isinstance(chunk, DataChunk):
            yield join(parent, f"{chunk.header.id}-{chunk.name}"), chunk
        else:
            raise Exception("Data / Folder type error")


def walk_chunks(chunks: List[Union[DataChunk, 'FolderChunk']]) -> Tuple[Union[DataChunk, 'FolderChunk']]:
    for chunk in chunks:
        yield chunk
        if isinstance(chunk, FolderChunk):
            for chunk in walk_chunks(chunk.chunks):
                yield chunk


def get_chunk(chunks: List[Union[DataChunk, 'FolderChunk']], id: str = None) -> Union[DataChunk, 'FolderChunk']:
    for c in walk_chunks(chunks):
        if c.header.id == id:
            return c
    raise KeyError()


@dataclass
class FolderChunk:
    header: ChunkHeader
    name: str
    chunks: List[Union['FolderChunk', DataChunk]]

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'FolderChunk':
        name = stream.read(header.name_size).decode("ascii").rstrip("\x00")
        data = stream.read(header.size)
        with BytesIO(data) as window:
            chunks = read_all_chunks(window)
        return FolderChunk(header, name, chunks)

    def walk_data(self) -> Tuple[str, DataChunk]:
        return walk_data_chunks(self.chunks, parent=f"{self.header.id}-{self.name}")

    def get_chunk(self, id: str):
        return get_chunk(self.chunks, id)


@dataclass
class FileHeader:
    type_br: str
    unk_a: int
    unk_b: int

    @classmethod
    def unpack(cls, stream: BinaryIO):
        buffer = stream.read(_FILE_HEADER_STRUCT.size)
        type_br, a, b = _FILE_HEADER_STRUCT.unpack_from(buffer)
        type_br = type_br.decode("ascii")
        return FileHeader(type_br, a, b)


@dataclass
class RelicChunky:
    header: FileHeader
    chunks: List[Union[FolderChunk, DataChunk]]

    @classmethod
    def unpack(cls, stream: BinaryIO):
        buffer = stream.read(_FILE_MAGIC_STRUCT.size)
        magic = _FILE_MAGIC_STRUCT.unpack_from(buffer)[0].decode("ascii")
        if magic != _FILE_MAGIC:
            raise ValueError((magic, _FILE_MAGIC))
        header = FileHeader.unpack(stream)
        chunks = read_all_chunks(stream)
        return RelicChunky(header, chunks)

    def walk_data(self) -> Tuple[str, DataChunk]:
        return walk_data_chunks(self.chunks)

    def get_chunk(self, id: str):
        return get_chunk(self.chunks, id)


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


#
# def get_frames(data: bytes, info: FdaInfoChunk) -> List[bytes]:
#     # I assume frame size is padded?
#     # THIS IS AN ASASUMPTION,NOT BASED ON ANY EVIDENCE
#     frame_size = int(math.ceil(info.block_bitrate / 8))
#     frame_count = len(data) / frame_size
#     if frame_count != int(frame_count):
#         raise ValueError()
#     else:
#         frame_count = int(frame_count)
#     frames = [data[i * frame_size:i * frame_size + frame_size] for i in range(frame_count)]
#     return frames
#
#
# def get_samples(data: bytes, info: FdaInfoChunk) -> List[int]:
#     # I assume sample size is padded?
#     # THIS IS AN ASASUMPTION,NOT BASED ON ANY EVIDENCE
#     sample_size = int(math.ceil(info.sample_size / 8))
#     sample_count = len(data) / sample_size
#     if sample_count != int(sample_count):
#         raise ValueError()
#     else:
#         sample_count = int(sample_count)
#     byte_samples = [data[i * sample_size:i * sample_size + sample_size] for i in range(sample_count)]
#     samples = [int.from_bytes(sample, byteorder="little", signed=True) for sample in byte_samples]
#     return samples
#
#
# def get_channels(data: List[int], info: FdaInfoChunk) -> List[List[bytes]]:
#     # I assume sample size is padded?
#     # THIS IS AN ASASUMPTION,NOT BASED ON ANY EVIDENCE
#     channels = info.channels
#     if len(data) % channels != 0:
#         raise ValueError("Channel mismatch!")
#     channel_samples = len(data) // channels
#     channels = [[data[s * channels + c] for c in range(channels)] for s in range(channel_samples)]
#     return channels


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
    path = "../../../dll/fda2aifc.exe"
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
