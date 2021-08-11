from dataclasses import dataclass
from os.path import join
from typing import List, Tuple, Iterable, Optional

from relic.chunky.data_chunk import DataChunk
from relic.chunky.abstract_chunk import AbstractChunk
from relic.chunky.chunk_header import ChunkType

# Path / Folders / Data
ChunkWalkResult = Tuple[str, List['Folder'], List['File']]


def walk_chunks(chunks: List[AbstractChunk], path: str = None, recursive: bool = True, unique: bool = True) -> Iterable[
    ChunkWalkResult]:
    path = path or ""
    folders: List['FolderChunk'] = []
    data: List['DataChunk'] = []
    for chunk in chunks:
        if chunk.header.type == ChunkType.Data:
            data.append(chunk)
        elif chunk.header.type == ChunkType.Folder:
            folders.append(chunk)

    yield path, folders, data

    if recursive:
        for i, folder in enumerate(folders):
            folder_path = join(path, f"{folder.header.id}")

            if unique:
                folder_path = f"{folder_path}-{i + 1}"

            for args in walk_chunks(folder.chunks, folder_path, recursive):
                yield args


def walk_chunks_filtered(chunks: List[AbstractChunk], parent: AbstractChunk = None, path: str = None,
                         recursive: bool = True, *, ids: List[str] = None, types: List[ChunkType] = None,
                         names: List[str] = None) -> Iterable[ChunkWalkResult]:
    if not ids and not types and not names:
        return walk_chunks(chunks, path, recursive)

    # Validate filters
    if types and not isinstance(types, List):
        types = [types]
    if ids and not isinstance(ids, List):
        ids = [ids]
    if names and not isinstance(names, List):
        names = [names]

    # we handle recursion manually due to  skip_filtered children
    for parent_path, folders, data in walk_chunks(chunks, path, recursive=False):
        filtered_folders = []
        filtered_data = []

        for chunk in folders:
            # Filters
            if ids and chunk.header.id not in ids:
                continue
            if types and chunk.header.type not in types:
                continue
            if names and chunk.header.name not in names:
                continue
            filtered_folders.append(chunk)

        for chunk in data:
            # Filters
            if ids and chunk.header.id not in ids:
                continue
            if types and chunk.header.type not in types:
                continue
            if names and chunk.header.name not in names:
                continue
            filtered_data.append(chunk)

        yield parent_path, filtered_folders, filtered_data

        if recursive:
            for i, subfolder in enumerate(folders):
                folder_path = join(parent_path, f"{subfolder.header.id}-{i + 1}")
                for args in walk_chunks_filtered(subfolder.chunks, subfolder, folder_path, recursive, ids=ids,
                                                 types=types, names=names):
                    yield args


@dataclass
class ChunkCollection:
    chunks: List[AbstractChunk]

    def walk_chunks_filtered(
            self, recursive: bool = True, *, ids: List[str] = None,
            types: List[ChunkType] = None, names: List[str] = None
    ) -> Iterable[ChunkWalkResult]:
        return walk_chunks_filtered(self.chunks, recursive=recursive, ids=ids, types=types, names=names)

    def walk_chunks(self, recursive: bool = True, unique: bool = True) -> Iterable[ChunkWalkResult]:
        return walk_chunks(self.chunks, recursive=recursive, unique=unique)

    def get_chunk_list(self, recursive: bool = True, *, id: str = None, type: ChunkType = None, name: str = None,
                       optional: bool = False) -> Optional[List[AbstractChunk]]:
        chunks = [chunk for chunk in self.get_chunks(recursive, id=id, type=type, name=name)]
        if len(chunks) == 0:
            if not optional:
                raise Exception(
                    f"No chunk found! ('{id}' '{type}' '{name}'). To allow missing chunks, set optional=True")
            else:
                return None
        else:
            return chunks

    def get_chunks(self, recursive: bool = True, *, id: str = None, type: ChunkType = None, name: str = None) -> \
            Iterable[AbstractChunk]:
        for _, folders, data in self.walk_chunks_filtered(recursive=recursive, ids=id, types=type, names=name):
            for folder in folders:
                yield folder
            for d in data:
                yield d

    def get_chunk(self, recursive: bool = True, *, id: str = None, type: ChunkType = None, name: str = None,
                  optional: bool = False) -> AbstractChunk:
        if recursive not in [True, False]:
            raise ValueError(
                "Recursive not boolean value, likely due to using old get_chunk syntax; to specify id, use id=")

        for chunk in self.get_chunks(recursive=recursive, id=id, type=type, name=name):
            return chunk
        if optional:
            return None
        raise Exception(f"Chunk not found! ('{id}' '{type}' '{name}'). To allow missing chunks, set optional=True")

    # Utils for common cases
    def get_data_chunk(self, id: str, optional: bool = False) -> DataChunk:
        return self.get_chunk(recursive=False, id=id, type=ChunkType.Data, optional=optional)

    def get_data_chunks(self, id: str) -> Iterable[DataChunk]:
        return self.get_chunks(recursive=False, id=id, type=ChunkType.Data)

    def get_folder_chunk(self, id: str, optional: bool = False) -> 'FolderChunk':
        return self.get_chunk(recursive=False, id=id, type=ChunkType.Folder, optional=optional)

    def get_folder_chunks(self, id: str) -> Iterable['FolderChunk']:
        return self.get_chunks(recursive=False, id=id, type=ChunkType.Folder)