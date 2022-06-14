from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Type

from relic.chunky import _abc
from relic.chunky._core import Version

version = Version(1)

@dataclass
class ChunkMeta:
    name: str
    version: int


class DataChunk(_abc.DataChunk[ChunkMeta], ABC):
    ...


class RawDataChunk(_abc.RawDataChunk[ChunkMeta]):
    ...


class FolderChunk(_abc.FolderChunk[ChunkMeta], ABC):
    ...


# V1.1 has no MetaData; use NoneType

class Chunky(_abc.Chunky[None, FolderChunk, DataChunk]):
    ...


class RawChunky(_abc.Chunky[None, FolderChunk, RawDataChunk]):
    ...
