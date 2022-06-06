from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from serialization_tools.structx import Struct

from relic.chunky import AbstractChunk, ChunkType, GenericDataChunk
from relic.file_formats.mesh_io import Float4

Byte = int
Short4 = Tuple[int, int, int, int]


@dataclass
class BvolChunk(AbstractChunk):
    CHUNK_ID = "BVOL"
    CHUNK_TYPE = ChunkType.Data
    LAYOUT = Struct("<b 12s 12f")

    unk: bytes

    matrix: Tuple[Float4, Float4, Float4]

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> BvolChunk:
        # TODO, this chunk is wierd; it makes sense to have a TRS matrix and then maybe some ints for size, BUT
        #       Not a 4x4 matrix (physically not enough data; 64 bytes min)
        #       Not an even nummer of bytes; (61?) meaning theres a flag byte of some kind
        #       Size could be 3 ints (XYZ) but why not store in TRS?
        assert len(chunk.raw_bytes) == chunk.header.size
        assert len(chunk.raw_bytes) == cls.LAYOUT.size, (len(chunk.raw_bytes), cls.LAYOUT.size)
        flag, unks, m00, m01, m02, m03, m10, m11, m12, m13, m20, m21, m22, m23 = cls.LAYOUT.unpack(chunk.raw_bytes)
        assert flag == 1, flag
        m = ((m00, m01, m02, m03), (m10, m11, m12, m13), (m20, m21, m22, m23))
        return BvolChunk(chunk.header, unks, m)


Byte4 = Tuple[int, int, int, int]
Byte3 = Tuple[int, int, int]
