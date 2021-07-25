from typing import TextIO

from relic.file_formats.mesh_io import Float3


class ObjWriter:
    def __init__(self, stream: TextIO):
        self._stream = stream

    def __write_index(self, code: str, *indexes: int, offset: int = 0, zero_based: bool = False, flip_winding:bool=False):

        if flip_winding:
            j = len(indexes)
            indexes = [indexes[j-i-1] for i in range(j)]
        indexes = [i + offset + (1 if zero_based else 0) for i in indexes]
        part = "%i/%i/%i"
        parts = [part % (i, i, i) for i in indexes]
        line = code + " " + " ".join(parts) + "\n"
        return self._stream.write(line)

    def __write_name(self, code: str, name: str):
        line = f"{code} {name}\n"
        return self._stream.write(line)

    # Prettify
    def write_blank(self):
        return self._stream.write("\n")

    # Vertex Info
    def write_vertex_position(self, x: float, y: float, z: float):
        line = 'v %f %f %f\n' % (x, y, z)
        return self._stream.write(line)

    def write_vertex_uv(self, u: float, v: float):
        line = 'vt %f %f\n' % (u, v)
        return self._stream.write(line)

    def write_vertex_normal(self, x: float, y: float, z: float):
        line = 'vn %f %f %f\n' % (x, y, z)
        return self._stream.write(line)

    # Index Info
    def write_index_face(self, *indexes: int, offset: int = 0, zero_based: bool = False, flip_winding:bool=False):
        return self.__write_index("f", *indexes, offset=offset, zero_based=zero_based, flip_winding=flip_winding)

    def write_index_line(self, *indexes: int, offset: int = 0, zero_based: bool = False):
        return self.__write_index("l", *indexes, offset=offset, zero_based=zero_based)

    def write_index_point(self, *indexes: int, offset: int = 0, zero_based: bool = False):
        return self.__write_index("p", *indexes, offset=offset, zero_based=zero_based)

    # Structure Info
    def write_group_name(self, name: str):
        return self.__write_name("g", name)

    def write_object_name(self, name: str):
        return self.__write_name("o", name)

    # Material
    def write_material_library(self, name: str):
        return self.__write_name("mtllib", name)

    def write_use_material(self, name: str):
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
        line = "\t%s %f %f %f\n" % (code, *color)
        return self._stream.write(line)

    def __write_texture(self, code: str, path: str, prefix: str = "map_") -> int:

        if " " in path:
            raise ValueError(f'path cannot contain any spaces! (Limitation of OBJ standard) \'{path}\'')
        line = f"\t{prefix}{code} {path}\n"
        return self._stream.write(line)

    # Colors
    def write_color_ambient(self, color: Float3):
        return self.__write_color("Ka", color)

    def write_color_diffuse(self, color: Float3):
        return self.__write_color("Kd", color)

    def write_color_specular(self, color: Float3):
        return self.__write_color("Ks", color)

    # Values
    def write_specular_highlight(self, value: float):
        return self.__write_float("Ns", value)

    def write_optical_density(self, value: float):
        return self.__write_float("Ni", value)

    def write_dissolve(self, value: float):
        written = self.__write_float("d", value)
        written += self.__write_float("Tr", 1.0-value)
        return written

    # Enum
    def write_illum_mode(self, value: int):
        return self.__write_int("illum", value)

    # Starts a block
    def write_new_material(self, name: str) -> int:
        return self._stream.write(f"newmtl {name}\n")

    # Textures
    def write_texture_diffuse(self, path: str) -> int:
        return self.__write_texture("Kd", path)

    def write_texture_ambient(self, path: str) -> int:
        return self.__write_texture("Kd", path)

    def write_texture_specular_color(self, path: str) -> int:
        return self.__write_texture("Ks", path)

    def write_texture_specular_highlight(self, path: str) -> int:
        return self.__write_texture("Ns", path)

    def write_texture_alpha(self, path: str) -> int:
        return self.__write_texture("d", path)

    def write_texture_bump(self, path: str) -> int:
        written = self.__write_texture("bump", path)
        written += self.__write_texture("bump", path, prefix="")
        return written

    def write_texture_displacement(self, path: str) -> int:
        return self.__write_texture("disp", path, prefix="")

    def write_texture_decal(self, path: str) -> int:
        return self.__write_texture("decal", path, prefix="")

    # Prettify
    def write_blank(self) -> int:
        return self._stream.write("\n")

    # Helper to write defaults
    # Can be appended with textures later
    def write_default_texture(self, name: str) -> int:
        written = 0
        WHITE = (1, 1, 1)
        BLACK = (0, 0, 0)
        written += self.write_new_material(name)
        written += self.write_color_ambient(WHITE)
        written += self.write_color_diffuse(WHITE)
        written += self.write_color_specular(BLACK)
        written += self.write_dissolve(0)
        written += self.write_specular_highlight(0)
        written += self.write_optical_density(1)
        written += self.write_illum_mode(2)
        return written
