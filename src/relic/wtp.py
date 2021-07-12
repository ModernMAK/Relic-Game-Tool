import json
import os
import struct
from dataclasses import dataclass
from io import BytesIO
from os.path import join, dirname
from typing import List, Tuple, BinaryIO, Optional

from PIL import Image, ImageOps

from relic import chunky
from relic.chunky import DataChunk, FolderChunk, RelicChunky
from relic.dxt import get_full_dxt_header, DDS_MAGIC, build_dow_tga_color_header, build_dow_tga_gray_header
from relic.shared import EnhancedJSONEncoder, walk_ext

_LAYER_NAMES = {
    0: "Primary",
    1: "Secondary",
    2: "Trim",
    3: "Weapon",
    4: "Detail",  # AKA Trim2
    5: "Dirt",  # Found this kinda cool; wonder if maps have a specific dirt color to allow for snow FX
}


def raw_dump():
    chunky.dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\wtp-chunky", [".wtp"], skip_fatal=True)


def meta_dump():
    for root, file in walk_ext(r"D:\Dumps\DOW I\sga", [".wtp"]):
        full = join(root, file)
        print_meta(full)


#
# @dataclass
# class HeadChunk:
#     _DATA = struct.Struct("< l l")
#     image_format: int
#     unk_a: int  # tex_count maybe?
#
#     @classmethod
#     def create(cls, chunk: DataChunk) -> 'HeadChunk':
#         with BytesIO(chunk.data) as stream:
#             buffer = stream.read(cls._DATA.size)
#             args = cls._DATA.unpack(buffer)
#             # excess = stream.read()
#             return HeadChunk(*args)
#
#
from rsh import AttrChunk, ImagChunk, create_image, get_ext


@dataclass
class InfoChunk:
    _HEADER = struct.Struct("< l l")

    width: int
    height: int

    @classmethod
    def create(cls, chunk: DataChunk) -> 'InfoChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            height, width = cls._HEADER.unpack(buffer)  # width and height are swapped?
            return InfoChunk(width, height)


# Painted Team Layer Data?
@dataclass
class PtldChunk:
    _HEADER = struct.Struct("< l l")
    # flag or counter, incriments, probably the 'layer' being painted, trim, weapon, etc
    layer: int
    image: bytes

    @classmethod
    def create(cls, chunk: DataChunk) -> 'PtldChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            unk_a, size = cls._HEADER.unpack(buffer)  # width and height are swapped?
            image = stream.read(size)
            return PtldChunk(unk_a, image)


# Painted Team BD?
@dataclass
class PtbdChunk:
    _HEADER = struct.Struct("< f f f f")  # 4 floats?
    # floats are typically positions, uv coordinates?
    # atlas size maybe? IDK
    unk_a: float
    unk_b: float
    unk_c: float
    unk_d: float

    @classmethod
    def create(cls, chunk: DataChunk) -> 'PtbdChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            args = cls._HEADER.unpack(buffer)
            return PtbdChunk(*args)


# Painted Team BN?
# Looks identical to PTBD
@dataclass
class PtbnChunk:
    _HEADER = struct.Struct("< f f f f")  # 4 floats?
    unk_a: float
    unk_b: float
    unk_c: float
    unk_d: float

    @classmethod
    def create(cls, chunk: DataChunk) -> 'PtbnChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            args = cls._HEADER.unpack(buffer)
            return PtbnChunk(*args)


#
#

#
#
@dataclass
class TpatChunk:
    info: InfoChunk
    imag: ImagChunk
    ptld: List[PtldChunk]
    # Under the assumption that there can only be one and that it may be missing
    ptbd: Optional[PtbdChunk] = None
    ptbn: Optional[PtbnChunk] = None

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'TpatChunk':
        info_chunk = chunk.get_chunk("INFO")
        imag_chunk = chunk.get_chunk("IMAG")
        ptld_chunks = chunk.get_all_chunks("PTLD", True)
        ptbd_chunk = chunk.get_chunk("PTBD", True)
        ptbn_chunk = chunk.get_chunk("PTBN", True)

        info = InfoChunk.create(info_chunk)
        imag = ImagChunk.create(imag_chunk)
        ptld = [PtldChunk.create(c) for c in ptld_chunks]
        ptbd = PtbdChunk.create(ptbd_chunk) if ptbd_chunk else None
        ptbn = PtbdChunk.create(ptbn_chunk) if ptbn_chunk else None

        return TpatChunk(info, imag, ptld, ptbd, ptbn)


@dataclass
class WtpFile:
    tpat: TpatChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WtpFile':
        tpat_folder = chunky.get_chunk("TPAT")
        tpat = TpatChunk.create(tpat_folder)
        return WtpFile(tpat)


