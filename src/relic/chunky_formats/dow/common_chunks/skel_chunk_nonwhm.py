
from __future__ import annotations
from dataclasses import dataclass
from typing import List

from ....chunky.chunk.chunk import AbstractChunk, GenericDataChunk, FolderChunk
from ....chunky.chunk.header import ChunkType
from ...util import find_chunks, find_chunk


@dataclass
class SkelInfoChunk(AbstractChunk):
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> SkelInfoChunk:
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class BoneChunk(AbstractChunk):
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> BoneChunk:
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class SkelChunk:
    info: SkelInfoChunk
    bones: List[BoneChunk]

    @classmethod
    def convert(cls, chunks: FolderChunk) -> SkelChunk:
        info = find_chunk(chunks.chunks, "INFO", ChunkType.Data)
        info = SkelInfoChunk.convert(info)

        bones = find_chunks(chunks.chunks, "BONE", ChunkType.Data)
        bones = [BoneChunk.convert(c) for c in bones]

        assert len(chunks.chunks) == len(bones) + 1
        return SkelChunk(info, bones)
