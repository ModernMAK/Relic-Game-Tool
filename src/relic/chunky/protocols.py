from __future__ import annotations

from contextlib import contextmanager
from typing import runtime_checkable, TypeVar, Protocol, BinaryIO, Sequence, Optional, Literal, Union

from relic.chunky._core import ChunkType

TCFolder = TypeVar("TCFolder")
TCData = TypeVar("TCData")
TChunkyMetadata = TypeVar("TChunkyMetadata")
T = TypeVar("T")


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
    def id(self) -> str:
        raise NotImplementedError

    @property
    def full_id(self) -> str:
        raise NotImplementedError


@runtime_checkable
class ChunkContainer(Protocol[TCFolder, TCData]):
    folders: Sequence[TCFolder]
    data_chunks: Sequence[TCData]


@runtime_checkable
class FolderChunk(IdentifiableChunk, TypedChunk, ChunkNode, ChunkContainer[TCFolder, TCData], Protocol[TCFolder, TCData]):
    @property
    def type(self) -> Literal[ChunkType.Folder]:  # type: ignore
        raise NotImplementedError


@runtime_checkable
class DataChunk(IdentifiableChunk, TypedChunk, ChunkNode, Protocol):
    @property
    def type(self) -> Literal[ChunkType.Data]:  # type: ignore
        raise NotImplementedError


@runtime_checkable
class RawDataChunk(DataChunk, Protocol):
    @property
    def data(self) -> bytes:
        raise NotImplementedError

    @contextmanager
    def open(self, read_only: bool = True) -> BinaryIO:
        raise NotImplementedError


Chunk = Union[FolderChunk, DataChunk]


@runtime_checkable
class Chunky(ChunkContainer[TCFolder, TCData], Protocol[TChunkyMetadata, TCFolder, TCData]):
    metadata: TChunkyMetadata
