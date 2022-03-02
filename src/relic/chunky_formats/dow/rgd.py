from __future__ import annotations
from dataclasses import dataclass

from relic.chunky import RelicChunky, GenericRelicChunky, ChunkType, GenericDataChunk, AbstractChunk
from relic.chunky_formats.util import find_chunk


@dataclass
class AegdChunk(AbstractChunk):
    raw: bytes  # TODO

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> AegdChunk:
        return AegdChunk(chunk.header, chunk.raw_bytes)


@dataclass
class RgdChunky(RelicChunky):
    aegd: AegdChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> RgdChunky:
        aegd = find_chunk(chunky.chunks, "AEGD", ChunkType.Data)
        aegd = AegdChunk.convert(aegd)
        assert len(chunky.chunks) == 1
        return RgdChunky(chunky.header, aegd)
