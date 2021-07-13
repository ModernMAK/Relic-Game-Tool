import json
import os
import struct
import subprocess
from dataclasses import dataclass
from io import BytesIO
from os.path import join, dirname
from typing import BinaryIO

from relic import chunky
from relic.chunky import DataChunk, FolderChunk, RelicChunky
from relic.dxt import get_full_dxt_header, DDS_MAGIC, build_dow_tga_color_header
from relic.shared import EnhancedJSONEncoder, walk_ext


def raw_dump():
    chunky.dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\rsh-chunky", [".rsh"])


@dataclass
class HeadChunk:
    _DATA = struct.Struct("< l l")
    image_format: int
    unk_a: int  # tex_count maybe?

    @classmethod
    def create(cls, chunk: DataChunk) -> 'HeadChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._DATA.size)
            args = cls._DATA.unpack(buffer)
            # excess = stream.read()
            return HeadChunk(*args)


# Info on ATTR Structure STOLEN FROM IBBoard.Relic.RelicTools
@dataclass
class AttrChunk:
    _MIP = struct.Struct("< l")
    _HEADER = struct.Struct("< l l l")

    img: int
    width: int
    height: int
    mips: int

    @classmethod
    def create(cls, chunk: DataChunk) -> 'AttrChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            img, height, width = cls._HEADER.unpack(buffer)  # width and height are swapped?

            if stream.tell() < len(chunk.data):
                buffer = stream.read(cls._MIP.size)
                mips = cls._MIP.unpack(buffer)[0]
            else:
                mips = 0

            return AttrChunk(img, width, height, mips)


@dataclass
class ImagChunk:
    attr: AttrChunk
    data: DataChunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'ImagChunk':
        attr_chunk = chunk.get_chunk("ATTR")
        data_chunk = chunk.get_chunk("DATA")

        attr = AttrChunk.create(attr_chunk)
        data = data_chunk

        return ImagChunk(attr, data)


@dataclass
class TxtrChunk:
    head: HeadChunk
    imag: ImagChunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'TxtrChunk':
        head_chunk = chunk.get_chunk("HEAD")
        imag_chunk = chunk.get_chunk("IMAG")

        head = HeadChunk.create(head_chunk)
        imag = ImagChunk.create(imag_chunk)

        return TxtrChunk(head, imag)


@dataclass
class ShrfChunk:
    texture: TxtrChunk

    # shader: ShdrChunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'ShrfChunk':
        txtr_chunk = chunk.get_chunk("TXTR")
        # shdr_chunk = chunk.get_chunk("SHDR")

        txtr = TxtrChunk.create(txtr_chunk)
        # shdr = ShdrChunk.create(shdr_chunk)

        return ShrfChunk(txtr)  # shdr,)


@dataclass
class RshFile:
    shrf: ShrfChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'RshFile':
        shrf_folder = chunky.get_chunk("SHRF")
        shrf = ShrfChunk.create(shrf_folder)
        return RshFile(shrf)


def get_dds_format(format: int) -> str:
    lookup = {
        8: "DXT1",
        10: "DXT3",
        11: "DXT5",
    }
    return lookup.get(format)


_TGA_FORMATS = [0]


def get_ext(format: int) -> str:
    if format in _TGA_FORMATS:
        return ".tga"
    elif get_dds_format(format) != None:
        return ".dds"
    else:
        raise NotImplementedError(format)


def create_image(stream: BinaryIO, chunk: ImagChunk):
    info = chunk.attr
    data = chunk.data.data
    format = get_dds_format(info.img)
    if format is not None:
        # DDS
        header = get_full_dxt_header(format, info.width, info.height, len(data), info.mips)
        stream.write(DDS_MAGIC)
        stream.write(header)
        stream.write(data)
        return

    if info.img in _TGA_FORMATS:
        header = build_dow_tga_color_header(info.width, info.height)
        stream.write(header)
        stream.write(data)
        return

    if format is None:
        raise NotImplementedError(info.img)


def get_rsh(f: str):
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        rsh = RshFile.create(chunky)
        return rsh


def print_meta(f: str):
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        rsh = RshFile.create(chunky)
        meta = json.dumps(rsh, indent=4, cls=EnhancedJSONEncoder)
        print(meta)


def dump_rsh_as_image(f: str, o: str):
    rsh = get_rsh(f)

    ext = get_ext(rsh.shrf.texture.imag.attr.img)
    o += ext

    try:
        os.makedirs(dirname(o))
    except FileExistsError:
        pass
    try:
        with open(o, "wb") as writer:
            create_image(writer, rsh.shrf.texture.imag)
    except NotImplementedError as e:
        try:
            os.remove(o)
        except FileNotFoundError:
            pass
        raise


def dump_all_rsh_as_image(f: str, o: str):
    for root, file in walk_ext(f, ["rsh"]):
        src = join(root, file)
        dest = src.replace(f, o, 1)
        print(src)
        print("\t", dest)
        try:
            dump_rsh_as_image(src, dest)
        except NotImplementedError as e:
            print("\t\t", e)


def directex_fix_texture(f: str, path: str = r"..\dll\texconv.exe"):
    path = os.path.abspath(path)
    outdir = dirname(f)
    subprocess.run([path, "-vflip", f, "-y", "-o", outdir])


def fix_texture_inversion(folder: str):
    for root, file in walk_ext(folder, ["dds"]):
        f = join(root, file)
        directex_fix_texture(f)


if __name__ == "__main__":
    # pass
    dump_all_rsh_as_image("D:\Dumps\DOW I\sga", "D:\Dumps\DOW I\dds")
    fix_texture_inversion("D:\Dumps\DOW I\dds")
