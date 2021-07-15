import enum
import json
import os
import shutil
import struct
from dataclasses import dataclass
from io import BytesIO
from os.path import join, splitext, dirname
from typing import BinaryIO, List, TextIO, Tuple, Iterable, Optional, Union, Any

from relic.chunky.data_chunk import DataChunk
from relic.chunky.dumper import dump_all_chunky
from relic.chunky.folder_chunk import FolderChunk
from relic.chunky.relic_chunky import RelicChunky
from relic.shared import walk_ext, EnhancedJSONEncoder

_UNK_STRUCT = struct.Struct("< L L")
_NUM = struct.Struct("< L")


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
        # the id is DATA not the type (alhough it is coincidentally, a ChunkType.Data)
        data: DataChunk = chunk.get_chunk(id="DATA", recursive=False)
        with BytesIO(data.data) as stream:
            buffer = stream.read(_NUM.size)
            count = _NUM.unpack(buffer)[0]
            parts = [MsgrName.unpack(stream) for _ in range(count)]
        submeshes = [MslcChunk.create(mscl) for mscl in chunk.get_chunks(id="MSLC")]

        return MsgrChunk(parts, submeshes)


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


class MslcBlockFormat(enum.Enum):
    Vertex32 = enum.auto()  # = 37
    Vertex48 = enum.auto()  # = 39

    # Oh boy; IDK how many 'texture' classes there are but there are enough
    Texture = enum.auto()


    @classmethod
    def from_code(cls, code: int):
        if code <= 6:
            return MslcBlockFormat.Texture

        lookup = {
            37: MslcBlockFormat.Vertex32,
            39: MslcBlockFormat.Vertex48,
        }
        value = lookup.get(code)
        if value:
            return value
        raise NotImplementedError(code)

    def vertex_buffer_size(self) -> int:
        size = {
            MslcBlockFormat.Vertex48: 48,
            MslcBlockFormat.Vertex32: 32,
        }
        val = size.get(self)
        if val is None:
            raise KeyError(f"'{val}' is not a Vertex Buffer Type")
        return val


@dataclass
class VertexMsclBlock:
    format: MslcBlockFormat
    count: int
    vertex_buffer: bytes


@dataclass
class TextureMsclSubBlock:
    name: str
    count: int
    index_buffer: bytes
    zero: int


@dataclass
class TextureMsclBlock:
    format: MslcBlockFormat
    zero: int
    blocks: List[TextureMsclSubBlock]
    info: List[Tuple[int, int]]

    unk_a: int
    unk_b: int
    unk_c: int


MslcBlock = Union[
    VertexMsclBlock,
    TextureMsclBlock
]


class MslcBlockUtil:
    @classmethod
    def unpack(cls, stream: BinaryIO) -> MslcBlock:
        def read_index_block() -> TextureMsclSubBlock:
            name_size = _NUM.unpack(stream.read(_NUM.size))[0]
            name = stream.read(name_size).decode("ascii")
            index_size = _NUM.unpack(stream.read(_NUM.size))[0]
            i_buffer = stream.read(index_size * 2)
            return TextureMsclSubBlock(name, index_size, i_buffer, count)

        block_header = stream.read(8)
        count, code = struct.unpack("< L L", block_header)
        try:
            f = MslcBlockFormat.from_code(code)
        except ValueError:
            raise NotImplementedError(code)

        if f == MslcBlockFormat.Texture:
            texture_count = code
            subs = []
            infos = []
            INFO = struct.Struct("< l l")
            for _ in range(texture_count):
                sub = read_index_block()

                buffer = stream.read(INFO.size)
                info = INFO.unpack(buffer)

                subs.append(sub)
                infos.append(info)

            UNK = struct.Struct("< l l l")

            buffer = stream.read(UNK.size)
            unks = UNK.unpack(buffer)

            return TextureMsclBlock(f, count, subs, infos, *unks)

        try:
            buffer_size = f.vertex_buffer_size()
            v_buffer = stream.read(buffer_size * count)
            return VertexMsclBlock(f, count, v_buffer)
        except KeyError:
            pass

        raise NotImplementedError(code)


