from dataclasses import dataclass

from relic.chunky import ChunkHeader, DataChunk


@dataclass
class AnbvChunk:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'AnbvChunk':
        return AnbvChunk(chunk.header, chunk.data)