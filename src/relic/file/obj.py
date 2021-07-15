import struct
from typing import Tuple, TextIO, Iterable

Float2 = Tuple[float, float]
Float2_Layout = struct.Struct("< f f")

Float3 = Tuple[float, float, float]
Float3_Layout = struct.Struct("< f f f")

Float4 = Tuple[float, float, float, float]
Float4_Layout = struct.Struct("< f f f f")

Short3 = Tuple[int, int, int]
Short3_Layout = struct.Struct("< h h h")


class ObjWriter:
    def __init__(self, stream: TextIO):
        self._stream = stream

    def __write_index(self, code: str, *indexes: Iterable[int]):
        line = code + ' %i' * len(indexes)
        line = line % indexes
        return self._stream.write(line)

    def __write_name(self, code: str, name: str):
        line = f"{code} {name}\n"
        return self._stream.write(line)

    # Prettify
    def write_blank(self):
        return self._stream.write("\n")

    # Vertex Info
    def write_position(self, x: float, y: float, z: float):
        line = 'v %f %f %f\n' % (x, y, z)
        return self._stream.write(line)

    def write_uv(self, u: float, v: float):
        line = 'vt %f %f\n' % (u, v)
        return self._stream.write(line)

    def write_normal(self, x: float, y: float, z: float):
        line = 'vn %f %f %f\n' % (x, y, z)
        return self._stream.write(line)

    # Index Info
    def write_face(self, *indexes: Iterable[int]):
        return self.__write_index("f", *indexes)

    def write_line(self, *indexes: Iterable[int]):
        return self.__write_index("l", *indexes)

    def write_point(self, *indexes: Iterable[int]):
        return self.__write_index("p", *indexes)

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