@dataclass
class MslcChunk:
    V_SIZE_39 = 48
    V_SIZE_37 = 32
    V_SIZE = {39: V_SIZE_39, 37: V_SIZE_37}
    I_SIZE = 2

    header: MsclHeader
    names: List[MslcName]

    blocks: List[MslcBlock]

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'MslcChunk':
        data: DataChunk = chunk.get_chunk(id="DATA", recursive=False)

        with BytesIO(data.data) as stream:
            header = MsclHeader.unpack(stream)
            names = [MslcName.unpack(stream) for _ in range(header.name_count)]

            blocks = []

            start = stream.tell()
            stream.seek(0, 2)
            end = stream.tell()
            stream.seek(start)

            while stream.tell() != end:
                block = MslcBlockUtil.unpack(stream)
                blocks.append(block)

            return MslcChunk(header, names, blocks)


@dataclass
class WhmChunk:
    sshr: List[SshrChunk]
    msgr: MsgrChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WhmChunk':
        sshr = [SshrChunk.create(c) for c in chunky.get_chunks(id='SSHR')]
        msgr = MsgrChunk.create(chunky.get_chunk(id="MSGR"))
        return WhmChunk(sshr, msgr)


def raw_dump():
    dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-chunky", [".whm"])


def print_meta(f: str):
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        whm = WhmChunk.create(chunky)
        meta = json.dumps(whm, indent=4, cls=EnhancedJSONEncoder)
        print(meta)



Float4 = Tuple[float, float, float, float]
Float3 = Tuple[float, float, float]
Float2 = Tuple[float, float]
_Float4 = struct.Struct("< f f f f")
_Float3 = struct.Struct("< f f f")
_Float2 = struct.Struct("< f f")

Short3 = Tuple[int, int, int]
_Short3 = struct.Struct("< h h h")


def read_float4_list(vertex_buffer: BinaryIO, vertex_count: int) -> Iterable[Float4]:
    for _ in range(vertex_count):
        buffer = vertex_buffer.read(_Float4.size)
        value = _Float4.unpack(buffer)
        yield value


def read_float3_list(vertex_buffer: BinaryIO, vertex_count: int) -> Iterable[Float3]:
    for _ in range(vertex_count):
        buffer = vertex_buffer.read(_Float3.size)
        value = _Float3.unpack(buffer)
        yield value


def read_float2_list(vertex_buffer: BinaryIO, vertex_count: int) -> Iterable[Float2]:
    for _ in range(vertex_count):
        buffer = vertex_buffer.read(_Float2.size)
        value = _Float2.unpack(buffer)
        yield value


def read_short3_list(index_buffer: BinaryIO, index_count):
    for _ in range(index_count):
        buffer = index_buffer.read(_Short3.size)
        value = _Short3.unpack(buffer)
        yield value


def seek_float4_list(vertex_buffer: BinaryIO, vertex_count: int):
    vertex_buffer.seek(vertex_count * _Float3.size, 1)


def seek_float3_list(vertex_buffer: BinaryIO, vertex_count: int):
    vertex_buffer.seek(vertex_count * _Float3.size, 1)


def seek_float2_list(vertex_buffer: BinaryIO, vertex_count: int):
    vertex_buffer.seek(vertex_count * _Float2.size, 1)


def read_write_positions(stream: TextIO, vertex: BinaryIO, count: int):
    for pos in read_float3_list(vertex, count):
        write_position(stream, *pos)


def read_write_normals(stream: TextIO, vertex: BinaryIO, count: int):
    for normal in read_float3_list(vertex, count):
        write_normal(stream, *normal)


def read_write_uvs(stream: TextIO, vertex: BinaryIO, count: int):
    for normal in read_float2_list(vertex, count):
        write_uv(stream, *normal)


def read_write_triangles(stream: TextIO, index: BinaryIO, count: int, offset: int = 0):
    for tri in read_short3_list(index, count):
        write_tri(stream, *tri, v_offset=offset, zero_based=True)


_BufferSize32 = 37
_BufferSize48 = 39


def write_obj(stream: TextIO, chunk: MslcChunk, name: str = None, v_offset: int = 0) -> int:
    if name:
        write_obj_name(stream, name)

    v_local_offset = 0

    vertex_blocks = [block for block in chunk.blocks if isinstance(block, VertexMsclBlock)]
    index_blocks = [block for block in chunk.blocks if isinstance(block, TextureMsclBlock)]

    for block in vertex_blocks:
        if block.format not in [MslcBlockFormat.Vertex48, MslcBlockFormat.Vertex32]:
            raise NotImplementedError(block.format)

        with BytesIO(block.vertex_buffer) as vertex:
            v_count = block.count

            read_write_positions(stream, vertex, v_count)

            if block.format in [MslcBlockFormat.Vertex48]:
                seek_float4_list(vertex, v_count)

            read_write_normals(stream, vertex, v_count)
            read_write_uvs(stream, vertex, v_count)

        v_local_offset += v_count

    for block in index_blocks:
        for sub in block.blocks:
            with BytesIO(sub.index_buffer) as index:
                i_count = int(sub.count / 3)
                read_write_triangles(stream, index, i_count, v_offset)
                # return  + v_local_offset
        # else:

    return v_local_offset
    # for _ in range(t_count):
    #     buffer = indexes.read(_TRI.size)
    #     a, b, c = _TRI.unpack(buffer)
    #     write_tri(stream, a, b, c,
    #               v_offset=v_offset + 1)  # blender is 1th based NOT 0th based, so we add 1 to the offset