def print_meta(f: str):
    with open(f, "rb") as handle:
        try:
            chunky = RelicChunky.unpack(handle)
        except TypeError as e:
            print(e)
            return
        rsh = WtpFile.create(chunky)
        meta = json.dumps(rsh, indent=4, cls=EnhancedJSONEncoder)
        print(meta)


def create_mask_image(stream: BinaryIO, chunk: PtldChunk, info: InfoChunk):
    data = chunk.image
    header = build_dow_tga_gray_header(info.width, info.height)
    stream.write(header)
    stream.write(data)


def dump_wtp_as_image(f: str, o: str):
    wtp = get_wtp(f)
    if not wtp:
        print(f"Cant parse '{f}'")
        return

    imag = wtp.tpat.imag
    ext = get_ext(imag.attr.img)
    try:
        os.makedirs(o)
    except FileExistsError:
        pass

    main = join(o, "main" + ext)
    with open(main, "wb") as writer:
        create_image(writer, imag)
    for p in wtp.tpat.ptld:
        layer = join(o, f"layer-{_LAYER_NAMES.get(p.layer)}.tga")
        with open(layer, "wb") as writer:
            create_mask_image(writer, p, wtp.tpat.info)


def get_wtp(f: str):
    with open(f, "rb") as handle:
        try:
            chunky = RelicChunky.unpack(handle)
            rsh = WtpFile.create(chunky)
            return rsh
        except TypeError:
            return None


def dump_all_wtp_as_image(f: str, o: str):
    for root, file in walk_ext(f, ["wtp"]):
        src = join(root, file)
        dest = src.replace(f, o, 1)
        print(src)
        print("\t", dest)
        try:
            dump_wtp_as_image(src, dest)
        except NotImplementedError as e:
            print("\t\t", e)


#
# def get_dds_format(format: int) -> str:
#     lookup = {
#         8: "DXT1",
#         10: "DXT3",
#         11: "DXT5",
#     }
#     return lookup.get(format)
#
#
# _TGA_FORMATS = [0]
#
#
# def get_ext(format: int) -> str:
#     if format in _TGA_FORMATS:
#         return ".tga"
#     elif get_dds_format(format) != None:
#         return ".dds"
#     else:
#         raise NotImplementedError(format)
#
#
# def create_image(stream: BinaryIO, chunk: ImagChunk):
#     info = chunk.attr
#     data = chunk.data.data
#     format = get_dds_format(info.img)
#     if format is not None:
#         # DDS
#         header = get_full_dxt_header(format, info.width, info.height, len(data), info.mips)
#         stream.write(DDS_MAGIC)
#         stream.write(header)
#         stream.write(data)
#         return
#
#     if info.img in _TGA_FORMATS:
#         header = build_dow_tga_header(info.width, info.height)
#         stream.write(header)
#         stream.write(data)
#         return
#
#     if format is None:
#         raise NotImplementedError(info.img)
#
#
# def get_rsh(f: str):
#     with open(f, "rb") as handle:
#         chunky = RelicChunky.unpack(handle)
#         rsh = RshFile.create(chunky)
#         return rsh
#
#
# def print_meta(f: str):
#     with open(f, "rb") as handle:
#         chunky = RelicChunky.unpack(handle)
#         rsh = RshFile.create(chunky)
#         meta = json.dumps(rsh, indent=4, cls=EnhancedJSONEncoder)
#         print(meta)
#
#
# def dump_rsh_as_image(f: str, o: str):
#     rsh = get_rsh(f)
#
#     ext = get_ext(rsh.shrf.texture.imag.attr.img)
#     o += ext
#
#     try:
#         os.makedirs(dirname(o))
#     except FileExistsError:
#         pass
#     try:
#         with open(o, "wb") as writer:
#             create_image(writer, rsh.shrf.texture.imag)
#     except NotImplementedError as e:
#         try:
#             os.remove(o)
#         except FileNotFoundError:
#             pass
#         raise
#
#
# def dump_all_rsh_as_image(f: str, o: str):
#     for root, file in walk_ext(f, ["rsh"]):
#         src = join(root, file)
#         dest = src.replace(f, o, 1)
#         print(src)
#         print("\t", dest)
#         try:
#             dump_rsh_as_image(src, dest)
#         except NotImplementedError as e:
#             print("\t\t", e)
#
#


if __name__ == "__main__":
    # meta_dump()
    # raw_dump()
    dump_all_wtp_as_image(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\wtp")
    # fix_texture_inverstion("D:\Dumps\DOW I\dds")
