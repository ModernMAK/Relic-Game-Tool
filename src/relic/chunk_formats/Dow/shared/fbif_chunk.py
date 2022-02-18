from dataclasses import dataclass

from archive_tools.vstruct import VStruct

from relic.chunky import DataChunk, AbstractChunk


@dataclass
class FbifChunk(AbstractChunk):
    LAYOUT = VStruct("v <L 2v")

    plugin: str
    version: int
    name: str
    timestamp: str

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'FbifChunk':
        args = cls.LAYOUT.unpack(chunk.data)
        return FbifChunk(chunk.header, *args)
