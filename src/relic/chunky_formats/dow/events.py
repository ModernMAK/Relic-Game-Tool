from __future__ import annotations

from dataclasses import dataclass
from typing import List

from relic.chunky import AbstractChunk, FolderChunk, GenericDataChunk
from relic.chunky.chunk import ChunkType
from relic.chunky.chunky import RelicChunky, GenericRelicChunky
from relic.chunky_formats.util import find_chunks, find_chunk


@dataclass
class EvntChunk(AbstractChunk):
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> EvntChunk:
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class EvctChunk(AbstractChunk):
    evnt: List[EvntChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> EvctChunk:
        evnt = find_chunks(chunk.chunks, "EVNT", ChunkType.Data)
        evnt = [EvntChunk.convert(_) for _ in evnt]
        assert len(chunk.chunks) == len(evnt)
        return cls(chunk.header, evnt)


@dataclass
class EventsChunky(RelicChunky):
    evct: EvctChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> EventsChunky:
        evct = find_chunk(chunky.chunks, "EVCT", ChunkType.Folder)
        evct = EvctChunk.convert(evct)
        assert len(chunky.chunks) == 1
        return EventsChunky(chunky.header, evct)
