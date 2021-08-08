from dataclasses import dataclass
from io import BytesIO
from struct import Struct
from typing import BinaryIO

from relic.chunky import ChunkHeader, DataChunk
from relic.shared import unpack_from_stream


@dataclass
class FbifChunk:
    _NUM = Struct("< L")
    header: ChunkHeader

    plugin: str
    version: int
    name: str
    timestamp: str

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'FbifChunk':
        def read_len_str(s: BinaryIO):
            size = unpack_from_stream(cls._NUM, s)[0]
            string = s.read(size).decode("ASCII")
            return string

        with BytesIO(chunk.data) as stream:
            plugin = read_len_str(stream)
            version = unpack_from_stream(cls._NUM, stream)[0]
            name = read_len_str(stream)
            timestamp = read_len_str(stream)
            return FbifChunk(chunk.header, plugin, version, name, timestamp)