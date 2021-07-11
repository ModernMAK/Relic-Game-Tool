import json
import struct
from dataclasses import dataclass
from io import BytesIO
from os.path import join, splitext
from typing import BinaryIO, List

from relic.model.archive import chunky

# FBIF
# RGSM (name of model)
# => MSGR
# => => MSLC (submodel? body part?)
# => => => BVOL
# => => => DATA
# => => BVOL
# => => DATA
# => SSHR (names are paths to textures [as images])
# => MARK
# => ANIM (name)
# => SKEL
from relic.model.archive.chunky import DataChunk, RelicChunky, FolderChunk, get_chunk_by_id, get_all_chunks_by_id
from relic.model.archive.shared import walk_ext, EnhancedJSONEncoder

_UNK_STRUCT = struct.Struct("< L L")
_NUM = struct.Struct("< L")


# MSGR

@dataclass
class MsgrName:
    name: str
    unk_a: int
    unk_b: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MsgrName':
        buffer = stream.read(_NUM.size)
        count = _NUM.unpack(buffer)[0]
        name = stream.read(count).decode("ascii")
        buffer = stream.read(_UNK_STRUCT.size)
        unk_a, unk_b = _UNK_STRUCT.unpack(buffer)
        return MsgrName(name, unk_a, unk_b)


@dataclass
class MsgrChunk:
    parts: List[MsgrName]
    submeshes: List['MslcChunk']

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'MsgrChunk':
        data = get_chunk_by_id(chunk.chunks, "DATA",flat=True)
        with BytesIO(data.data) as stream:
            buffer = stream.read(_NUM.size)
            count = _NUM.unpack(buffer)[0]
            parts = [MsgrName.unpack(stream) for _ in range(count)]
        submeshes = [MslcChunk.create(mscl) for mscl in get_all_chunks_by_id(chunk.chunks, "MSLC")]

        return MsgrChunk(parts, submeshes)


# SSHR
@dataclass
class SshrChunk:
    name: str

    @classmethod
    def create(cls, chunk: DataChunk) -> 'SshrChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(_NUM.size)
            num = _NUM.unpack(buffer)[0]
            name = stream.read(num).decode("ascii")
            return SshrChunk(name)


@dataclass
class MsclHeader:
    unk_a: int
    flag_b: bytes
    unk_c: int
    unk_d: int
    name_count: int

    _HEADER = struct.Struct("< L b L L L")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MsclHeader':
        buffer = stream.read(cls._HEADER.size)
        args = cls._HEADER.unpack(buffer)
        return MsclHeader(*args)


@dataclass
class MslcName:
    name: str
    unk_a: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MslcName':
        buffer = stream.read(_NUM.size)
        size = _NUM.unpack(buffer)[0]
        name = stream.read(size).decode("ascii")

        buffer = stream.read(_NUM.size)
        unk_a = _NUM.unpack(buffer)[0]

        return MslcName(name, unk_a)


@dataclass
class MslcChunk:
    V_SIZE = 48
    I_SIZE = 2

    header: MsclHeader
    names: List[MslcName]
    unk_b: int
    vertex_data: bytes
    unk_c: int
    textures: List[str]
    index_data: bytes
    unk_d: int
    unk_e: int
    unk_f: int
    unk_g: int

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'MslcChunk':
        data = get_chunk_by_id(chunk.chunks, "DATA")

        with BytesIO(data.data) as stream:
            header = MsclHeader.unpack(stream)
            names = [MslcName.unpack(stream) for _ in range(header.name_count)]
            vertex_count, unk_b = struct.unpack("< L L", stream.read(8))
            vertex = stream.read(vertex_count * cls.V_SIZE)
            unk_c, texture_count = struct.unpack("< L L", stream.read(8))
            textures = []
            for _ in range(texture_count):
                size = _NUM.unpack(stream.read(_NUM.size))[0]
                name = stream.read(size).decode("ascii")
                textures.append(name)

            index_count = _NUM.unpack(stream.read(_NUM.size))[0]
            index = stream.read(index_count * cls.I_SIZE)
            unk_d, unk_e, unk_f, unk_g = struct.unpack("< L L L L", stream.read(4 * 4))

        return MslcChunk(header, names, unk_b, vertex, unk_c, textures, index, unk_d, unk_e, unk_f, unk_g)


@dataclass
class WhmChunk:
    sshr: List[SshrChunk]
    msgr: MsgrChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WhmChunk':
        sshr = [SshrChunk.create(c) for c in get_all_chunks_by_id(chunky.chunks, 'SSHR')]
        msgr = MsgrChunk.create(get_chunk_by_id(chunky.chunks, "MSGR"))

        return WhmChunk(sshr, msgr)


# after MSCL texture name is the index count, multiply by two due to the size (short)?

def raw_dump():
    chunky.dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-chunky", [".whm"])


if __name__ == "__main__":
    with open(r"D:\Dumps\DOW I\sga\art\ebps\races\chaos\troops\aspiring_champion.whm", "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        whm = WhmChunk.create(chunky)
        meta = json.dumps(whm, indent=4, cls=EnhancedJSONEncoder)
        print(meta)

# 2a50 ~ 51 = 2a00 (VERTEX ONLY)
# 10752 bytes OR 2688 4byte words
# 0xEA01 ~ 59905 ~ 0.17 OR 0.04 (prob not this)
# 0xEA ~ 234 ~ 45.9 OR 11.48 (prob no this)
# 0xE0 ~ 224 ~ 48 OR 12
# 0x27 ~ 39 ~  275.69 OR 68.92


# Index Count is less obvious
# possible starts?
# @2aa1 ~ 10913
# @2aa5 ~ 10917
# possible ends
# @3024 ~ 12324
# @3034 ~ 12340
# possible sizes?
# 1407 ~ 0x57f +/-1? ~ 0x580 / 0x57e
# 1411 ~ 0x583 +/-1? ~ 0x584 / 0x582
# 1423 ~ 0x58f +/-1? ~ 0x590 / 0x58e
# 1427 ~ 0x593 +/-1? ~ 0x594 / 0x592
# Triangle counts?
# 469 ~ +1 invalid ~ -1 invalid
# 470.33 ~ +1 invalid ~ 470
# 474.33 ~ +1 invalid ~ 474
# 475.66 ~ 476 ~ -1 invalid
# Triangle counts (short groups)
# 234.5 ~ / ~ / @ ~
# / ~ / ~ 235 @ EB
# / ~ / ~ 237 @ ED
# / ~ 238 ~ / @ EE

# 74 ~ @0x4A
# @27 ~ 39

# @be02 ~ 48642
# @02be ~ 702

# 0x2aa1 ~ 0x3035 ~ 0x594
# 10913 ~ 12341 = 1428
# /2 ~ 714 ~ 2CA
# /3 ~ 476 ~ 1DC
# /6 ~ 238 ~ EC

#
# 3020 - 2aa4 by jumping pairs of 6's we got an index range
# 12320 ~ 10916 = 1404
# 234 Triangles @ 0xEA
# PROB NOT THIS 468 Triangle's
# 702 Indexes @ 0x2BE... which was the obvious answer but I DIDNT BELIEVE!!!!! (its the num I mentioned way up top)

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WITH NO EVIDENCE WHATSOEVER I AM 100% CONFIDENT THAT BVOL is 'Bounding Volume'
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
