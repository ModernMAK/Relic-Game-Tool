from dataclasses import dataclass
from typing import List

from relic.chunky.chunk import FolderChunk, ChunkType, AbstractChunk
from relic.chunky.chunky import RelicChunky, GenericRelicChunky
from relic.chunky_formats.common_chunks.imag import TxtrChunk
from relic.chunky_formats.convertable import find_chunk, find_chunks


@dataclass
class ShrfChunk(AbstractChunk):
    texture: List[TxtrChunk]
    shdr: FolderChunk  # ShdrChunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'ShrfChunk':
        txtr = find_chunks(chunk.chunks, "TXTR", ChunkType.Folder)
        txtr = [TxtrChunk.convert(_) for _ in txtr]
        shdr = find_chunk(chunk.chunks, "SHDR", ChunkType.Folder)

        # shdr = ShdrChunk.create(shdr_chunk)
        assert len(chunk.chunks) == 1 + len(txtr), ([(c.header.type.name, c.header.id) for c in chunk.chunks])
        return ShrfChunk(chunk.header, txtr, shdr)


@dataclass
class RshChunky(RelicChunky):
    shrf: ShrfChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> 'RshChunky':
        shrf = find_chunk(chunky.chunks, "SHRF", ChunkType.Folder)
        shrf = ShrfChunk.create(shrf)
        assert len(chunky.chunks) == 1
        return RshChunky(chunky.header, shrf)
