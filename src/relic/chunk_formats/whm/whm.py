import json
import os
import shutil
import struct
from dataclasses import dataclass
from io import BytesIO
from os.path import join, splitext, dirname, split
from typing import BinaryIO, List, TextIO

from relic.chunk_formats.whm.msgr_chunk import MsgrChunk
from relic.chunk_formats.whm.mslc_chunk import MslcChunk, MslcBlockFormat, VertexMsclBlock, TextureMsclBlock
from relic.chunk_formats.whm.shared import num_layout
from relic.chunk_formats.whm.sshr_chunk import SshrChunk
from relic.chunky import DataChunk, RelicChunky
from relic.chunky.dumper import dump_all_chunky
from relic.file_formats.mesh_io import MeshReader
from relic.file_formats.wavefront_obj import ObjWriter
from relic.shared import walk_ext, EnhancedJSONEncoder


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
                writer.write_vertex_position(*pos)

            if block.format in [MslcBlockFormat.Vertex48]:
                reader.seek_float4(v_count)

            for normal in reader.read_float3(v_count):
                writer.write_vertex_normal(*normal)

            for uv in reader.read_float2(v_count):
                writer.write_vertex_uv(*uv)

        v_local_offset += v_count

    for block in index_blocks:
        for sub in block.blocks:
            writer.write_use_material(sub.name)
            with BytesIO(sub.index_buffer) as index:
                reader = MeshReader(index)
                triangles = int(sub.count / 3)

                for tri in reader.read_short3(triangles):
                    writer.write_index_face(*tri, offset=v_offset, zero_based=True)

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

    return join(dirname, filename)


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
    name: str
    index: int
    floats: List[int]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'SkelBone':
        buffer = stream.read(num_layout.size)
        name_size = num_layout.unpack(buffer)[0]
        name = stream.read(name_size)
        data = stream.read(32)
        args = struct.unpack("< l 7f", data)

        return SkelBone(name, args[0], args[1:])


@classmethod
class SkelChunk:
    # This chunk is super easy
    bones: List[SkelBone]

    def unpack(self, chunk: DataChunk) -> 'SkelChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(num_layout.size)
            bone_size = num_layout.unpack(buffer)[0]
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
