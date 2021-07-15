from typing import BinaryIO, List

from relic.chunky.abstract_chunk import AbstractChunk
from relic.chunky.chunk_header import ChunkHeader, ChunkType
from relic.chunky.data_chunk import DataChunk
from relic.chunky.folder_chunk import FolderChunk
from relic.shared import get_stream_size


def read_all_chunks(stream: BinaryIO) -> List[AbstractChunk]:
    chunks: List[AbstractChunk] = []
    terminal = get_stream_size(stream)

    while stream.tell() < terminal:
        header = ChunkHeader.unpack(stream, True)

        if header.type == ChunkType.Folder:
            c = FolderChunk.unpack(stream, header)
        elif header.type == ChunkType.Data:
            c = DataChunk.unpack(stream, header)
        else:
            raise Exception("Header isn't folder or data! This should have been caught earlier!")
        chunks.append(c)
    return chunks
