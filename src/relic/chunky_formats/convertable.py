from __future__ import annotations

from abc import ABC
from collections import UserDict
from dataclasses import dataclass
from typing import Dict, Type, List, Optional, Iterable, Protocol, Union, Tuple, ClassVar, Sized

from ..chunky.chunk.chunk import AbstractChunk, GenericDataChunk, FolderChunk
from ..chunky.chunk.header import ChunkType, ChunkHeader
from ..chunky.chunky.chunky import GenericRelicChunky, RelicChunky


def find_chunks(chunks: List[AbstractChunk], id: str, type: ChunkType) -> Iterable[AbstractChunk]:
    for c in chunks:
        if c.header.id == id and c.header.type == type:
            yield c


def find_chunk(chunks: List[AbstractChunk], id: str, type: ChunkType) -> Optional[AbstractChunk]:
    for c in find_chunks(chunks, id, type):
        return c
    return None


@dataclass
class UnimplementedChunky(RelicChunky):

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> None:
        raise NotImplementedError(cls.__name__, [(_.header.type.value, _.header.id) for _ in chunky.chunks])


@dataclass
class UnimplementedFolderChunk(AbstractChunk):
    @classmethod
    def convert(cls, chunk: FolderChunk) -> None:
        raise NotImplementedError(cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks])


@dataclass
class UnimplementedDataChunk(AbstractChunk):
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> UnimplementedDataChunk:
        return cls(chunk.header, chunk.data)


class ConvertableFolderChunk(Protocol):
    @classmethod
    def convert(cls, chunk: FolderChunk) -> AbstractChunk:
        raise NotImplementedError


class ConvertableDataChunk(Protocol):
    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> AbstractChunk:
        raise NotImplementedError


class ConvertableChunky(Protocol):
    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> RelicChunky:
        raise NotImplementedError


class SelfIdentifyingChunk(Protocol):
    CHUNK_ID: ClassVar[str]
    CHUNK_TYPE: ClassVar[ChunkType]


class SelfIdConvertableFolderChunk(SelfIdentifyingChunk, ConvertableFolderChunk, ABC):
    pass


# noinspection DuplicatedCode
class SelfIdConvertableDataChunk(SelfIdentifyingChunk, ConvertableDataChunk, ABC):
    pass


class ChunkCollection(Protocol):
    chunks: Iterable[AbstractChunk]


class ChunkCollectionX:
    @classmethod
    def list2col(cls, col: List[AbstractChunk]) -> ChunkCollectionX:
        @dataclass
        class Wrapper:
            chunks: List[AbstractChunk]

        return ChunkCollectionX(Wrapper(col))

    def __init__(self, inner: ChunkCollection):
        self.inner = inner

    def __len__(self) -> int:
        if isinstance(self.inner.chunks, Sized):
            return len(self.inner.chunks)
        else:
            return sum(1 for _ in self.inner.chunks)

    def get_chunks_by_type(self, chunk_type: ChunkType) -> Iterable[AbstractChunk]:
        for c in self.inner.chunks:
            if c.header.type == chunk_type:
                yield c

    @property
    def data_chunks(self) -> Iterable[AbstractChunk]:
        return self.get_chunks_by_type(ChunkType.Data)

    @property
    def folder_chunks(self) -> Iterable[AbstractChunk]:
        return self.get_chunks_by_type(ChunkType.Folder)

    def find(self, chunk: Type[SelfIdentifyingChunk], many: bool = False) -> Union[Iterable[AbstractChunk], Optional[AbstractChunk]]:
        return self.get(chunk.CHUNK_ID, chunk.CHUNK_TYPE, many=many)

    def find_and_convert(self, id_converter: Union[ClassVar[SelfIdConvertableDataChunk], ClassVar[SelfIdConvertableDataChunk]], many: bool = False) -> Union[Optional[AbstractChunk], Iterable[AbstractChunk]]:
        if many:
            chunks = self.find_chunks(id_converter)
            return [id_converter.convert(_) for _ in chunks]
        else:
            chunk = self.find_chunk(id_converter)
            if chunk:
                return id_converter.convert(chunk)
            else:
                return None

    def find_chunk(self, chunk: Type[SelfIdentifyingChunk]) -> Union[Iterable[AbstractChunk], Optional[AbstractChunk]]:
        return self.get_chunk(chunk.CHUNK_ID, chunk.CHUNK_TYPE)

    def find_chunks(self, chunk: Type[SelfIdentifyingChunk]) -> Union[Iterable[AbstractChunk], Optional[AbstractChunk]]:
        return self.get_chunks(chunk.CHUNK_ID, chunk.CHUNK_TYPE)

    def get(self, chunk_id: str, chunk_type: ChunkType, many: bool = False) -> Union[Iterable[AbstractChunk], Optional[AbstractChunk]]:
        if many:
            return self.get_chunks(chunk_id, chunk_type)
        else:
            return self.get_chunk(chunk_id, chunk_type)

    def get_chunks(self, chunk_id: str, chunk_type: ChunkType) -> Iterable[AbstractChunk]:
        for c in self.get_chunks_by_type(chunk_type):
            if c.header.id == chunk_id:
                yield c

    def get_chunk(self, chunk_id: str, chunk_type: ChunkType) -> Optional[AbstractChunk]:
        for c in self.get_chunks(chunk_id, chunk_type):
            return c
        return None


