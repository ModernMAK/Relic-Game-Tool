from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time
from typing import Union

from serialization_tools.vstruct import VStruct

from ....chunky import ChunkType, ChunkHeader
from ...protocols import ConvertableDataChunk
from ....chunky.chunk.chunk import DataChunk, GenericDataChunk


@dataclass
class FbifChunk(DataChunk, ConvertableDataChunk):
    CHUNK_ID = "FBIF"
    CHUNK_TYPE = ChunkType.Data
    LAYOUT = VStruct("v <l 2v")
    RELIC_LIKE_TIMESTAMP_FORMAT = "%B %d, %I:%M:%S %p"  # Not perfect due to leading 0's

    plugin: str
    version: int
    name: str
    timestamp: str

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> FbifChunk:
        assert chunk.header.version in [1], chunk.header.version
        plugin, version, name, timestamp = cls.LAYOUT.unpack(chunk.raw_bytes)
        plugin = plugin.decode("ascii")
        name = name.decode("ascii")
        timestamp = timestamp.decode("ascii")
        assert len(chunk.raw_bytes) == len(plugin) + len(name) + len(timestamp) + cls.LAYOUT.min_size
        return FbifChunk(chunk.header, plugin, version, name, timestamp)

    @classmethod
    def mimic_relic_timestamp(cls, t: Union[date, datetime, time]) -> str:
        return t.strftime(cls.RELIC_LIKE_TIMESTAMP_FORMAT)

    @classmethod
    def default(cls) -> FbifChunk:
        """ Creates a full (header included) default FbifChunk """
        HEADER_NAME = "FileBurnInfo"
        PLUGIN = "https://github.com/ModernMAK/Relic-SGA-Archive-Tool"
        VERSION = 0
        NAME = "Marcus Kertesz"
        TIME_STAMP = cls.mimic_relic_timestamp(datetime.now())
        SIZE = len(PLUGIN) + len(NAME) + len(TIME_STAMP) + cls.LAYOUT.min_size
        return FbifChunk(ChunkHeader(cls.CHUNK_TYPE, cls.CHUNK_ID, 1, SIZE, HEADER_NAME), PLUGIN, VERSION, NAME, TIME_STAMP)  # TODO Implement Timestamp
