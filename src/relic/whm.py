import json
import os
import struct
from dataclasses import dataclass
from io import BytesIO
from os.path import join, splitext, dirname
from typing import BinaryIO, List, TextIO, Tuple

from relic import chunky

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
from relic.chunky import DataChunk, RelicChunky, FolderChunk, get_chunk_by_id, get_all_chunks_by_id, dump_all_chunky
from relic.shared import walk_ext, EnhancedJSONEncoder

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
        data = get_chunk_by_id(chunk.chunks, "DATA", flat=True)
        with BytesIO(data.data) as stream:
            buffer = stream.read(_NUM.size)
            count = _NUM.unpack(buffer)[0]
            parts = [MsgrName.unpack(stream) for _ in range(count)]
        submeshes = [MslcChunk.create(mscl) for mscl in get_all_chunks_by_id(chunk.chunks, "MSLC")]

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


TYPE_FLOAT3 = Tuple[float, float, float]
TYPE_FLOAT2 = Tuple[float, float, float]
TYPE_INT3 = Tuple[int, int, int]


class VertexBufferTools:
    _POSITION = struct.Struct("< f f f")
    _NORMAL = struct.Struct("< f f f")
    _UV = struct.Struct("< f f")

    _INDEX = struct.Struct("< h")
    _TRIANGLE = struct.Struct("< h h h")
    # _UNK = struct.Struct("< e e e") # I assume that a half3 is the remaining value
    _UNK = struct.Struct("< 16s")  # I assume that bone weight is half

    _MIN_SIZE = _POSITION.size + _NORMAL.size + _UV.size
    #
    # _T39_VERTEX_SIZE = 48
    # _T37_VERTEX_SIZE = 32
    # _LOOKUP_VERTEX_SIZE = {
    #     39: _T39_VERTEX_SIZE,
    #     37: _T37_VERTEX_SIZE
    # }

    VERTEX_RESULTS = Tuple[List[TYPE_FLOAT3], List[TYPE_FLOAT3], List[TYPE_FLOAT2]]
    INDEX_RESULTS = List[TYPE_INT3]

    @classmethod
    def read_buffer(cls, stream: BinaryIO, vertex_count: int, format: int) -> VERTEX_RESULTS:
        vertexes = [cls._POSITION.unpack(stream.read(cls._POSITION.size)) for _ in range(vertex_count)]
        # stream.seek(cls._BONE.size * bone_count, 1)  # either a half or a byte/
        # stream.seek(cls._UNK.size, 1)  # a 3 half?
        if format == 39:
            stream.seek(cls._UNK.size * vertex_count, 1)
            # unk = [cls._UNK.unpack(stream.read(cls._UNK.size)) for _ in range(vertex_count)]
        normals = [cls._NORMAL.unpack(stream.read(cls._NORMAL.size)) for _ in range(vertex_count)]
        uvs = [cls._UV.unpack(stream.read(cls._UV.size)) for _ in range(vertex_count)]
        return vertexes, normals, uvs

    #
    # @classmethod
    # def read_39_buffer(cls, stream: BinaryIO, v_count: int) -> VERTEX_RESULTS:
    #     vertexes = [cls._POSITION.unpack(stream.read(cls._POSITION.size)) for _ in range(v_count)]
    #     stream.seek(4 * 4 * v_count, 1)
    #     normals = [cls._NORMAL.unpack(stream.read(cls._NORMAL.size)) for _ in range(v_count)]
    #     uvs = [cls._UV.unpack(stream.read(cls._UV.size)) for _ in range(v_count)]
    #     return vertexes, normals, uvs
    #
    # @classmethod
    # def read_37_buffer(cls, stream: BinaryIO, v_count: int) -> VERTEX_RESULTS:
    #     vertexes = [cls._POSITION.unpack(stream.read(cls._POSITION.size)) for _ in range(v_count)]
    #     # stream.seek(4 * 4 * v_count, 1) #
    #     normals = [cls._NORMAL.unpack(stream.read(cls._NORMAL.size)) for _ in range(v_count)]
    #     uvs = [cls._UV.unpack(stream.read(cls._UV.size)) for _ in range(v_count)]
    #     return vertexes, normals, uvs

    @classmethod
    def read_triangles(cls, stream: BinaryIO, index_count: int) -> INDEX_RESULTS:
        triangle_count = int(index_count / 3)
        return [cls._TRIANGLE.unpack(stream.read(cls._TRIANGLE.size)) for _ in range(triangle_count)]

    #
    # @classmethod
    # def read_vertex_buffer(cls, stream: BinaryIO, vertex_count: int, format: int) -> VERTEX_RESULTS:
    #     funcs = {
    #         39: cls.read_39_buffer,
    #         37: cls.read_37_buffer,
    #     }
    #     if format in funcs:
    #         return funcs[format](stream, vertex_count)
    #     else:
    #         raise KeyError(format)

    @classmethod
    def calculate_v_size(cls, bone_count: int = 0):
        return cls._MIN_SIZE + (cls._UNK.size if bone_count > 0 else 0)


