from __future__ import annotations

from typing import Protocol, ClassVar, List

from relic.chunky import ChunkType, ChunkyVersion, FolderChunk, AbstractChunk, GenericDataChunk, GenericRelicChunky, RelicChunky


class ChunkDefinition(Protocol):
    CHUNK_ID: ClassVar[str]
    CHUNK_TYPE: ClassVar[ChunkType]
    VERSIONS: ClassVar[List[int]]


class ChunkyDefinition(Protocol):
    EXT: ClassVar[str]
    VERSIONS: ClassVar[List[ChunkyVersion]]


class ConvertableFolderChunk(Protocol):
    @classmethod
    def convert(cls, chunk: FolderChunk) -> AbstractChunk:
        ...


class ConvertableDataChunk(Protocol):
    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> AbstractChunk:
        ...


class ConvertableChunky(Protocol):
    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> RelicChunky:
        ...
