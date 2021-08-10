from typing import BinaryIO, Tuple, Any

from struct import Struct


def unpack_from_stream(layout: Struct, stream: BinaryIO) -> Tuple[Any, ...]:
    buffer = stream.read(layout.size)
    return layout.unpack(buffer)


def pack_into_stream(layout: Struct, stream: BinaryIO, *args: Any) -> int:
    buffer = layout.pack(*args)
    return stream.write(buffer)


_UInt64 = Struct("< Q")
_UInt32 = Struct("< L")
_UInt16 = Struct("< H")
_UInt8 = Struct("< B")
_UIntLookup = {8: _UInt64, 4: _UInt32, 2: _UInt16, 1: _UInt8}


def unpack_byte_length_data(stream: BinaryIO, length_byte_size: int = 4, data_byte_size: int = 1):
    len_struct = _UIntLookup[length_byte_size]
    size = unpack_from_stream(len_struct, stream)[0]
    size *= data_byte_size
    buffer = stream.read(size)
    assert len(buffer) == size
    return buffer
