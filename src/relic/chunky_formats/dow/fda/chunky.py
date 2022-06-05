from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct

from ..common_chunks.fbif import FbifChunk
from ...convertable import ChunkConverterFactory
from ...util import ChunkCollectionX
from ....chunky import DataChunk, GenericDataChunk, ChunkType, RelicChunky, GenericRelicChunky, ChunkyVersion, AbstractChunk, FolderChunk


@dataclass
class FdaInfoChunk(DataChunk):
    LAYOUT = Struct("< 7l")
    CHUNK_ID = "INFO"
    CHUNK_TYPE = ChunkType.Data

    channels: int
    sample_size: int
    block_bitrate: int
    sample_rate: int
    begin_loop: int
    end_loop: int
    start_offset: int

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> FdaInfoChunk:
        # VERSIONED
        assert chunk.header.version in [1], chunk.header.version

        args = cls.LAYOUT.unpack(chunk.raw_bytes)
        return FdaInfoChunk(chunk.header, *args)


@dataclass
class FdaDataChunk(DataChunk):
    CHUNK_ID = "DATA"
    CHUNK_TYPE = ChunkType.Data
    LAYOUT = VStruct("< v")
    # size: int
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> FdaDataChunk:
        # VERSIONED
        assert chunk.header.version in [1], chunk.header.version

        data = cls.LAYOUT.unpack(chunk.raw_bytes)[0]
        assert len(data) == len(chunk.raw_bytes) - cls.LAYOUT.min_size
        return FdaDataChunk(chunk.header, data)


@dataclass
class FdaChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "FDA "
    # chunks: List[AbstractChunk]

    info: FdaInfoChunk
    data: FdaDataChunk

    @property
    def chunks(self) -> Iterable[AbstractChunk]:
        yield self.info
        yield self.data

    @classmethod
    def convert(cls, chunk: FolderChunk) -> FdaChunk:
        assert chunk.header.version in [1], chunk.header.version
        converted = FdaChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        info = x.find(FdaInfoChunk)
        data = x.find(FdaDataChunk)
        assert len(converted) == len(chunk.chunks) and len(chunk.chunks) == 2
        return FdaChunk(chunk.header, info, data)


@dataclass
class FdaChunky(RelicChunky):
    SUPPORTED_VERSIONS = [ChunkyVersion.v0101]
    fbif: FbifChunk
    fda: FdaChunk

    @property
    def chunks(self) -> Iterable[AbstractChunk]:
        yield self.fbif
        yield self.fda

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> FdaChunky:
        # VERSIONED
        assert chunky.header.version in cls.SUPPORTED_VERSIONS, chunky.header.version
        converted = FdaChunkConverter.convert_many(chunky.chunks)
        x = ChunkCollectionX.list2col(converted)
        fbif = x.find(FbifChunk)
        fda = x.find(FdaChunk)
        assert len(converted) == len(chunky.chunks) and len(chunky.chunks) == 2
        return FdaChunky(chunky.header, fbif, fda)


def add_fda_chunk_converter(conv: ChunkConverterFactory):
    conv.register(FbifChunk)
    conv.register(FdaInfoChunk)
    conv.register(FdaDataChunk)
    conv.register(FdaChunk)


def generate_fda_chunk_converter():
    conv = ChunkConverterFactory()
    add_fda_chunk_converter(conv)
    return conv


# Individual converters are used to allow differing Chunkies to substitute their own Chunks
FdaChunkConverter = generate_fda_chunk_converter()
