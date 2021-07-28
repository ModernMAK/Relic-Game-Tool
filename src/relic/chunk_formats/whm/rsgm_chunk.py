from dataclasses import dataclass
from typing import List, Optional

from relic.chunk_formats.whm.msgr_chunk import MsgrChunk
from relic.chunk_formats.whm.skel_chunk import SkelChunk
from relic.chunk_formats.whm.sshr_chunk import SshrChunk
from relic.chunk_formats.whm.whm_chunky import MarkChunk, AnimChunk
from relic.chunky import ChunkCollection


@dataclass
class RsgmChunk:
    sshr: List[SshrChunk]
    skel: Optional[SkelChunk]
    msgr: MsgrChunk
    mark: MarkChunk
    anim: List[AnimChunk]

    @classmethod
    def convert(cls, chunk: ChunkCollection) -> 'RsgmChunk':
        sshr = [SshrChunk.convert(c) for c in chunk.get_chunks(id='SSHR', recursive=False)]

        skel_chunk = chunk.get_chunk(id='SKEL', recursive=False, optional=True)
        skel = SkelChunk.convert(skel_chunk) if skel_chunk else None

        mark_chunk = chunk.get_chunk(id="MARK", recursive=False, optional=True)
        mark = MarkChunk.convert(mark_chunk) if mark_chunk else None

        msgr = MsgrChunk.convert(chunk.get_chunk(id="MSGR", recursive=False))

        anim = [AnimChunk.convert(c) for c in chunk.get_chunks(id='ANIM', recursive=False)]

        return RsgmChunk(sshr, skel, msgr, mark, anim)