from abc import ABC
from dataclasses import dataclass
from typing import ClassVar

from relic.chunky import _abc
from relic.chunky._core import Version

version = Version(3)

@dataclass
class ChunkyMetadata:
    rsv_a_thirty_six: int
    rsv_b_twenty_eight: int
    rsv_c_one: int
    RESERVED: ClassVar = (36, 28, 1)  # what they mean; idk, but its technically meta data, so I define a class


@dataclass
class ChunkMeta:
    name: str
    version: int
    unk_a: int
    unk_b: int


class DataChunk(_abc.DataChunk[ChunkMeta], ABC):
    ...


class RawDataChunk(_abc.RawDataChunk[ChunkMeta]):
    ...


class FolderChunk(_abc.FolderChunk[ChunkMeta], ABC):
    ...


# V1.1 has no MetaData; use NoneType

class Chunky(_abc.Chunky[ChunkyMetadata, FolderChunk, DataChunk]):
    ...


class RawChunky(_abc.Chunky[ChunkyMetadata, FolderChunk, RawDataChunk]):
    ...
