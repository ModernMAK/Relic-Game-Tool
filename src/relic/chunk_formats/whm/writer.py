from io import BytesIO
from os.path import split, splitext, join, basename
from typing import TextIO, Tuple, Optional, Iterable

from relic.chunk_formats.whm.msgr_chunk import MsgrChunk
from relic.chunk_formats.whm.mslc_chunk import MslcChunk, TextureMsclBlock, VertexMsclBlock, MslcBlockFormat
from relic.file_formats.mesh_io import MeshReader
from relic.file_formats.wavefront_obj import ObjWriter, MtlWriter


def get_name_from_texture_path(path: str) -> str:
    path = basename(path)
    path, _ = splitext(path)
    return path


# writes the matlib name into an OBJ file
# the associated mtl should be generated appropriately
# for convienience, the path to the mtl is returned
def write_matlib_name(stream: TextIO, obj_path: str) -> str:
    dirname, filename = split(obj_path)
    filename, _ = splitext(filename)

    filename += ".mtl"

    matlib_writer = ObjWriter(stream)
    matlib_writer.write_material_library(filename)

    return join(dirname, filename)


def write_mslc_to_obj(stream: TextIO, chunk: MslcChunk, name: str = None, v_offset: int = 0) -> int:
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
            tex_name = get_name_from_texture_path(sub.name)
            writer.write_use_material(tex_name)

            with BytesIO(sub.index_buffer) as index:
                reader = MeshReader(index)
                triangles = int(sub.count / 3)

                for tri in reader.read_short3(triangles):
                    writer.write_index_face(*tri, offset=v_offset, zero_based=True)

    return v_local_offset


def write_msgr_to_obj(stream: TextIO, chunk: MsgrChunk, obj_path: str = None) -> Tuple[int, Optional[str]]:
    matlib_path = write_matlib_name(stream, obj_path) if obj_path else None

    v_offset = 0
    for i, mesh in enumerate(chunk.sub_meshes):
        name = chunk.parts[i].name
        v_offset += write_mslc_to_obj(stream, mesh, name, v_offset=v_offset)

    return v_offset, matlib_path


def fetch_textures_from_mslc(chunk: MslcChunk) -> Iterable[str]:
    for block in chunk.blocks:
        if isinstance(block, TextureMsclBlock):
            block: TextureMsclBlock
            for sub_block in block.blocks:
                yield sub_block.name  # this is the texture


def fetch_textures_from_msgr(chunk: MsgrChunk) -> Iterable[str]:
    for sub_chunk in chunk.sub_meshes:
        for texture in fetch_textures_from_mslc(sub_chunk):
            yield texture


def write_msgr_to_mtl(stream: TextIO, chunk: MsgrChunk, texture_root: str = None, texture_ext: str = None):
    texture_ext = texture_ext or ""
    textures = [t for t in fetch_textures_from_msgr(chunk)]
    textures = set(textures)
    mtl_writer = MtlWriter(stream)
    for texture in textures:
        tex_name = get_name_from_texture_path(texture)
        mtl_writer.write_default_texture(tex_name)
        full_texture = join(texture_root, texture) if texture_root else texture
        mtl_writer.write_texture_diffuse(full_texture + texture_ext)


def write_obj_mtl(dest: str, chunk: MsgrChunk, texture_root: str = None, texture_ext: str = None):
    with open(dest, "w") as obj_handle:
        _, mtl = write_msgr_to_obj(obj_handle, chunk, dest)
    with open(mtl, "w") as mtl_handle:
        write_msgr_to_mtl(mtl_handle, chunk, texture_root, texture_ext)
