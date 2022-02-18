from dataclasses import dataclass
from typing import BinaryIO

from relic.chunky.abstract_chunk import UnpackableChunk
from relic.chunky.chunk_header import ChunkHeader
from relic.shared import Version


@dataclass
class DataChunk(UnpackableChunk):
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'DataChunk':
        data = stream.read(header.size)
        assert len(data) == header.size
        return DataChunk(header, data)

    def pack(self, stream: BinaryIO, chunky_version: Version) -> int:
        header = self.header.copy()
        header.size = len(self.data)

        written = header.pack(stream, chunky_version)
        written += stream.write(self.data)
        return written
