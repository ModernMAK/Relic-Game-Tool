from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Iterable, Optional, Protocol, Sized, Type, Union, ClassVar

from relic.chunky import AbstractChunk, ChunkType, RelicChunky, GenericRelicChunky, FolderChunk, GenericDataChunk
from relic.chunky_formats.convertable import SupportsDataChunkAutoConvert
from relic.chunky_formats.protocols import ChunkDefinition


def DEBUG_WRITE_TO_BIN(data: bytes, name: str = None):
    name = name or r"debug_dump"
    name += ".bin"
    print("\n", os.path.abspath(f".\\{name}"))
    with open(name, "wb") as h:
        h.write(data)


def find_chunks(chunks: List[AbstractChunk], id: str, type: ChunkType) -> Iterable[AbstractChunk]:
    for c in chunks:
        if c.header.id == id and c.header.type == type:
            yield c


def find_chunk(chunks: List[AbstractChunk], id: str, type: ChunkType) -> Optional[AbstractChunk]:
    for c in find_chunks(chunks, id, type):
        return c
    return None


@dataclass
class UnimplementedChunky(RelicChunky):

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> None:
        raise NotImplementedError(cls.__name__, [(_.header.type.value, _.header.id) for _ in chunky.chunks])


@dataclass
class UnimplementedFolderChunk(AbstractChunk):
    @classmethod
    def convert(cls, chunk: FolderChunk) -> None:
        raise NotImplementedError(cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks])


@dataclass
class UnimplementedDataChunk(AbstractChunk):
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> UnimplementedDataChunk:
        return cls(chunk.header, chunk.raw_bytes)


class ChunkCollection(Protocol):
    chunks: Iterable[AbstractChunk]


class ChunkCollectionX:
    @classmethod
    def list2col(cls, col: List[AbstractChunk]) -> ChunkCollectionX:
        @dataclass
        class Wrapper:
            chunks: List[AbstractChunk]

        return ChunkCollectionX(Wrapper(col))

    def __init__(self, inner: ChunkCollection):
        self.inner = inner

    def __len__(self) -> int:
        if isinstance(self.inner.chunks, Sized):
            return len(self.inner.chunks)
        else:
            return sum(1 for _ in self.inner.chunks)

    def get_chunks_by_type(self, chunk_type: ChunkType) -> Iterable[AbstractChunk]:
        for c in self.inner.chunks:
            if c.header.type == chunk_type:
                yield c

    @property
    def data_chunks(self) -> Iterable[AbstractChunk]:
        return self.get_chunks_by_type(ChunkType.Data)

    @property
    def folder_chunks(self) -> Iterable[AbstractChunk]:
        return self.get_chunks_by_type(ChunkType.Folder)

    def find(self, chunk: Type[ChunkDefinition], many: bool = False) -> Union[List[AbstractChunk], Optional[AbstractChunk]]:
        return self.get(chunk.CHUNK_ID, chunk.CHUNK_TYPE, many=many)

    def find_and_convert(self, id_converter: Union[ClassVar[SupportsDataChunkAutoConvert], ClassVar[SupportsDataChunkAutoConvert]], many: bool = False) -> Union[Optional[AbstractChunk], List[AbstractChunk]]:
        if many:
            chunks = self.find_chunks(id_converter)
            return [id_converter.convert(_) for _ in chunks]
        else:
            chunk = self.find_chunk(id_converter)
            if chunk:
                return id_converter.convert(chunk)
            else:
                return None

    def find_chunk(self, chunk: Type[ChunkDefinition]) -> Union[List[AbstractChunk], Optional[AbstractChunk]]:
        return self.get_chunk(chunk.CHUNK_ID, chunk.CHUNK_TYPE)

    def find_chunks(self, chunk: Type[ChunkDefinition]) -> Union[List[AbstractChunk], Optional[AbstractChunk]]:
        return self.get_chunks(chunk.CHUNK_ID, chunk.CHUNK_TYPE)

    def get(self, chunk_id: str, chunk_type: ChunkType, many: bool = False) -> Union[List[AbstractChunk], Optional[AbstractChunk]]:
        if many:
            return self.get_chunks(chunk_id, chunk_type)
        else:
            return self.get_chunk(chunk_id, chunk_type)

    def get_chunks(self, chunk_id: str, chunk_type: ChunkType) -> List[AbstractChunk]:
        return [c for c in self.get_chunks_by_type(chunk_type) if c.header.id == chunk_id]

    def get_chunk(self, chunk_id: str, chunk_type: ChunkType) -> Optional[AbstractChunk]:
        for c in self.get_chunks(chunk_id, chunk_type):
            return c
        return None
