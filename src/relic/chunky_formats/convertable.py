from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass
from typing import Dict, Type, List, Generic, TypeVar, Optional, Iterable

from ..chunky.chunk.chunk import AbstractChunk, GenericDataChunk, FolderChunk
from ..chunky.chunk.header import ChunkType
from ..chunky.chunky.chunky import GenericRelicChunky, RelicChunky
from ..chunky.chunky.header import ChunkyVersion


def find_chunks(chunks: List[AbstractChunk], id: str, type: ChunkType) -> Iterable[AbstractChunk]:
    for c in chunks:
        if c.header.id == id and c.header.type == type:
            yield c


def find_chunk(chunks: List[AbstractChunk], id: str, type: ChunkType) -> Optional[AbstractChunk]:
    for c in find_chunks(chunks, id, type):
        return c
    return None


@dataclass
class ConvertableChunky(RelicChunky):
    @classmethod
    def convert(cls, chunk: GenericRelicChunky) -> ConvertableChunky:
        raise NotImplementedError


@dataclass
class ConvertableChunk(AbstractChunk):
    @classmethod
    def convert(cls, chunk: AbstractChunk) -> ConvertableChunk:
        raise NotImplementedError


@dataclass
class ConvertableDataChunk(ConvertableChunk):
    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> ConvertableDataChunk:
        raise NotImplementedError


@dataclass
class ConvertableFolderChunk(ConvertableChunk):
    @classmethod
    def convert(cls, chunk: FolderChunk) -> ConvertableFolderChunk:
        raise NotImplementedError


T = TypeVar('T')


class ChunkyConverterFactory(Generic[T], UserDict):
    @property
    def supported(self) -> List[str]:
        return list(self.keys())

    @classmethod
    def __simplify_ext(cls, extension: str) -> str:
        return extension.lower().lstrip(".")

    def __setitem__(self, key: str, value):
        super().__setitem__(self.__simplify_ext(key), value)

    def __getitem__(self, item: str):
        return super().__getitem__(self.__simplify_ext(item))

    def add_converter(self, extension: str, convertable: Type[T]):
        self[extension] = convertable

    def get_converter(self, extension: str, _default: Type[T] = None) -> Optional[Type[T]]:
        return self.get(extension, _default)

    def convert(self, extension: str, chunky: RelicChunky):
        converter = self.get(extension)
        return converter.convert(chunky) if converter else chunky


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
