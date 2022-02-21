from __future__ import annotations
from dataclasses import dataclass

from archive_tools.structx import Struct
from archive_tools.vstruct import VStruct

from ...chunky.chunk import DataChunk, GenericDataChunk, FolderChunk, AbstractChunk, ChunkType
from ...chunky.chunky import RelicChunky, GenericRelicChunky
from ..common_chunks.fbif import FbifChunk
from ..convertable import ConvertableDataChunk, find_chunk, ConvertableChunky


@dataclass
class FdaInfoChunk(DataChunk, ConvertableDataChunk):
    LAYOUT = Struct("< 7L")

    channels: int
    sample_size: int
    block_bitrate: int
    sample_rate: int
    begin_loop: int
    end_loop: int
    start_offset: int

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> FdaInfoChunk:
        args = cls.LAYOUT.unpack(chunk.data)
        return FdaInfoChunk(chunk.header, *args)


@dataclass
class FdaDataChunk(DataChunk):
    LAYOUT = VStruct("< v")
    # size: int
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> FdaDataChunk:
        data = cls.LAYOUT.unpack(chunk.data)[0]
        assert len(data) == len(chunk.data) - cls.LAYOUT.min_size
        return FdaDataChunk(chunk.header, data)


@dataclass
class FdaChunk(AbstractChunk):
    info: FdaInfoChunk
    data: FdaDataChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> FdaChunk:
        assert len(chunk.chunks) == 2

        info = find_chunk(chunk.chunks, "INFO", ChunkType.Data)
        # noinspection PyTypeChecker
        info = FdaInfoChunk.convert(info)

        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        # noinspection PyTypeChecker
        data = FdaDataChunk.convert(data)

        return FdaChunk(chunk.header, info, data)


@dataclass
class FdaChunky(ConvertableChunky, RelicChunky):
    fbif: FbifChunk
    fda: FdaChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> FdaChunky:
        assert len(chunky.chunks) == 2

        fbif = find_chunk(chunky.chunks, "FBIF", ChunkType.Data)
        # noinspection PyTypeChecker
        fbif = FbifChunk.convert(fbif)

        fda = find_chunk(chunky.chunks, "FDA ", ChunkType.Folder)
        # noinspection PyTypeChecker
        fda = FdaChunk.convert(fda)

        return FdaChunky(chunky.header, fbif, fda)
