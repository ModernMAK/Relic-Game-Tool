import struct
from typing import BinaryIO, Tuple

from relic.model.archive import ieee754

SSND = "SSND"
SSND_STRUCT = struct.Struct("> 4s l L L H")  # Relic has an extra short inthere


# According to the DOW spec, offset and blocksize is always 0
def write_SSND(stream: BinaryIO, data: bytes, block_bitrate: int):
    buffer = SSND_STRUCT.pack(SSND.encode("ascii"), len(data) + 8 + 2, 0, 0, block_bitrate) #+2 for block_bitrate! DOH! its not in the spec so i was confused
    total = stream.write(buffer)
    total += stream.write(data)
    return total


def read_SSND(stream: BinaryIO) -> Tuple[bytes, int]:
    buffer = stream.read(SSND_STRUCT.size)
    ssnd, size, _, _, block_bitrate = SSND_STRUCT.unpack(buffer)
    assert ssnd.decode("ascii") == SSND
    size -= 8
    data = stream.read(size)
    return data, block_bitrate


MARKER_STRUCT = struct.Struct("> H L b")  # Relic has an extra short inthere


def read_marker(stream: BinaryIO) -> Tuple[int, int, str]:
    buffer = stream.read(MARKER_STRUCT.size)
    id, pos, name_size = MARKER_STRUCT.unpack(buffer)
    name = stream.read(name_size).decode("ascii")
    _pad = stream.read(1)
    return id, pos, name


def write_marker(stream: BinaryIO, id: int, pos: int, name: str) -> int:
    buffer = MARKER_STRUCT.pack(id, pos, len(name))
    total = stream.write(buffer)
    total += stream.write(name.encode("ascii"))
    total += stream.write(bytes(0x00))
    return total


def write_default_markers(stream: BinaryIO) -> int:
    total = write_marker(stream, 0x01, 0x00, "beg loop\00")
    total += write_marker(stream, 0x02, 0xffffffff, "end loop\00")
    total += write_marker(stream, 0x03, 0x00, "start offset\00")
    return total


MARK = "MARK"
MARK_STRUCT = struct.Struct("> 4s l H")  # Relic has an extra short inthere


def write_MARK(stream: BinaryIO, count: int, marker_data: bytes) -> int:
    buffer = MARK_STRUCT.pack(MARK.encode("ascii"), len(marker_data) + 2, count)
    total = stream.write(buffer)
    total += stream.write(marker_data)
    return total


def read_MARK(stream: BinaryIO) -> Tuple[int, bytes]:
    buffer = stream.read(MARK_STRUCT.size)
    mark, size, count = MARK_STRUCT.unpack(buffer)
    assert mark.decode("ascii") == MARK
    size -= 2
    data = stream.read(size)
    return count, data


COMM = "COMM"
COMM_STRUCT = struct.Struct(
    "> 4s l h L h 10s 4s b")  # python doesnt have an easy 10byte float, so I head by using a double, and relying on the fact that the fraction's most finite bits will be 0
COMM_MINSIZE = 23

def encode_sample_rate(sample_rate:float) -> bytes:
    return bytes([0x00] * 10)
    return ieee754.pack_float80(sample_rate)


def write_COMM(stream: BinaryIO, channels: int, sample_frames: int, sample_size: int, sample_rate: float, comp: str,
               desc: str) -> int:
    encoded_sample_rate = encode_sample_rate(sample_rate)
    buffer = COMM_STRUCT.pack(COMM.encode("ascii"), COMM_MINSIZE + len(desc), channels, sample_frames, sample_size,
                              encoded_sample_rate, comp.encode("ascii"),                              len(desc))
    total = stream.write(buffer)
    total += stream.write(desc.encode("ascii"))
    total += stream.write(bytes([0x00]))
    return total


def read_COMM(stream: BinaryIO) -> Tuple[int, int, int, float, str, str]:
    buffer = stream.read(MARK_STRUCT.size)
    comm, _, channels, sample_frames, sample_size, sample_rate, comp, desc_len = MARK_STRUCT.unpack(buffer)
    assert comm.decode("ascii") == COMM
    desc = stream.read(desc_len).decode("ascii")
    _pad = stream.read(1)
    return channels, sample_frames, sample_size, sample_rate, comp, desc


FVER = "FVER"
FVER_STRUCT = struct.Struct("> 4s l")


def write_FVER(stream: BinaryIO, data: bytes = None) -> int:
    d_len = 0 if not data else len(data)
    buffer = FVER_STRUCT.pack(FVER.encode("ascii"), d_len)
    total = stream.write(buffer)
    if data:
        total += stream.write(data)
    return total


def read_FVER(stream: BinaryIO) -> bytes:
    buffer = stream.read(FVER_STRUCT.size)
    fver, size = FVER_STRUCT.unpack(buffer)
    assert fver.decode("ascii") == FVER
    data = stream.read(size)
    return data


def write_default_FVER(stream: BinaryIO) -> int:
    VERSION = bytes([0xa2, 0x80, 0x51, 0x40])
    return write_FVER(stream, VERSION)


FORM = "FORM"
FORM_STRUCT = struct.Struct("> 4s l 4s")
AIFC = "AIFC"


def write_FORM(stream: BinaryIO, data: bytes) -> int:
    buffer = FORM_STRUCT.pack(FORM.encode("ascii"), len(data) + 4, AIFC.encode("ascii"))
    total = stream.write(buffer)
    total += stream.write(data)
    return total


def read_FORM(stream: BinaryIO) -> bytes:
    buffer = stream.read(FORM_STRUCT.size)
    form, size, aifc = FORM_STRUCT.unpack(buffer)
    assert form.decode("ascii") == FORM
    assert aifc.decode("ascii") == AIFC
    data = stream.read(size - 4)
    return data
