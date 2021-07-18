from dataclasses import dataclass

from relic.chunk_formats.wtp.tpat_chunk import TpatChunk
from relic.chunky import RelicChunky


@dataclass
class WtpChunky:
    tpat: TpatChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WtpChunky':
        tpat_folder = chunky.get_chunk(id="TPAT")
        tpat = TpatChunk.create(tpat_folder)
        return WtpChunky(tpat)
