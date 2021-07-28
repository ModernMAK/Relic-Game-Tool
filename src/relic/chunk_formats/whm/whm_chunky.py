from dataclasses import dataclass
from typing import List, Optional

from relic.chunk_formats.shared.fbif_chunk import FbifChunk
from relic.chunk_formats.whm.msgr_chunk import MsgrChunk
from relic.chunk_formats.whm.rsgm_chunk import RsgmChunk
from relic.chunk_formats.whm.skel_chunk import SkelChunk
from relic.chunk_formats.whm.sshr_chunk import SshrChunk
from relic.chunky import RelicChunky, ChunkCollection, DataChunk, ChunkHeader
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


@dataclass
class MarkChunk:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'MarkChunk':
        return MarkChunk(chunk.header, chunk.data)


@dataclass
class AnimChunkData:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'AnimChunkData':
        return AnimChunkData(chunk.header, chunk.data)


@dataclass
class AnbvChunk:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'AnbvChunk':
        return AnbvChunk(chunk.header, chunk.data)


@dataclass
class AnimChunk:
    data: AnimChunkData
    anbv: AnbvChunk

    @classmethod
    def convert(cls, chunk: ChunkCollection) -> 'AnimChunk':
        data = AnimChunkData.convert(chunk.get_chunk(recursive=False, id="DATA"))
        anbv = AnbvChunk.convert(chunk.get_chunk(recursive=False, id="ANBV"))
        return AnimChunk(data, anbv)



@dataclass
class WhmChunky(AbstractRelicChunky):
    rsgm: RsgmChunk
    fbif: Optional[FbifChunk] = None

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WhmChunky':
        rsgm = RsgmChunk.convert(chunky.get_chunk(id="RSGM", recursive=False))
        fbif = FbifChunk.unpack(chunky.get_chunk(id="FBIF", recursive=False))
        # sshr = [SshrChunk.convert(c) for c in chunky.get_chunks(id='SSHR')]
        # msgr = MsgrChunk.convert(chunky.get_chunk(id="MSGR"))
        return WhmChunky(chunky.chunks, chunky.header, rsgm, fbif)  # sshr, msgr)
