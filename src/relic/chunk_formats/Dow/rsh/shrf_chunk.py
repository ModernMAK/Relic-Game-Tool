from dataclasses import dataclass

from relic.chunk_formats.Dow.shared.txtr.txtr_chunk import TxtrChunk
from relic.chunky import FolderChunk


@dataclass
class ShrfChunk:
    texture: TxtrChunk

    # shader: ShdrChunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'ShrfChunk':
        txtr_chunk = chunk.get_chunk(id="TXTR")
        # shdr_chunk = chunk.get_chunk("SHDR")

        txtr = TxtrChunk.create(txtr_chunk)
        # shdr = ShdrChunk.create(shdr_chunk)

        return ShrfChunk(txtr)  # shdr,)
