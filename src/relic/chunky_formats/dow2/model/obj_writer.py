from enum import Enum
from os.path import split, splitext, join
from typing import TextIO, Iterable, List, Tuple

from relic.chunky_formats.dow2.model.model import MtrlChunk, ModelChunky, TrimDataChunk, VarChunk, TextureVar
from relic.file_formats.wavefront_obj import ObjWriter, MtlWriter


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


def write_trim_data_to_obj(stream: TextIO, chunk: TrimDataChunk, name: str = None, v_offset: int = 0,
                           validate: bool = True, axis_fix: bool = True) -> int:
    writer = ObjWriter(stream)

    stream.write("\n# Object\n")
    # I couldn't find a good name for the sub-parts, so I make do with the material name (stripping the excess relic.blah.blah)
    _, name = name or chunk.material_name.rsplit(".", maxsplit=1)
    # if name:
    writer.write_object_name(name)

    stream.write("\t# Vertexes\n")
    has_norm = chunk.vertexes[0].normal is not None
    has_uv = chunk.vertexes[0].uv is not None
    for v in chunk.vertexes:
        stream.write("\t")
        writer.write_vertex_position(*v.position)
        if has_norm:
            stream.write("\t")
            writer.write_vertex_normal(*v.normal)
        stream.write("\t")
        if has_uv:
            writer.write_vertex_uv(*v.uv)
            stream.write("\n")

    stream.write("# Material\n")
    writer.write_use_material(chunk.material_name)

    stream.write("\t# Indexes\n")
    for index in range(int(len(chunk.indexes) // 3)):
        stream.write("\t")
        tri = chunk.indexes[3 * index], chunk.indexes[3 * index + 1], chunk.indexes[3 * index + 2]
        writer.write_index_face(*tri, offset=v_offset, zero_based=True, normal=has_norm, uv=has_uv)

    return len(chunk.vertexes)


def write_mtllib_to_obj(stream: TextIO, mtl_path: str):
    matlib_writer = ObjWriter(stream)
    matlib_writer.write_material_library(mtl_path)


def write_model_to_obj(stream: TextIO, chunk: ModelChunky) -> int:
    v_offset = 0
    for mgrp_mesh in chunk.modl.mesh.mgrp.mesh:
        for imdg_mesh in mgrp_mesh.imdg.mesh:
            for mesh in imdg_mesh.imod.mesh:
                v_offset += write_trim_data_to_obj(stream, mesh.trim.data, v_offset=v_offset)

    return v_offset


class TextureType(Enum):
    Team = "teamTex"
    Dirt = "dirtTex"
    BadgeSecondary = "badge2Tex"
    BadgePrimary = "badge1Tex"
    Normal = "normalMap"
    Diffuse = "diffuseTex"
    Emissive = "emissiveTex"
    Specular = "specularTex"
    Occlusion = "occlusionTex"
    Gloss = "glossTex"

    # TODO check if normal and specular exist when these are present
    DamageNormal = "damageNormalTex"
    DamageSpecular = "damageSpecTex"
    DamageDiffuse = "damageDiffuseTex"
    Scar = "scarTexture"
    Overlay = 'overlayTex'

    CoarseNormal = 'normalMapCoarseTex'
    FineNormal = 'normalMapFineTex'

    WaterTurbulenceMask = 'waterTurbulenceMaskTex'
    WaterColor = 'waterColourTex'
    WaterTurbulence = 'waterTurbulenceTex'
    WaterFoamNormal = 'normalMapFoamTex'

    # Prob shouldn't do this; not as obvious as the Version Enum's
    #   This performs a VALUE comparison against the enum
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        else:
            return super.__eq__(self, other)

    def __ne__(self, other):
        return not self == other


def fetch_textures_from_dow2_unit(chunks: List[VarChunk]) -> Iterable[Tuple[TextureType, str]]:
    for chunk in chunks:
        if not isinstance(chunk.property_data, TextureVar):
            continue
        type = TextureType(chunk.property_name)
        path = chunk.property_data.texture
        yield type, path


class SupportedShaders(Enum):
    Dow2_Unit = "dow2_unit"

    # This is somehow different from the other? Maybe UV Offset actually matters for this one?
    #   Cherry on top; this seems to only be used by classes using
    Dow2_Unit_2Uv = "dow2_unit_2uv"

    # Prob shouldn't do this; not as obvious as the Version Enum's
    #   This performs a VALUE comparison against the enum
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        else:
            return super.__eq__(self, other)

    def __ne__(self, other):
        return not self == other


def fetch_textures_from_mtrl(chunk: MtrlChunk) -> Iterable[Tuple[TextureType, str]]:
    if chunk.info.shader_name in [SupportedShaders.Dow2_Unit, SupportedShaders.Dow2_Unit_2Uv]:
        return fetch_textures_from_dow2_unit(chunk.var)
    else:
        return []  # I kinda wanted to start
        # return fetch_textures_from_dow2_unit(chunk.var)
        # raise NotImplementedError(chunk.info.shader_name)


def write_mtrl_to_mtl(stream: TextIO, chunk: MtrlChunk, texture_root: str = None, texture_ext: str = None, force_valid: bool = True) -> int:
    texture_ext = texture_ext or ""
    start = stream.tell()
    mtl_writer = MtlWriter(stream)
    mtl_writer.write_default_texture(chunk.header.name)
    for tex_type, texture in fetch_textures_from_mtrl(chunk):
        full_texture = join(texture_root, texture) if texture_root else texture
        full_texture += texture_ext
        if force_valid:
            d, b = split(full_texture)
            full_texture = join(d, b.replace(" ", "_"))
        # Unsupported
        if tex_type == TextureType.Team:
            mtl_writer.write_unsupported_texture(full_texture, "Team")
        elif tex_type == TextureType.Dirt:
            mtl_writer.write_unsupported_texture(full_texture, "Dirt")
        elif tex_type == TextureType.BadgePrimary:
            mtl_writer.write_unsupported_texture(full_texture, "Badge 1")
        elif tex_type == TextureType.BadgeSecondary:
            mtl_writer.write_unsupported_texture(full_texture, "Badge 2")
        elif tex_type == TextureType.Emissive:
            mtl_writer.write_texture_emissive(full_texture)
        elif tex_type == TextureType.Occlusion:
            mtl_writer.write_unsupported_texture(full_texture, "Occlusion")
        elif tex_type == TextureType.Gloss:
            mtl_writer.write_unsupported_texture(full_texture, "Gloss")
        elif tex_type == TextureType.DamageNormal:
            mtl_writer.write_unsupported_texture(full_texture, "Damage Normal")
        elif tex_type == TextureType.DamageSpecular:
            mtl_writer.write_unsupported_texture(full_texture, "Damage Specular")
        elif tex_type == TextureType.DamageDiffuse:
            mtl_writer.write_unsupported_texture(full_texture, "Damage Diffuse")
        elif tex_type == TextureType.Scar:
            mtl_writer.write_unsupported_texture(full_texture, "Scar")
        elif tex_type == TextureType.Overlay:
            mtl_writer.write_unsupported_texture(full_texture, "Overlay")
        elif tex_type == TextureType.WaterTurbulence:
            mtl_writer.write_unsupported_texture(full_texture, "Water Turbulence")
        elif tex_type == TextureType.WaterTurbulenceMask:
            mtl_writer.write_unsupported_texture(full_texture, "Water Turbulence Mask")
        elif tex_type == TextureType.WaterFoamNormal:
            mtl_writer.write_unsupported_texture(full_texture, "Water Foam Normal")
        elif tex_type == TextureType.WaterColor:
            mtl_writer.write_unsupported_texture(full_texture, "Water Color")
        elif tex_type == TextureType.CoarseNormal:
            mtl_writer.write_unsupported_texture(full_texture, "Coarse Normal")
        elif tex_type == TextureType.FineNormal:
            mtl_writer.write_unsupported_texture(full_texture, "Fine Normal")
        elif tex_type == TextureType.FineNormal:
            mtl_writer.write_unsupported_texture(full_texture, "Fine Normal")
        # Supported
        elif tex_type == TextureType.Diffuse:
            mtl_writer.write_texture_diffuse(full_texture)
            mtl_writer.write_texture_alpha(full_texture)
        elif tex_type == TextureType.Normal:
            mtl_writer.write_texture_normal(full_texture)
        elif tex_type == TextureType.Specular:
            mtl_writer.write_texture_specular(full_texture)
        else:
            raise NotImplementedError(tex_type)
    return stream.tell() - start


def write_model_to_mtl(stream: TextIO, chunk: ModelChunky, texture_root: str, texture_ext: str) -> int:
    written = 0
    for mtrl in chunk.modl.mtrls:
        written += write_mtrl_to_mtl(stream, mtrl, texture_root, texture_ext)
    return written


def dump_model_as_obj(chunk: ModelChunky, mtl_path: str, obj_stream: TextIO, mtl_stream: TextIO, texture_root: str, texture_ext: str):
    write_mtllib_to_obj(obj_stream, mtl_path)
    write_model_to_obj(obj_stream, chunk)

    write_model_to_mtl(mtl_stream, chunk, texture_root, texture_ext)


# def write_obj_mtl(dest: str, chunk: MsgrChunk, texture_root: str = None, texture_ext: str = None):
#     with open(dest, "w") as obj_handle:
#         _, mtl = write_msgr_to_obj(obj_handle, chunk, dest)
#     with open(mtl, "w") as mtl_handle:
#         write_msgr_to_mtl(mtl_handle, chunk, texture_root, texture_ext)
def write_model(output_path: str, model: ModelChunky):
    obj_path = output_path + ".obj"
    mtl_path = output_path + ".mtl"
    with open(obj_path, "w") as obj_file:
        with open(mtl_path, "w") as mtl_file:
            dump_model_as_obj(model, mtl_path, obj_file, mtl_file, None, ".dds")
