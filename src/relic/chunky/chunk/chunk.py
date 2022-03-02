from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .header import ChunkHeader


@dataclass
class AbstractChunk:
    """A base class for all chunks."""
    header: ChunkHeader


@dataclass
class ChunkCollection:
    chunks: List[AbstractChunk]


@dataclass
class FolderChunk(AbstractChunk, ChunkCollection):
    pass


@dataclass
class DataChunk(AbstractChunk):
    pass


@dataclass
class GenericDataChunk(DataChunk):
    raw_bytes: bytes