class ChunkyConverterFactory(UserDict[str, Type[ConvertableChunky]]):
    def __init__(self, not_implemented: List[str] = None, __dict: Dict[str, Type[ConvertableChunky]] = None, **kwargs):
        """

        :param not_implemented: A list of keys that will raise a NotImplementedError instead of a KeyError when using this class's convert method.
        :param __dict: An existing dict mapping, see UserDict for details.
        :param kwargs: See UserDict for details.
        """
        super().__init__(__dict=__dict, **kwargs)
        self.not_implemented = not_implemented or []

    @property
    def supported(self) -> List[str]:
        return list(self.keys())

    def __is_not_implemented(self, key: str) -> bool:
        return self.__simplify_ext(key) in self.not_implemented

    @classmethod
    def __simplify_ext(cls, extension: str) -> str:
        return extension.lower().lstrip(".")

    def __setitem__(self, key: str, value):
        super().__setitem__(self.__simplify_ext(key), value)

    def __getitem__(self, item: str):
        return super().__getitem__(self.__simplify_ext(item))

    def add_converter(self, extension: str, convertable: Type[ConvertableChunky]):
        self[extension] = convertable

    def get_converter(self, extension: str, _default: Type[ConvertableChunky] = None) -> Optional[Type[ConvertableChunky]]:
        return self.get(extension, _default)

    def convert(self, extension: str, chunky: GenericRelicChunky):
        try:
            converter = self[extension]
        except KeyError:
            if self.__is_not_implemented(extension):
                raise NotImplementedError(self.__simplify_ext(extension))
            else:
                raise
        return converter.convert(chunky)


@dataclass
class GenericFolderChunk(AbstractChunk):
    chunks: List[AbstractChunk]


