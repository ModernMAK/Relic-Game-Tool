import math
import struct
from typing import Tuple, BinaryIO, Iterable, Any

Float2 = Tuple[float, float]
Float2_Layout = struct.Struct("< f f")

Float3 = Tuple[float, float, float]
Float3_Layout = struct.Struct("< f f f")

Float4 = Tuple[float, float, float, float]
Float4_Layout = struct.Struct("< f f f f")

Short3 = Tuple[int, int, int]
Short3_Layout = struct.Struct("< h h h")


class MeshReader:
    def __init__(self, stream: BinaryIO):
        self._stream = stream

    def __read(self, layout: struct.Struct) -> Any:
        buffer = self._stream.read(layout.size)
        value = layout.unpack(buffer)
        return value

    def __seek(self, layout: struct.Struct, size: int = 1):
        offset = layout.size * size
        return self._stream.seek(offset, 1)

    def __read_list(self, layout: struct.Struct, size: int) -> Iterable[Any]:
        for _ in range(size):
            yield self.__read(layout)

    @classmethod
    def _validate_float(cls, validate: bool, *values: float):
        if validate:
            for value in values:
                assert not math.isnan(value)

    @classmethod
    def _validate_float_list(cls, validate: bool, *value_lists: Iterable[float]) -> Iterable[Iterable[float]]:
        if validate:
            for list in value_lists:
                for value in list:
                    assert not math.isnan(value)
                yield list
        else:
            return value_lists

    def read_float3(self, size: int = 1, validate: bool = False) -> Iterable[Float3]:
        values = self.__read_list(Float3_Layout, size)
        return self._validate_float_list(validate, *values)
        # return values

    def seek_float3(self, size: int = 1):
        self.__seek(Float3_Layout, size)

    def read_float4(self, size: int = 1, validate: bool = False) -> Iterable[Float4]:
        values = self.__read_list(Float4_Layout, size)
        return self._validate_float_list(validate, *values)
        # return values

    def seek_float4(self, size: int = 1):
        self.__seek(Float4_Layout, size)

    def read_float2(self, size: int = 1, validate: bool = False) -> Iterable[Float2]:
        values = self.__read_list(Float2_Layout, size)
        return self._validate_float_list(validate, *values)
        # return values

    def seek_float2(self, size: int = 1):
        self.__seek(Float2_Layout, size)

    def read_short3(self, size: int = 1, validate: bool = False) -> Iterable[Short3]:
        return self.__read_list(Short3_Layout, size)

    def seek_short3(self, size: int = 1):
        self.__seek(Short3_Layout, size)
