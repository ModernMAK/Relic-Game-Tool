from dataclasses import dataclass

from relic.chunky import ChunkHeader, DataChunk


@dataclass
class MarkChunk:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'MarkChunk':
        return MarkChunk(chunk.header, chunk.data)

