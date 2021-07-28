from dataclasses import dataclass
from typing import Optional

from relic.chunk_formats.shared.fbif_chunk import FbifChunk
from relic.chunk_formats.whm.rsgm_chunk import RsgmChunk
from relic.chunky import RelicChunky
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


@dataclass
class WhmChunky(AbstractRelicChunky):
    rsgm: RsgmChunk
    fbif: Optional[FbifChunk] = None

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WhmChunky':
        rsgm = RsgmChunk.convert(chunky.get_chunk(id="RSGM", recursive=False))
        fbif = FbifChunk.convert(chunky.get_chunk(id="FBIF", recursive=False))
        # sshr = [SshrChunk.convert(c) for c in chunky.get_chunks(id='SSHR')]
        # msgr = MsgrChunk.convert(chunky.get_chunk(id="MSGR"))
        return WhmChunky(chunky.chunks, chunky.header, rsgm, fbif)  # sshr, msgr)
