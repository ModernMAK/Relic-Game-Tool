from dataclasses import dataclass

from relic.chunk_formats.whm.anbv_chunk import AnbvChunk
from relic.chunky import ChunkHeader, DataChunk, ChunkCollection


@dataclass
class AnimChunkData:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'AnimChunkData':
        return AnimChunkData(chunk.header, chunk.data)


@dataclass
class AnimChunk:
    data: AnimChunkData
    anbv: AnbvChunk

    @classmethod
    def convert(cls, chunk: ChunkCollection) -> 'AnimChunk':
        data = AnimChunkData.convert(chunk.get_chunk(recursive=False, id="DATA"))
        anbv = AnbvChunk.convert(chunk.get_chunk(recursive=False, id="ANBV"))
        return AnimChunk(data, anbv)
