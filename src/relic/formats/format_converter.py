from __future__ import annotations

from typing import Dict, Type, List, Generic, TypeVar

from ..chunky.chunk.chunk import AbstractChunk, GenericDataChunk, FolderChunk
from ..chunky.chunk.header import ChunkType
from ..chunky.chunky.chunky import GenericRelicChunky, RelicChunky
from ..chunky.chunky.header import ChunkyVersion


def find_chunk(chunks: List[AbstractChunk], id: str, type: ChunkType) -> AbstractChunk:
    for c in chunks:
        if c.header.id == id and c.header.type == type:
            return c
    raise KeyError


class ConvertableChunk(AbstractChunk):
    @classmethod
    def convert(cls, chunk: AbstractChunk) -> ConvertableChunk:
        raise NotImplementedError


class ConvertableDataChunk(ConvertableChunk):
    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> ConvertableDataChunk:
        raise NotImplementedError


class ConvertableFolderChunk(ConvertableChunk):
    @classmethod
    def convert(cls, chunk: FolderChunk) -> ConvertableFolderChunk:
        raise NotImplementedError


T = TypeVar('T')


class ChunkConverterFactory(Generic[T]):
    _DEFAULT: Dict[str, Type[T]]
    _VERSIONED: Dict[(str, ChunkyVersion), Type[T]]

    def __init__(self):
        self._DEFAULT = {}
        self._VERSIONED = {}

    def add_converter(self, chunk_id: str, convertable: Type[T], version: ChunkyVersion = None):
        if version:
            key = (chunk_id, version)
            self._VERSIONED[key] = convertable
        else:
            self._DEFAULT[chunk_id] = convertable

    def get_converter(self, chunk_id: str, version: ChunkyVersion = None) -> Type[T]:
        if version:
            key = (chunk_id, version)
            converter = self._VERSIONED.get(key, )
            if converter:
                return converter
            # else try default
        return self._DEFAULT[chunk_id]


DATA_CONVERTER: ChunkConverterFactory[ConvertableDataChunk] = ChunkConverterFactory()
FOLDER_CONVERTER: ChunkConverterFactory[ConvertableFolderChunk] = ChunkConverterFactory()


def convert_chunk(chunk: AbstractChunk) -> AbstractChunk:
    if isinstance(chunk, FolderChunk):
        convert_chunks(chunk.chunks)
        converter = FOLDER_CONVERTER.get_converter(chunk.header.id, chunk.header.chunky_version)
        if converter:
            return converter.convert(chunk)
        else:
            return chunk
    elif isinstance(chunk, GenericDataChunk):
        converter = DATA_CONVERTER.get_converter(chunk.header.id, chunk.header.chunky_version)
        if converter:
            return converter.convert(chunk)
        else:
            return chunk
    else:
        return chunk


def convert_chunks(chunks: List[AbstractChunk]) -> List[AbstractChunk]:
    for i, c in enumerate(chunks):
        chunks[i] = convert_chunk(c)
    return chunks


def convert_chunky(chunky: GenericRelicChunky) -> RelicChunky:
    chunky.chunks = convert_chunks(chunky.chunks)
    return chunky
