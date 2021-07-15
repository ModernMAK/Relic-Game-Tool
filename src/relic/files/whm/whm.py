import json
import os
import struct
from dataclasses import dataclass
from io import BytesIO
from os.path import join, splitext, dirname
from typing import BinaryIO, List, TextIO

from relic.chunky.data_chunk import DataChunk
from relic.chunky.dumper import dump_all_chunky
from relic.chunky.folder_chunk import FolderChunk
from relic.chunky.relic_chunky import RelicChunky
from relic.shared import walk_ext, EnhancedJSONEncoder

# FBIF
# RGSM (name of model)
# => MSGR
# => => MSLC (submodel? body part?)
# => => => BVOL
# => => => DATA
# => => BVOL
# => => DATA
# => SSHR (names are paths to textures [as images])
# => MARK
# => ANIM (name)
# => SKEL

_UNK_STRUCT = struct.Struct("< L L")
_NUM = struct.Struct("< L")


# MSGR

@dataclass
class MsgrName:
    name: str
    unk_a: int
    unk_b: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MsgrName':
        buffer = stream.read(_NUM.size)
        count = _NUM.unpack(buffer)[0]
        name = stream.read(count).decode("ascii")
        buffer = stream.read(_UNK_STRUCT.size)
        unk_a, unk_b = _UNK_STRUCT.unpack(buffer)
        return MsgrName(name, unk_a, unk_b)


@dataclass
class MsgrChunk:
    parts: List[MsgrName]
    submeshes: List['MslcChunk']

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'MsgrChunk':
        data: DataChunk = chunk.get_chunk(id="DATA", recursive=False)
        # the id is DATA not the type (alhough it is coincidentally, a ChunkType.Data)
        # data = get_chunk_by_id(chunk.chunks, "DATA", flat=True)
        with BytesIO(data.data) as stream:
            buffer = stream.read(_NUM.size)
            count = _NUM.unpack(buffer)[0]
            parts = [MsgrName.unpack(stream) for _ in range(count)]
        submeshes = [MslcChunk.create(mscl) for mscl in chunk.get_chunks(id="MSLC")]

        return MsgrChunk(parts, submeshes)


# SSHR
@dataclass
class SshrChunk:
    name: str

    @classmethod
    def create(cls, chunk: DataChunk) -> 'SshrChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(_NUM.size)
            num = _NUM.unpack(buffer)[0]
            name = stream.read(num).decode("ascii")
            return SshrChunk(name)


@dataclass
class MsclHeader:
    unk_a: int
    flag_b: bytes
    unk_c: int
    unk_d: int
    name_count: int

    _HEADER = struct.Struct("< L b L L L")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MsclHeader':
        buffer = stream.read(cls._HEADER.size)
        args = cls._HEADER.unpack(buffer)
        return MsclHeader(*args)


@dataclass
class MslcName:
    name: str
    unk_a: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MslcName':
        buffer = stream.read(_NUM.size)
        size = _NUM.unpack(buffer)[0]
        name = stream.read(size).decode("ascii")

        buffer = stream.read(_NUM.size)
        unk_a = _NUM.unpack(buffer)[0]

        return MslcName(name, unk_a)


@dataclass
class MslcChunk:
    V_SIZE_39 = 48
    V_SIZE_37 = 32
    V_SIZE = {39: V_SIZE_39, 37: V_SIZE_37}
    I_SIZE = 2

    # name:str

    header: MsclHeader
    names: List[MslcName]

    buffer_format: int

    vertex_data: bytes

    unk_c: int

    textures: List[str]

    index_data: bytes

    unk_d: int
    unk_e: int
    unk_f: int
    unk_g: int

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'MslcChunk':
        # name = chunk.name
        data: DataChunk = chunk.get_chunk(id="DATA", recursive=False)
        # 0x5570 - 0x770 = 0x4E00 ! 48 BITS ?!
        # 0xe05d - 0xa39d = 0x3CC0 ~ 15552 ! 32 BITS ?!

        with BytesIO(data.data) as stream:
            header = MsclHeader.unpack(stream)
            names = [MslcName.unpack(stream) for _ in range(header.name_count)]
            vertex_count, buffer_format = struct.unpack("< L L", stream.read(8))
            # print(chunk.name, "\n","\t", "HEADER:", header.unk_a, header.flag_b, header.unk_c, header.unk_d, "~", buffer_format)
            vertex = stream.read(vertex_count * cls.V_SIZE.get(buffer_format))
            buffer = stream.read(8)
            unk_c, texture_count = struct.unpack("< L L", buffer)
            textures = []
            for _ in range(texture_count):
                size = _NUM.unpack(stream.read(_NUM.size))[0]
                name = stream.read(size).decode("ascii")
                textures.append(name)

            index_count = _NUM.unpack(stream.read(_NUM.size))[0]
            index = stream.read(index_count * cls.I_SIZE)
            unk_d, unk_e, unk_f, unk_g = struct.unpack("< L L L L", stream.read(4 * 4))

        return MslcChunk(header, names, buffer_format, vertex, unk_c, textures, index, unk_d, unk_e, unk_f, unk_g)


