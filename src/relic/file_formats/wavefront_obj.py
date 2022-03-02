from typing import TextIO, Iterable, Tuple

from relic.file_formats.mesh_io import Float3, Float2


class ObjWriter:
    def __init__(self, stream: TextIO):
        self._stream = stream

    def __write_index(self, code: str, *indexes: int, offset: int = 0, zero_based: bool = False,
                      flip_winding: bool = False, normal=True, uv=True):
        if flip_winding:
            j = len(indexes)
            indexes = [indexes[j - i - 1] for i in range(j)]
        indexes = [i + offset + (1 if zero_based else 0) for i in indexes]

        repeat = 1 + (1 if normal else 0) + (1 if uv else 0)
        if normal and uv:
            part = "{}/{}/{}"
        elif uv:
            part = "{}/{}"
        elif normal:
            part = "{}//{}"
        else:
            part = "{}"

        parts = [part.format(*[i for _ in range(repeat)]) for i in indexes]
        line = code + " " + " ".join(parts) + "\n"
        return self._stream.write(line)

    def __write_name(self, code: str, name: str):
        line = f"{code} {name}\n"
        return self._stream.write(line)

    # Prettify
    def write_blank(self):
        return self._stream.write("\n")

    # Vertex Info
    def write_vertex_position(self, x: float, y: float, z: float) -> int:
        line = 'v %f %f %f\n' % (x, y, z)
        return self._stream.write(line)

    def write_vertex_positions(self, positions: Iterable[Float3]) -> int:
        return sum(self.write_vertex_position(*pos) for pos in positions)

    def write_vertex_uv(self, u: float, v: float):
        line = 'vt %f %f\n' % (u, v)
        return self._stream.write(line)

    def write_vertex_uvs(self, uvs: Iterable[Float2]) -> int:
        return sum(self.write_vertex_uv(*uv) for uv in uvs)

    def write_vertex_normal(self, x: float, y: float, z: float):
        line = 'vn %f %f %f\n' % (x, y, z)
        return self._stream.write(line)

    def write_vertex_normals(self, normals: Iterable[Float3]) -> int:
        return sum(self.write_vertex_normal(*normal) for normal in normals)

    # Index Info
    def write_index_face(self, *indexes: int, offset: int = 0, zero_based: bool = False, flip_winding: bool = False, normal: bool = True, uv: bool = True):
        return self.__write_index("f", *indexes, offset=offset, zero_based=zero_based, flip_winding=flip_winding, normal=normal, uv=uv)

    def write_index_faces(self, *indexes: Tuple[int, int, int], offset: int = 0, zero_based: bool = False, flip_winding: bool = False, normal: bool = True, uv: bool = True):
        return sum(self.write_index_face(*index, offset=offset, zero_based=zero_based, flip_winding=flip_winding, normal=normal, uv=uv) for index in indexes)

    def write_index_line(self, *indexes: int, offset: int = 0, zero_based: bool = False, normal: bool = True, uv: bool = True):
        return self.__write_index("l", *indexes, offset=offset, zero_based=zero_based, normal=normal, uv=uv)

    def write_index_lines(self, *indexes: Tuple[int, int], offset: int = 0, zero_based: bool = False, normal: bool = True, uv: bool = True):
        return sum(self.write_index_line(*index, offset=offset, zero_based=zero_based, normal=normal, uv=uv) for index in indexes)

    def write_index_point(self, *indexes: int, offset: int = 0, zero_based: bool = False, normal: bool = True, uv: bool = True):
        return self.__write_index("p", *indexes, offset=offset, zero_based=zero_based, normal=normal, uv=uv)

    def write_index_points(self, *indexes: Tuple[int, int], offset: int = 0, zero_based: bool = False, normal: bool = True, uv: bool = True):
        return sum(self.write_index_point(*index, offset=offset, zero_based=zero_based, normal=normal, uv=uv) for index in indexes)

    # Structure Info
    def write_group_name(self, name: str) -> int:
        return self.__write_name("g", name)

    def write_object_name(self, name: str) -> int:
        return self.__write_name("o", name)

    # Material
    def write_material_library(self, name: str) -> int:
        return self.__write_name("mtllib", name)

    def write_use_material(self, name: str) -> int:
        return self.__write_name("usemtl", name)


