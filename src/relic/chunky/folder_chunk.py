from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

from relic.chunky.abstract_chunk import AbstractChunk
from relic.chunky.chunk_collection import ChunkCollection
from relic.chunky.chunk_header import ChunkHeader


@dataclass
class FolderChunk(AbstractChunk, ChunkCollection):

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'FolderChunk':
        from relic.chunky.reader import read_all_chunks  # Causes cylic dependency, must be included inside unpack
        data = stream.read(header.size)
        with BytesIO(data) as window:
            chunks = read_all_chunks(window)
        return FolderChunk(chunks, header)
