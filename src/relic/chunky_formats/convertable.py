from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass
from typing import Dict, Type, List, Optional, Iterable, Union, Tuple

from relic.chunky.chunk.chunk import AbstractChunk, GenericDataChunk, FolderChunk
from relic.chunky.chunk.header import ChunkType, ChunkHeader
from relic.chunky.chunky.chunky import GenericRelicChunky
from relic.chunky_formats.protocols import ChunkDefinition, ChunkyDefinition, ConvertableFolderChunk, ConvertableDataChunk, ConvertableChunky


class SupportsFolderChunkAutoConvert(ChunkDefinition, ConvertableFolderChunk):
    ...


class SupportsDataChunkAutoConvert(ChunkDefinition, ConvertableDataChunk):
    ...


class SupportsChunkyAutoConvert(ConvertableChunky, ChunkyDefinition):
    ...


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

    def register(self, convertable: Type[SupportsChunkyAutoConvert]):
        self[convertable.EXT] = convertable

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


class ChunkConverterFactory(UserDict[Tuple[ChunkType, str], Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]]):
    @dataclass
    class GenericFolderChunk(AbstractChunk):
        chunks: List[AbstractChunk]

    def __init__(self, default_generic_folder: bool = False, allow_overwrite: bool = False, __dict: Dict[Tuple[ChunkType, str], Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]] = None, **kwargs):
        super().__init__(__dict, **kwargs)
        self.default_generic_folder = default_generic_folder
        self.allow_overwrite = allow_overwrite

    def __setitem__(self, key: Tuple[ChunkType, str], value):
        assert len(key[1]) <= 4, f"ID '{key[1]}' is too large! IDs can be at most 4 characters long. This tool will strip '\0' but leave ' '."
        if not self.allow_overwrite and key in self.keys():
            raise KeyError(f"Key '{key}' already exists and overwrites are not allowed!")
        super().__setitem__(key, value)

    def __getitem__(self, item: Tuple[ChunkType, str]):
        return super().__getitem__(item)

    def add_converter(self, chunk_type: ChunkType, chunk_id: str, convertable: Union[ChunkConverterFactory, Type[Union[ConvertableDataChunk, ConvertableFolderChunk]]]):
        self[(chunk_type, chunk_id)] = convertable

    def register(self, convertable: Union[Type[SupportsDataChunkAutoConvert], Type[SupportsFolderChunkAutoConvert]]):
        self.add_converter(convertable.CHUNK_TYPE, convertable.CHUNK_ID, convertable)

    def register_sub_factory(self, chunk: ChunkDefinition, converter: ChunkConverterFactory):
        self.add_converter(chunk.CHUNK_TYPE, chunk.CHUNK_ID, converter)

    def add_data_converter(self, chunk_id: str, convertable: Type[ConvertableDataChunk]):
        self.add_converter(ChunkType.Data, chunk_id, convertable)

    def add_folder_converter(self, chunk_id: str, convertable: Union[ChunkConverterFactory, Type[SupportsFolderChunkAutoConvert]]):
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
        return self.GenericFolderChunk(header, sub_chunks)

    def convert(self, chunk: Union[GenericDataChunk, FolderChunk]) -> AbstractChunk:
        converter = self.get_converter_from_chunk(chunk)

        if not converter:
            if self.default_generic_folder and chunk.header.type == ChunkType.Folder:
                return self.__convert_folder_generic(chunk)
            raise KeyError(chunk.header.type, chunk.header.id)
        if isinstance(converter, ChunkConverterFactory):
            return converter.convert(chunk)  # Same signature but very different methods
        else:
            return converter.convert(chunk)

    def convert_many(self, chunks: Iterable[Union[GenericDataChunk, FolderChunk]]) -> List[AbstractChunk]:
        return [self.convert(c) for c in chunks]