@dataclass
class WhmChunk:
    sshr: List[SshrChunk]
    msgr: MsgrChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WhmChunk':
        sshr = [SshrChunk.create(c) for c in chunky.get_chunks(id='SSHR')]
        msgr = MsgrChunk.create(chunky.get_chunk(id="MSGR"))
        return WhmChunk(sshr, msgr)


# after MSCL texture name is the index count, multiply by two due to the size (short)?

def raw_dump():
    dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-chunky", [".whm"])


def print_meta(f: str):
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        whm = WhmChunk.create(chunky)
        meta = json.dumps(whm, indent=4, cls=EnhancedJSONEncoder)
        print(meta)


def write_vertex(stream: TextIO, x, y, z):
    stream.write('v %f %f %f\n' % (x, y, z))


def write_normal(stream: TextIO, x, y, z):
    stream.write('vn %f %f %f\n' % (x, y, z))


def write_uv2(stream: TextIO, x, y):
    stream.write('vt %f %f\n' % (x, y))


def write_tri(stream: TextIO, *args, v_offset: int = 0):
    stream.write('f')
    for v in args:
        stream.write(' %i/%i/%i' % (v + v_offset, v + v_offset, v + v_offset))
    stream.write("\n")


def write_obj_name(stream: TextIO, name: str):
    stream.write(f'o {name}\n')


# DOW VERTEX FORMAT:
#  POS ~ 3 float32 (12 bytes)
#  ??? ~ 4 float32 (16 bytes)?
#  NORM? ~ 3 float32 (12 bytes)
#  UV ~ 2 float32 (8 bytes)
#       TOTAL ~ 48 bytes

def write_obj(stream: TextIO, vertex: BinaryIO, indexes: BinaryIO, v_count: int, t_count: int, name: str = None,
              v_offset: int = 0):
    if name:
        write_obj_name(stream, name)

    _POS = struct.Struct("< f f f")
    # _UNK_A = struct.Struct("< f f f")
    _UV = struct.Struct("< f f")
    for _ in range(v_count):
        buffer = vertex.read(_POS.size)
        x, y, z = _POS.unpack(buffer)
        write_vertex(stream, x, y, z)

    vertex.seek(4 * 4 * v_count, 1)

    for _ in range(v_count):
        buffer = vertex.read(_POS.size)
        x, y, z = _POS.unpack(buffer)
        write_normal(stream, x, y, z)

    for _ in range(v_count):
        buffer = vertex.read(_UV.size)
        u, v = _UV.unpack(buffer)
        write_uv2(stream, u, v)
    # vertex.seek(4 * 1 * v_count, 1)

    _TRI = struct.Struct("< h h h")
    for _ in range(t_count):
        buffer = indexes.read(_TRI.size)
        a, b, c = _TRI.unpack(buffer)
        write_tri(stream, a, b, c,
                  v_offset=v_offset + 1)  # blender is 1th based NOT 0th based, so we add 1 to the offset


def dump_obj(f: str, o: str):
    try:
        os.makedirs(dirname(o))
    except FileExistsError:
        pass

    with open(o + ".obj", "w") as obj:
        with open(f + ".meta") as m:
            meta = json.loads(m.read())

        with open(f + ".vert", "rb") as vertex:
            with open(f + ".tri", "rb") as index:
                write_obj(obj, vertex, index, meta['vertexes'], meta['triangles'])


def dump_all_obj(f: str):
    for root, file in walk_ext(f, ".vert"):
        full = join(root, file)
        full, _ = splitext(full)
        dump_obj(full, full)


def dump_model(f: str, o: str):
    print("" + f)
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        whm = WhmChunk.create(chunky)

        for i, mesh in enumerate(whm.msgr.submeshes):
            name = whm.msgr.parts[i].name
            full_o = join(o, name)
            try:
                os.makedirs(dirname(full_o))
            except FileExistsError:
                pass
            print("\t" + full_o)

            with open(full_o + ".vert", "wb") as v:
                v.write(mesh.vertex_data)
            with open(full_o + ".tri", "wb") as t:
                t.write(mesh.index_data)
            with open(full_o + ".meta", "w") as m:
                m.write(json.dumps({'vertexes': len(mesh.vertex_data) / 48, 'triangles': len(mesh.index_data) / 6}))