#
# def dump_obj(f: str, o: str):
#     try:
#         os.makedirs(dirname(o))
#     except FileExistsError:
#         pass
#
#     with open(o + ".obj", "w") as obj:
#         with open(f + ".meta") as m:
#             meta = json.loads(m.read())
#
#         with open(f + ".vert", "rb") as vertex:
#             with open(f + ".tri", "rb") as index:
#                 write_obj(obj, vertex, index, meta['vertexes'], meta['triangles'])
#
#
# def dump_all_obj(f: str):
#     for root, file in walk_ext(f, ".vert"):
#         full = join(root, file)
#         full, _ = splitext(full)
#         dump_obj(full, full)


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
#                 m.write(json.dumps({'vertexes': len(mesh.vertex_data) / 48, 'triangles': len(mesh.index_data) / 6}))


def dump_all_model(f: str, o: str, full: bool = True):
    for root, file in walk_ext(f, ".whm"):
        full_path = join(root, file)
        dump = full_path.replace(f, o, 1)
        dump, _ = splitext(dump)
        dump += ".obj"
        try:
            dump_model(full_path, dump, full)
        except (NotImplementedError, struct.error, UnicodeDecodeError, Exception) as e:
            print("\t", e)
            try:
                os.remove(dump)
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
            shutil.move(full, dump)

            # raise


def dump_model(f: str, o: str, full: bool = True):
    print(f + "\t=>\t" + o)
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        try:
            whm = WhmChunk.create(chunky)
        except NotImplementedError as e:
            if e.args[0] == 55:
                print("Skipping funky vertex buffer?")
                raise
                return
            elif e.args[0] == 48:
                print("Found an invalid index buffer?")
                raise
                return
            else:
                raise

        if full:
            try:
                os.makedirs(dirname(o))
            except FileExistsError:
                pass
            with open(o, "w") as obj:
                v_offset = 0
                for i, mesh in enumerate(whm.msgr.submeshes):
                    # if mesh.unk_buffer_format != 39:
                    #     continue
                    # v_count = int(len(mesh.vertex_data) / 48)
                    # t_count = int(len(mesh.index_data) / 6)
                    # t_count = mesh.index_count
                    name = whm.msgr.parts[i].name
                    v_offset += write_obj(obj, mesh, name, v_offset=v_offset)
        else:
            o, _ = splitext(o)
            try:

                os.makedirs(o)
            except FileExistsError:
                pass
            for i, mesh in enumerate(whm.msgr.submeshes):
                name = whm.msgr.parts[i].name
                o_part = join(o, name + ".obj")
                with open(o_part, "w") as obj:
                    # if mesh.unk_buffer_format != 39:
                    #     continue
                    # v_count = int(len(mesh.vertex_data) / 48)
                    # t_count = int(len(mesh.index_data) / 6)
                    # t_count = mesh.index_count
                    # v_offset += \
                    write_obj(obj, mesh, name)
                # v_offset += mesh.vertex_count
                # with BytesIO(mesh.vertex_data) as v_data:
                #     with BytesIO(mesh.index_data) as i_data:
                #
                #         write_obj(obj, v_data, i_data, v_count, t_count, name, v_offset=v_offset)
                #         v_offset += v_count


if __name__ == "__main__":
    # raw_dump()
    # exit()
    # print_meta(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm")
    # dump_model(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm",
    #            r"D:\Dumps\DOW I\whm-model\art\ebps\races\chaos\troops\aspiring_champion\\")
    # dump_full_model(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard\troops\guardsmen.whm",
    #                 r"D:\Dumps\DOW I\whm-model\art\ebps\races\imperial_guard\troops\guardsmen.obj")

    dump_all_model(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-model", True)

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