class MtlWriter:
    def __init__(self, stream: TextIO):
        self._stream = stream

    # Helpers
    def __write_int(self, code: str, value: int) -> int:
        line = "\t%s %i\n" % (code, value)
        return self._stream.write(line)

    def __write_float(self, code: str, value: float) -> int:
        line = "\t%s %f\n" % (code, value)
        return self._stream.write(line)

    def __write_color(self, code: str, color: Float3) -> int:
        line = "\t%s %f %f %f\n" % (code, color[0], color[1], color[2])
        return self._stream.write(line)

    def __write_texture(self, code: str, path: str, prefix: str = "map_") -> int:
        if " " in path:
            raise ValueError(f'path cannot contain any spaces! (Limitation of OBJ standard) \'{path}\'')
        line = f"\t{prefix}{code} {path}\n"
        return self._stream.write(line)

    # Comment
    def start_comment(self) -> int:
        return self._stream.write("#\t")

    # Colors
    def write_color_ambient(self, color: Float3) -> int:
        return self.__write_color("Ka", color)

    def write_color_diffuse(self, color: Float3) -> int:
        return self.__write_color("Kd", color)

    def write_color_specular(self, color: Float3) -> int:
        return self.__write_color("Ks", color)

    # Values
    def write_specular_highlight(self, value: float) -> int:
        return self.__write_float("Ns", value)

    def write_optical_density(self, value: float) -> int:
        return self.__write_float("Ni", value)

    def write_dissolve(self, value: float) -> int:
        written = self.__write_float("d", value)
        written += self.__write_float("Tr", 1.0 - value)
        return written

    # Enum
    def write_illum_mode(self, value: int) -> int:
        return self.__write_int("illum", value)

    # Starts a block
    def write_new_material(self, name: str) -> int:
        return self._stream.write(f"newmtl {name}\n")

    # Textures
    def write_texture_diffuse(self, path: str) -> int:
        return self.__write_texture("Kd", path)

    def write_texture_ambient(self, path: str) -> int:
        return self.__write_texture("Kd", path)

    def write_texture_specular(self, path: str) -> int:
        return self.write_texture_specular_highlight(path) + self.write_texture_specular_color(path)

    def write_texture_specular_color(self, path: str) -> int:
        return self.__write_texture("Ks", path)

    def write_texture_specular_highlight(self, path: str) -> int:
        return self.__write_texture("Ns", path)

    def write_texture_alpha(self, path: str) -> int:
        return self.__write_texture("d", path)

    def write_texture_bump(self, path: str) -> int:
        return self.__write_texture("bump", path) + \
               self.__write_texture("bump", path, prefix="")

    def write_texture_displacement(self, path: str) -> int:
        return self.__write_texture("disp", path, prefix="")

    def write_texture_decal(self, path: str) -> int:
        return self.__write_texture("decal", path, prefix="")

    # UNOFFICIAL ARGS (PBR pipeline)
    def write_texture_roughness(self, path: str) -> int:
        return self.__write_texture("Pr", path) + \
               self.__write_texture("Pr", path, prefix="")

    def write_texture_metallic(self, path: str) -> int:
        return self.__write_texture("Pm", path) + \
               self.__write_texture("Pm", path, prefix="")

    def write_texture_sheen(self, path: str) -> int:
        return self.__write_texture("Ps", path)

    def write_clearcoat_thickness(self, value: float) -> int:
        return self.__write_float("Pc", value)

    def write_clearcoat_rougness(self, value: float) -> int:
        return self.__write_float("Pcr", value)

    def write_texture_emissive(self, path: str) -> int:
        return self.__write_texture("Ke", path)

    def write_anisotropy(self, value: float) -> int:
        return self.__write_float("aniso", value)

    def write_anisotropy_rotation(self, value: float) -> int:
        return self.__write_float("anisor", value)

    def write_texture_normal(self, path: str) -> int:
        return self.__write_texture("norm", path, prefix="") + self.__write_texture("norm", path)

    # UNOFFICIAL ARGS (DirectX)
    def write_merged_RMA(self, path: str) -> int:
        return self.__write_texture("RMA", path)

    def write_merged_ORM(self, path: str) -> int:
        return self.__write_texture("ORM", path)

    #
    def write_unsupported_texture(self, path: str, name: str) -> int:
        return self.__write_texture(name, path, prefix="# ")

    # Prettify
    def write_blank(self) -> int:
        return self._stream.write("\n")

    # Helper to write defaults
    # Can be appended with textures later
    def write_default_texture(self, name: str, transparent: bool = False) -> int:
        written = 0
        WHITE = (1, 1, 1)
        BLACK = (0, 0, 0)
        written += self.write_new_material(name)
        written += self.write_color_ambient(WHITE)
        written += self.write_color_diffuse(WHITE)
        written += self.write_color_specular(BLACK)
        written += self.write_dissolve(0 if transparent else 1)
        written += self.write_specular_highlight(0)
        written += self.write_optical_density(1)
        written += self.write_illum_mode(2)
        return written
