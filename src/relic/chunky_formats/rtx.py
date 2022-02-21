from __future__ import annotations
from dataclasses import dataclass

from relic.chunky.chunk import ChunkType
from relic.chunky.chunky import RelicChunky, GenericRelicChunky
from relic.chunky_formats.common_chunks.imag import TxtrChunk
from relic.chunky_formats.convertable import find_chunk


@dataclass
class RtxChunky(RelicChunky):
    txtr: TxtrChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> RtxChunky:
        txtr = find_chunk(chunky.chunks, "TXTR", ChunkType.Folder)
        txtr = TxtrChunk.convert(txtr)
        assert len(chunky.chunks) == 1
        return RtxChunky(chunky.header, txtr)
