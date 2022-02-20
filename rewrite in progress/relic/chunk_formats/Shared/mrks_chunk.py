from dataclasses import dataclass

from relic.chunky import DataChunk


@dataclass
class MrksChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)