from dataclasses import dataclass
from typing import List

from relic.chunk_formats.whm.msgr_chunk import MsgrChunk
from relic.chunk_formats.whm.sshr_chunk import SshrChunk
from relic.chunky import RelicChunky
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


@dataclass
class WhmChunky(AbstractRelicChunky):
    sshr: List[SshrChunk]
    msgr: MsgrChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WhmChunky':
        sshr = [SshrChunk.create(c) for c in chunky.get_chunks(id='SSHR')]
        msgr = MsgrChunk.create(chunky.get_chunk(id="MSGR"))
        return WhmChunky(chunky.chunks,chunky.header, sshr, msgr)