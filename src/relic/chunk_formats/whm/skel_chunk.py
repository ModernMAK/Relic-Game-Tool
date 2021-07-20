import struct
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, List

from relic.chunk_formats.whm.shared import num_layout
from relic.chunky import DataChunk


@dataclass
class SkelBone:
    # This chunk is also super easy
    name: str
    index: int
    floats: List[int]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'SkelBone':
        buffer = stream.read(num_layout.size)
        name_size = num_layout.unpack(buffer)[0]
        name = stream.read(name_size).decode("ascii")
        data = stream.read(32)
        args = struct.unpack("< l 7f", data)

        return SkelBone(name, args[0], args[1:])


@dataclass
class SkelChunk:
    # This chunk is super easy
    bones: List[SkelBone]

    def unpack(self, chunk: DataChunk) -> 'SkelChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(num_layout.size)
            bone_size = num_layout.unpack(buffer)[0]
            bones = [SkelBone.unpack(stream) for _ in range(bone_size)]
        return SkelChunk(bones)