def dump_all_full_model(f: str, o: str):
    for root, file in walk_ext(f, ".whm"):
        full = join(root, file)
        dump = full.replace(f, o, 1)
        dump, _ = splitext(dump)
        dump += ".obj"
        try:
            dump_full_model(full, dump)
        except Exception as e:
            print("\t", e)
            try:
                os.remove(dump)
            except Exception:
                pass
            raise


def dump_full_model(f: str, o: str):
    print("" + f)
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        whm = WhmChunk.create(chunky)

        try:
            os.makedirs(dirname(o))
        except FileExistsError:
            pass
        v_offset = 0
        with open(o, "w") as obj:
            for i, mesh in enumerate(whm.msgr.submeshes):
                if mesh.buffer_format != 39:
                    continue
                v_count = int(len(mesh.vertex_data) / 48)
                t_count = int(len(mesh.index_data) / 6)
                name = whm.msgr.parts[i].name
                with BytesIO(mesh.vertex_data) as v_data:
                    with BytesIO(mesh.index_data) as i_data:
                        write_obj(obj, v_data, i_data, v_count, t_count, name, v_offset=v_offset)
                        v_offset += v_count


if __name__ == "__main__":
    # print_meta(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm")
    # dump_model(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm",
    #            r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion\\")
    # dump_full_model(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard\troops\guardsmen.whm",
    #                 r"D:\Dumps\DOW I\whm-model\art\ebps\races\imperial_guard\troops\guardsmen.obj")

    dump_all_full_model(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-model")

    # dump_all_obj(r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion")
    # dump_obj(r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion\aspiring_champion_banner",
    #            r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion\aspiring_champion_banner")

# 2a50 ~ 51 = 2a00 (VERTEX ONLY)
# 10752 bytes OR 2688 4byte words
# 0xEA01 ~ 59905 ~ 0.17 OR 0.04 (prob not this)
# 0xEA ~ 234 ~ 45.9 OR 11.48 (prob no this)
# 0xE0 ~ 224 ~ 48 OR 12
# 0x27 ~ 39 ~  275.69 OR 68.92

# 224 vertexes


# Index Count is less obvious
# possible starts?
# @2aa1 ~ 10913
# @2aa5 ~ 10917
# possible ends
# @3024 ~ 12324
# @3034 ~ 12340
# possible sizes?
# 1407 ~ 0x57f +/-1? ~ 0x580 / 0x57e
# 1411 ~ 0x583 +/-1? ~ 0x584 / 0x582
# 1423 ~ 0x58f +/-1? ~ 0x590 / 0x58e
# 1427 ~ 0x593 +/-1? ~ 0x594 / 0x592
# Triangle counts?
# 469 ~ +1 invalid ~ -1 invalid
# 470.33 ~ +1 invalid ~ 470
# 474.33 ~ +1 invalid ~ 474
# 475.66 ~ 476 ~ -1 invalid
# Triangle counts (short groups)
# 234.5 ~ / ~ / @ ~
# / ~ / ~ 235 @ EB
# / ~ / ~ 237 @ ED
# / ~ 238 ~ / @ EE

# 74 ~ @0x4A
# @27 ~ 39

# @be02 ~ 48642
# @02be ~ 702

# 0x2aa1 ~ 0x3035 ~ 0x594
# 10913 ~ 12341 = 1428
# /2 ~ 714 ~ 2CA
# /3 ~ 476 ~ 1DC
# /6 ~ 238 ~ EC

#
# 3020 - 2aa4 by jumping pairs of 6's we got an index range
# 12320 ~ 10916 = 1404
# 234 Triangles @ 0xEA
# PROB NOT THIS 468 Triangle's
# 702 Indexes @ 0x2BE... which was the obvious answer but I DIDNT BELIEVE!!!!! (its the num I mentioned way up top)

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WITH NO EVIDENCE WHATSOEVER I AM 100% CONFIDENT THAT BVOL is 'Bounding Volume'
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# VERTEX LAYOUT ( V representing vertex count ) ~ layout in bytes
# POS: V * 3 (xyz) * 4 bytes (int32/float32?) ~ 12 ~ 0x258
# NORM?: V * 4 (???) * 4 bytes (int32/float32?) ~ 16 ~ 0x320
# ???: V * 3 (???) * 4 bytes (int32/float32) ~ 12 ~ 0x258
# UV: V * 2 (???) * 4 bytes    ~ 8 ~ 0x190         # 0x960-0x578 =0x3e8

# 0x960-0x7d0?

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# UV is inverted
#   More likely, textures are inverted?
#       BUT
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
