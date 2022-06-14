from __future__ import annotations

from typing import runtime_checkable, TypeVar, Protocol, BinaryIO, Sequence, Optional, Literal, Type, Iterable, Tuple

from relic.chunky._core import ChunkType, Version, ChunkFourCCPath, ChunkFourCC

TCFolder = TypeVar("TCFolder")
TCData = TypeVar("TCData")
TCFolder_co = TypeVar("TCFolder_co", covariant=True)
TCData_co = TypeVar("TCData_co", covariant=True)
TChunkyMetadata = TypeVar("TChunkyMetadata")
TCMetadata = TypeVar("TCMetadata")
T = TypeVar("T")
TChunky = TypeVar("TChunky")


@runtime_checkable
class StreamSerializer(Protocol[T]):
    def unpack(self, stream: BinaryIO) -> T:
        raise NotImplementedError

    def pack(self, stream: BinaryIO, packable: T) -> int:
        raise NotImplementedError


@runtime_checkable
class ChunkNode(Protocol):
    parent: Optional[ChunkContainer]


@runtime_checkable
class TypedChunk(Protocol):
    @property
    def type(self) -> ChunkType:
        raise NotImplementedError


@runtime_checkable
class IdentifiableChunk(Protocol):
    @property
    def fourCC(self) -> ChunkFourCC:
        raise NotImplementedError

    @property
    def fourCC_path(self) -> ChunkFourCCPath:
        raise NotImplementedError


@runtime_checkable
class Chunk(TypedChunk, IdentifiableChunk, ChunkNode, Protocol[TCMetadata]):
    metadata: TCMetadata


@runtime_checkable
class ChunkContainer(Protocol[TCFolder, TCData]):
    folders: Sequence[TCFolder]
    data_chunks: Sequence[TCData]


ChunkWalkStep = Tuple[ChunkContainer, Sequence[TCFolder_co], Sequence[TCData_co]]
ChunkWalk = Iterable[ChunkWalkStep]


class ChunkWalkable(Protocol[TCFolder_co, TCData_co]):
    def walk(self) -> ChunkWalk:
        raise NotImplementedError


class FolderChunk(Chunk[TCMetadata], ChunkWalkable, ChunkContainer, Protocol[TCMetadata]):
    @property
    def type(self) -> Literal[ChunkType.Folder]:  # type: ignore
        raise NotImplementedError


class DataChunk(Chunk[TCMetadata], Protocol[TCMetadata]):
    @property
    def type(self) -> Literal[ChunkType.Data]:  # type: ignore
        raise NotImplementedError


@runtime_checkable
class Chunky(ChunkContainer[TCFolder, TCData], ChunkWalkable, Protocol[TChunkyMetadata, TCFolder, TCData]):
    metadata: TChunkyMetadata


@runtime_checkable
class API(Protocol[TChunky, TCFolder, TCData, TChunkyMetadata, TCMetadata]):
    version: Version
    Chunky: Type[TChunky]
    FolderChunk: Type[TCFolder]
    DataChunk: Type[TCData]
    ChunkyMetadata: Type[TChunkyMetadata]
    ChunkMetadata: Type[TCMetadata]

    def read(self, stream: BinaryIO, lazy: bool = False) -> TChunky:
        raise NotImplementedError

    def write(self, stream: BinaryIO, chunky: TChunky):
        raise NotImplementedError
