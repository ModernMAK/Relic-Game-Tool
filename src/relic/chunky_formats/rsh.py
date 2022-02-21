from dataclasses import dataclass

from relic.chunky.chunk import FolderChunk
from relic.chunky_formats.common_chunks.imag import TxtrChunk


@dataclass
class ShrfChunk:
    texture: TxtrChunk

    shader: FolderChunk  # ShdrChunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'ShrfChunk':
        txtr_chunk = chunk.get_folder_chunk("TXTR")
        shdr_chunk = chunk.get_folder_chunk("SHDR")

        txtr = TxtrChunk.convert(txtr_chunk)
        # shdr = ShdrChunk.create(shdr_chunk)

        return ShrfChunk(txtr, shdr_chunk)  # shdr,)


@dataclass
class RshChunky(AbstractRelicChunky):
    shrf: ShrfChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'RshChunky':
        shrf_folder = chunky.get_chunk(chunk_id="SHRF", recursive=True)
        shrf = ShrfChunk.create(shrf_folder)
        return RshChunky(chunky.chunks, chunky.header, shrf)
