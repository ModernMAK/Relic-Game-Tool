from dataclasses import dataclass
from typing import List

from relic.chunky import ChunkCollection, DataChunk


@dataclass
class SkelInfoChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class BoneChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class SkelChunk:
    info: SkelInfoChunk
    bones: List[BoneChunk]

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        info = SkelInfoChunk.convert(chunks.get_data_chunk("INFO"))
        bones = [BoneChunk.convert(c) for c in chunks.get_data_chunks("BONE")]
        return SkelChunk(info, bones)