class ChunkConverterFactory(UserDict[Tuple[ChunkType, str], Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]]):
    def __init__(self, default_generic_folder: bool = False, __dict: Dict[Tuple[ChunkType, str], Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]] = None, **kwargs):
        super().__init__(__dict, **kwargs)
        self.default_generic_folder = default_generic_folder

    def __setitem__(self, key: Tuple[ChunkType, str], value):
        assert len(key[1]) <= 4, f"ID '{key[1]}' is too large! IDs can be at most 4 characters long. This tool will strip '\0' but leave ' '."
        super().__setitem__(key, value)

    def __getitem__(self, item: Tuple[ChunkType, str]):
        return super().__getitem__(item)

    def add_converter(self, chunk_type: ChunkType, chunk_id: str, convertable: Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]):
        self[(chunk_type, chunk_id)] = convertable

    def register(self, convertable: Type[Union[SelfIdConvertableDataChunk, SelfIdConvertableFolderChunk]]):
        self.add_converter(convertable.CHUNK_TYPE, convertable.CHUNK_ID, convertable)

    def add_data_converter(self, chunk_id: str, convertable: Type[ConvertableDataChunk]):
        self.add_converter(ChunkType.Data, chunk_id, convertable)

    def add_folder_converter(self, chunk_id: str, convertable: Type[ConvertableFolderChunk]):
        self.add_converter(ChunkType.Data, chunk_id, convertable)

    def get_converter(self, chunk_type: ChunkType, chunk_id: str, _default: Type[Union[ConvertableDataChunk, ConvertableFolderChunk]] = None) -> Optional[Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]]:
        return self.get((chunk_type, chunk_id), _default)

    def get_converter_from_header(self, header: ChunkHeader) -> Optional[Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]]:
        return self.get_converter(header.type, header.id)

    def get_converter_from_chunk(self, chunk: AbstractChunk) -> Optional[Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]]:
        return self.get_converter_from_header(chunk.header)

    def __convert_folder_generic(self, chunk: FolderChunk) -> GenericFolderChunk:
        header = chunk.header
        sub_chunks = self.convert_many(chunk.chunks)
        return GenericFolderChunk(header, sub_chunks)

    def convert(self, chunk: Union[GenericDataChunk, FolderChunk]) -> AbstractChunk:
        converter = self.get_converter_from_chunk(chunk)
        if not converter:
            if self.default_generic_folder and chunk.header.type == ChunkType.Folder:
                return self.__convert_folder_generic(chunk)
            raise KeyError(chunk.header.type, chunk.header.id)
        return converter.convert(chunk)

    def convert_many(self, chunks: Iterable[Union[GenericDataChunk, FolderChunk]]) -> List[AbstractChunk]:
        return [self.convert(c) for c in chunks]

# def find_and_convert(chunk: ChunkCollection, identifier: SelfIdentifyingChunk, convert_factory: ChunkConverterFactory, many: bool = False) -> Union[Optional[AbstractChunk], Iterable[AbstractChunk]]:
#     if many:
#         gathered = chunk.find_chunks(identifier)
#         return convert_factory.convert_many(gathered)
#     else:
#         gathered = chunk.find_chunk(identifier)
#         if gathered:
#             return convert_factory.convert(gathered)
#         else:
#             return None


# class ChunkConverterFactory(Generic[T]):
#     def __init__(self):
#         self._DEFAULT = {}
#         self._VERSIONED = {}
#
#     def add_converter(self, chunk_id: str, convertable: Type[T], version: ChunkyVersion = None):
#         if version:
#             key = (chunk_id, version)
#             self._VERSIONED[key] = convertable
#         else:
#             self._DEFAULT[chunk_id] = convertable
#
#     def get_converter(self, chunk_id: str, version: ChunkyVersion = None) -> Type[T]:
#         if version:
#             key = (chunk_id, version)
#             converter = self._VERSIONED.get(key, )
#             if converter:
#                 return converter
#             # else try default
#         return self._DEFAULT[chunk_id]
#
#
# DATA_CONVERTER: ChunkConverterFactory = ChunkConverterFactory()
# FOLDER_CONVERTER: ChunkConverterFactory = ChunkConverterFactory()


# def convert_chunk(chunk: AbstractChunk) -> AbstractChunk:
#     if isinstance(chunk, FolderChunk):
#         convert_chunks(chunk.chunks)
#         converter = FOLDER_CONVERTER.get_converter(chunk.header.id, chunk.header.chunky_version)
#         if converter:
#             return converter.convert(chunk)
#         else:
#             return chunk
#     elif isinstance(chunk, GenericDataChunk):
#         converter = DATA_CONVERTER.get_converter(chunk.header.id, chunk.header.chunky_version)
#         if converter:
#             return converter.convert(chunk)
#         else:
#             return chunk
#     else:
#         return chunk


# def convert_chunks(chunks: List[AbstractChunk]) -> List[AbstractChunk]:
#     for i, c in enumerate(chunks):
#         chunks[i] = convert_chunk(c)
#     return chunks

#
# def convert_chunky(chunky: GenericRelicChunky) -> RelicChunky:
#     chunky.chunks = convert_chunks(chunky.chunks)
#     return chunky
