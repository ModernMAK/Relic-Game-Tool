from typing import TextIO, Iterable


class ObjWriter:
    def __init__(self, stream: TextIO):
        self._stream = stream

    def __write_index(self, code: str, *indexes: int, offset:int = 0, zero_based: bool=False):
        line = code + ' %i' * len(indexes) + "\n"
        indexes = [i + offset + (1 if zero_based else 0) for i in indexes]
        line = line % tuple(indexes)
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
    def write_face(self, *indexes: int, offset: int = 0, zero_based: bool = False):
        return self.__write_index("f", *indexes, offset=offset, zero_based=zero_based)

    def write_line(self, *indexes: int, offset: int = 0, zero_based: bool = False):
        return self.__write_index("l", *indexes, offset=offset, zero_based=zero_based)

    def write_point(self, *indexes: int, offset: int = 0, zero_based: bool = False):
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