@dataclass
class MslcChunk:
    header: MsclHeader
    names: List[MslcName]

    unk_format: int

    vertex_count: int
    vertex_data: bytes

    unk_c: int
    unk_h: int
    # textures: List[str]
    texture: str

    index_count: int
    index_data: bytes

    unk_d: int
    unk_e: int
    unk_f: int
    unk_g: int

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'MslcChunk':
        # name = chunk.name
        data = get_chunk_by_id(chunk.chunks, "DATA")
        # 0x5570 - 0x770 = 0x4E00 ! 48 BITS ?!
        # 0xe05d - 0xa39d = 0x3CC0 ~ 15552 ! 32 BITS ?!
        # 0x68337 - 0x0ad3 = 0x67864 ~ 424036 -> ??87.4?? I'll assume 88 ( (v:4850 b:25)
        # 171eb - 164cb = 0xD20 ~ 3360 -> 48 (v:70 b:1)
        # aa_destroyer_die_1.whm ~ 0x398fb - 0xb9b = 0x38D60 ~ 232800 ~ (/4850) = 48 bytes
        #       0x21e14 - 0xeef4 = 0x12F20 ~ 77600 ~ (/4850) = 16 bytes
        # aa_destroyer_get_up.whm ~ v:4846 ~ 0x68333 - 0xad3 = 0x67860 ~ 424032 ~ 87.5
        #       0x21cdb - 0xedfb = 0x12EE0 ~  77536 (/4846) ~ 16 and unk_d = 2323
        with BytesIO(data.data) as stream:
            header = MsclHeader.unpack(stream)
            if header.unk_d != 0:
                raise NotImplementedError("This file is prob not supported")

            bone_info = [MslcName.unpack(stream) for _ in range(header.name_count)]
            bone_count = len(bone_info)
            vertex_count, unk_format = struct.unpack("< L L", stream.read(8))
            # print(chunk.name, "\n","\t", "HEADER:", header.unk_a, header.flag_b, header.unk_c, header.unk_d, "~", buffer_format)
            v_size = VertexBufferTools.calculate_v_size(bone_count)
            vertex = stream.read(vertex_count * v_size)
            buffer = stream.read(8)
            unk_c, unk_h = struct.unpack("< L L", buffer)
            # textures = []
            # for _ in range(texture_count):
            buffer = stream.read(_NUM.size)
            size = _NUM.unpack(buffer)[0]
            name = stream.read(size)
            texture = name.decode("ascii")  # I have a strong feeling that meshes only have one texture...
            # textures.append(name)

            index_count = _NUM.unpack(stream.read(_NUM.size))[0]
            index = stream.read(index_count * VertexBufferTools._INDEX.size)
            unk_d, unk_e, unk_f, unk_g = struct.unpack("< L L L L", stream.read(4 * 4))

        return MslcChunk(header, bone_info, unk_format, vertex_count, vertex, unk_c, unk_h, texture, index_count, index,
                         unk_d, unk_e, unk_f, unk_g)


@dataclass
class WhmChunk:
    sshr: List[SshrChunk]
    msgr: MsgrChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WhmChunk':
        sshr = [SshrChunk.create(c) for c in get_all_chunks_by_id(chunky.chunks, 'SSHR')]
        msgr = MsgrChunk.create(get_chunk_by_id(chunky.chunks, "MSGR"))

        return WhmChunk(sshr, msgr)


# after MSCL texture name is the index count, multiply by two due to the size (short)?

def raw_dump():
    chunky.dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-chunky", [".whm"])


def print_meta(f: str):
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        whm = WhmChunk.create(chunky)
        meta = json.dumps(whm, indent=4, cls=EnhancedJSONEncoder)
        print(meta)


def write_position(stream: TextIO, x, y, z):
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

# 0x016c74 - 0x016814 = 0x460 ~ v:70 = 16 bytes

def write_obj(stream: TextIO, vertex: BinaryIO, indexes: BinaryIO, v_count: int, t_count: int,
              bone_count: int, name: str = None, v_offset: int = 0):
    if name:
        write_obj_name(stream, name)

    positions, normals, uvs = VertexBufferTools.read_buffer(vertex, v_count, bone_count)

    for position in positions:
        write_position(stream, *position)

    for normal in normals:
        write_normal(stream, *normal)

    for uv in uvs:
        write_uv2(stream, *uv)

    triangles = VertexBufferTools.read_triangles(indexes, t_count * 3)

    for triangle in triangles:
        write_tri(stream, *triangle,
                  v_offset=v_offset + 1)  # blender is 1th based NOT 0th based, so we add 1 to the offset


