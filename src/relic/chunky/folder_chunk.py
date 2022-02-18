from dataclasses import dataclass
from typing import BinaryIO

from archive_tools.structio import BinaryWindow, end_of_stream

from relic.chunky.abstract_chunk import UnpackableChunk
from relic.chunky.chunk_collection import ChunkCollection
from relic.chunky.chunk_header import ChunkHeader
from relic.shared import Version


@dataclass
class FolderChunk(UnpackableChunk, ChunkCollection):

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader, chunky_version: Version) -> 'FolderChunk':
        from relic.chunky.reader import read_all_chunks  # Causes cylic dependency, must be included inside unpack

        with BinaryWindow.slice(stream, header.size).as_parsing_window() as window:
            chunks = read_all_chunks(window, chunky_version)
            assert end_of_stream(window)
        return FolderChunk(chunks, header)

    def pack(self, stream: BinaryIO, chunky_version: Version) -> int:
        from relic.chunky.reader import write_all_chunks
        start = stream.tell()  # We need to do a write-back
        header = self.header.copy()

        header.pack(stream, chunky_version)
        header.size = write_all_chunks(stream, self.chunks, chunky_version)

        end = stream.tell()

        stream.seek(start)  # Write-back
        header.pack(stream, chunky_version)

        stream.seek(end)
        return end - start
