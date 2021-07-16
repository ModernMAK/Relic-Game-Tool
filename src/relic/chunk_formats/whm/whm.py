import enum
import json
import os
import shutil
import struct
from dataclasses import dataclass
from io import BytesIO
from os.path import join, splitext, dirname, basename, split
from typing import BinaryIO, List, TextIO, Tuple, Union

from relic.chunky.data_chunk import DataChunk
from relic.chunky.dumper import dump_all_chunky
from relic.chunky.folder_chunk import FolderChunk
from relic.chunky.relic_chunky import RelicChunky
from relic.file_formats.mesh_io import MeshReader
from relic.file_formats.obj import ObjWriter
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
    sub_meshes: List['MslcChunk']

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


_BufferSize32 = 37
_BufferSize48 = 39


def write_obj(stream: TextIO, chunk: MslcChunk, name: str = None, v_offset: int = 0) -> int:
    writer = ObjWriter(stream)
    v_local_offset = 0

    if name:
        writer.write_object_name(name)

    vertex_blocks = [block for block in chunk.blocks if isinstance(block, VertexMsclBlock)]
    index_blocks = [block for block in chunk.blocks if isinstance(block, TextureMsclBlock)]

    for block in vertex_blocks:
        if block.format not in [MslcBlockFormat.Vertex48, MslcBlockFormat.Vertex32]:
            raise NotImplementedError(block.format)

        with BytesIO(block.vertex_buffer) as vertex:
            reader = MeshReader(vertex)
            v_count = block.count

            for pos in reader.read_float3(v_count):
                writer.write_position(*pos)

            if block.format in [MslcBlockFormat.Vertex48]:
                reader.seek_float4(v_count)

            for normal in reader.read_float3(v_count):
                writer.write_normal(*normal)

            for uv in reader.read_float2(v_count):
                writer.write_uv(*uv)

        v_local_offset += v_count

    for block in index_blocks:
        for sub in block.blocks:
            writer.write_use_material(sub.name)
            with BytesIO(sub.index_buffer) as index:
                reader = MeshReader(index)
                triangles = int(sub.count / 3)

                for tri in reader.read_short3(triangles):
                    writer.write_face(*tri, offset=v_offset, zero_based=True)

    return v_local_offset


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


# writes the matlib name into an OBJ file
# the associated mtl should be generated appropriately
# for convienience, the path to the mtl is returned
def write_matlib_name(obj: TextIO, obj_path: str) -> str:
    dirname, filename = split(obj_path)
    filename, _ = splitext(filename)

    filename += ".mtl"

    matlib_writer = ObjWriter(obj)
    matlib_writer.write_material_library(filename)

    return join(dirname,filename)


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
            elif e.args[0] == 48:
                print("Found an invalid index buffer?")
                raise
            else:
                raise

        if full:
            try:
                os.makedirs(dirname(o))
            except FileExistsError:
                pass
            with open(o, "w") as obj:
                write_matlib_name(obj, o)
                v_offset = 0
                for i, mesh in enumerate(whm.msgr.sub_meshes):
                    name = whm.msgr.parts[i].name
                    v_offset += write_obj(obj, mesh, name, v_offset=v_offset)
        else:
            o, _ = splitext(o)
            try:

                os.makedirs(o)
            except FileExistsError:
                pass
            for i, mesh in enumerate(whm.msgr.sub_meshes):
                name = whm.msgr.parts[i].name
                o_part = join(o, name + ".obj")
                with open(o_part, "w") as obj:
                    write_matlib_name(obj, o_part)
                    write_obj(obj, mesh, name)

@dataclass
class SkelBone:
     # This chunk is also super easy
    name:str
    index:int
    floats:List[int]

    @classmethod
    def unpack(cls, stream:BinaryIO) -> 'SkelBone':
        buffer = stream.read(_NUM.size)
        name_size = _NUM.unpack(buffer)[0]
        name = stream.read(name_size)
        data = stream.read(32)
        args = struct.unpack("< l 7f", data)

        return SkelBone(name,args[0],args[1:])

@classmethod
class SkelChunk:
     # This chunk is super easy
    bones:List[SkelBone]

    def unpack(self, chunk:DataChunk) -> 'SkelChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(_NUM.size)
            bone_size = _NUM.unpack(buffer)[0]
            bones = [SkelBone.unpack(stream) for _ in range(bone_size)]
        return SkelChunk(bones)






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
