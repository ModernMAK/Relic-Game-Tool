from dataclasses import dataclass

from relic.chunk_formats.Dow.shared.txtr.txtr_chunk import TxtrChunk
from relic.chunky import RelicChunky
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


@dataclass
class RtxChunky(AbstractRelicChunky):
    txtr: TxtrChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'RtxChunky':
        txtr_folder = chunky.get_chunk(id="TXTR")
        txtr = TxtrChunk.create(txtr_folder)
        return RtxChunky(chunky.chunks, chunky.header, txtr)
