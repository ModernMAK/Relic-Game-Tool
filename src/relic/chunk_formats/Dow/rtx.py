from dataclasses import dataclass

from relic.chunk_formats.Dow.shared.txtr import TxtrChunk
from relic.chunky import RelicChunky
from relic.chunky import AbstractRelicChunky


@dataclass
class RtxChunky(AbstractRelicChunky):
    txtr: TxtrChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'RtxChunky':
        txtr_folder = chunky.get_chunk(chunk_id="TXTR")
        txtr = TxtrChunk.convert(txtr_folder)
        return RtxChunky(chunky.chunks, chunky.header, txtr)


__all__ = [
    RtxChunky.__name__,
    # The following are provided as Aliases
    TxtrChunk.__name__
]