def write_mscl_as_obj(stream: TextIO, mscl: MslcChunk, v_offset: int = 0, name: str = None):
    if name:
        write_obj_name(stream, name)
    with BytesIO(mscl.vertex_data) as buffer:
        positions, normals, uvs = VertexBufferTools.read_buffer(buffer, mscl.vertex_count, mscl.unk_h)

    for position in positions:
        write_position(stream, *position)

    for normal in normals:
        write_normal(stream, *normal)

    for uv in uvs:
        write_uv2(stream, *uv)

    with BytesIO(mscl.vertex_data) as buffer:
        triangles = VertexBufferTools.read_triangles(buffer, mscl.index_count)

    for triangle in triangles:
        write_tri(stream, *triangle,
                  v_offset=v_offset + 1)  # blender is 1th based NOT 0th based, so we add 1 to the offset


def dump_obj(f: str, o: str):
    raise NotImplementedError()

    try:
        os.makedirs(dirname(o))
    except FileExistsError:
        pass

    with open(o + ".obj", "w") as obj:
        with open(f + ".meta") as m:
            meta = json.loads(m.read())

        with open(f + ".vert", "rb") as vertex:
            with open(f + ".tri", "rb") as index:
                write_obj(obj, meta['format'], vertex, index, meta['vertexes'], meta['triangles'])


def dump_all_obj(f: str):
    for root, file in walk_ext(f, ".vert"):
        full = join(root, file)
        full, _ = splitext(full)
        dump_obj(full, full)
#
#
# def dump_model(f: str, o: str):
#     print("" + f)
#     with open(f, "rb") as handle:
#         chunky = RelicChunky.unpack(handle)
#         whm = WhmChunk.create(chunky)
#
#         for i, mesh in enumerate(whm.msgr.submeshes):
#             name = whm.msgr.parts[i].name
#             full_o = join(o, name)
#             try:
#                 os.makedirs(dirname(full_o))
#             except FileExistsError:
#                 pass
#             print("\t" + full_o)
#
#             with open(full_o + ".vert", "wb") as v:
#                 v.write(mesh.vertex_data)
#             with open(full_o + ".tri", "wb") as t:
#                 t.write(mesh.index_data)
#             with open(full_o + ".meta", "w") as m:
#                 meta = {
#                     'vertexes': len(mesh.vertex_data) / 48,
#                     'triangles': len(mesh.index_data) / 6,
#                     'format': mesh.unk_format
#                 }
#                 m.write(json.dumps(meta, indent=4))


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
            except:
                pass
            # if not isinstance(e,(NotImplementedError,struct.error,UnicodeDecodeError)):
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
                # if mesh.buffer_format != 39:
                #     continue
                v_count = mesh.vertex_count
                # t_count = int(len(mesh.index_data) / 6)
                name = whm.msgr.parts[i].name
                # with BytesIO(mesh.vertex_data) as v_data:
                # with BytesIO(mesh.index_data) as i_data:
                write_mscl_as_obj(obj, mesh, v_offset, name)
                # write_obj(obj, v_data, i_data, v_count, t_count, len(mesh.names), name, v_offset=v_offset)
                v_offset += v_count

def dump_model(f: str, o: str):
    print("" + f)
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        whm = WhmChunk.create(chunky)
        try:
            os.makedirs(o)
        except FileExistsError:
            pass
        for i, mesh in enumerate(whm.msgr.submeshes):
            name = whm.msgr.parts[i].name
            with open(join(o,name+".obj"), "w") as obj:
                # if mesh.buffer_format != 39:
                #     continue
                # v_count = mesh.vertex_count
                # t_count = int(len(mesh.index_data) / 6)
                # with BytesIO(mesh.vertex_data) as v_data:
                # with BytesIO(mesh.index_data) as i_data:
                write_mscl_as_obj(obj, mesh, 0, name)
                # write_obj(obj, v_data, i_data, v_count, t_count, len(mesh.names), name, v_offset=v_offset)

def dump_all_model(f:str,o:str):
    for root, file in walk_ext(f, ".whm"):
        full = join(root, file)
        dump = full.replace(f, o, 1)
        dump, _ = splitext(dump)
        try:
            dump_model(full, dump)
        except Exception as e:
            print("\t", e)
            try:
                os.remove(dump)
            except:
                pass
            # if not isinstance(e,(NotImplementedError,struct.error,UnicodeDecodeError)):
            raise

if __name__ == "__main__":
    # print_meta(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm")
    # dump_model(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm",
    #            r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion\\")
    # dump_full_model(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard\troops\guardsmen.whm",
    #                 r"D:\Dumps\DOW I\whm-model\art\ebps\races\imperial_guard\troops\guardsmen.obj")

    # dump_all_chunky(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard\troops",
    #                 r"D:\Dumps\DOW I\whm-chunky\art\ebps\races\imperial_guard\troops", ["whm"])
    # dump_all_full_model(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard\troops", r"D:\Dumps\DOW I\whm-model\art\ebps\races\imperial_guard\troops")
    dump_all_model(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard\troops", r"D:\Dumps\DOW I\whm-model\art\ebps\races\imperial_guard\troops")

    # dump_all_full_model("D:\Dumps\DOW I\sga", "D:\Dumps\DOW I\whm-model")
    # dump_all_full_model(r"D:\Dumps\DOW I\sga\art\ebps\races", r"D:\Dumps\DOW I\whm-model\art\ebps\races")

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
