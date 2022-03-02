from __future__ import annotations

from dataclasses import dataclass

from .header import ChunkyHeader
from ..chunk.chunk import ChunkCollection


@dataclass
class RelicChunky:
    header: ChunkyHeader


@dataclass
class GenericRelicChunky(RelicChunky, ChunkCollection):
    pass
