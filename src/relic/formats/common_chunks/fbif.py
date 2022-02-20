from __future__ import annotations

from dataclasses import dataclass

from archive_tools.vstruct import VStruct

from relic.formats.format_converter import ConvertableDataChunk
from relic.chunky.chunk.chunk import DataChunk, GenericDataChunk


@dataclass
class FbifChunk(DataChunk, ConvertableDataChunk):
    LAYOUT = VStruct("v <L 2v")

    plugin: str
    version: int
    name: str
    timestamp: str

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> FbifChunk:
        plugin, version, name, timestamp = cls.LAYOUT.unpack(chunk.data)
        plugin = plugin.decode("ascii")
        name = name.decode("ascii")
        timestamp = timestamp.decode("ascii")
        return FbifChunk(chunk.header, plugin, version, name, timestamp)

