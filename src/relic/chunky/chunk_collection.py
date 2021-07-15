from dataclasses import dataclass
from os.path import join
from typing import List, Tuple, Union, Iterable

from relic.chunky.abstract_chunk import AbstractChunk

# Here for any pu
from relic.chunky.chunk_header import ChunkType

# Path / Parent / Folders / Data
WalkResult = Tuple[str, 'ChunkCollection', List['ChunkCollection'], List[AbstractChunk]]


def walk_chunks(chunks: List[AbstractChunk], parent: AbstractChunk = None, path: str = None, recursive: bool = True) -> \
        Iterable[
            WalkResult]:
    path = path or ""
    folders: List[ChunkCollection] = []
    data: List[AbstractChunk] = []
    for chunk in chunks:
        if chunk.header.type == ChunkType.Data:
            data.append(chunk)
        elif chunk.header.type == ChunkType.Folder:
            folders.append(chunk)

    yield path, parent, folders, data

    if recursive:
        for i, folder in enumerate(folders):
            folder_path = join(path, f"{folder.header.id}-{i + 1}")
            for args in walk_chunks(folder.chunks, folder, folder_path, recursive):
                yield args


def walk_chunks_filtered(chunks: List[AbstractChunk], parent: AbstractChunk = None, path: str = None,
                         recursive: bool = True, *, ids: List[str] = None, types: List[ChunkType] = None,
                         names: List[str] = None) -> Iterable[
    WalkResult]:
    if not ids and not types and not names:
        return walk_chunks(chunks, parent, path, recursive)

    # Validate filters
    if types and not isinstance(types, List):
        types = [types]
    if ids and not isinstance(ids, List):
        ids = [ids]
    if names and not isinstance(names, List):
        names = [names]

    # we handle recursion manually due to  skip_filtered children
    for parent_path, parent, folders, data in walk_chunks(chunks, parent, path, recursive=False):
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

        yield parent_path, parent, filtered_folders, filtered_data

        if recursive:
            for i, subfolder in enumerate(folders):
                folder_path = join(parent_path, f"{subfolder.header.id}-{i + 1}")
                for args in walk_chunks_filtered(subfolder.chunks, subfolder, folder_path, recursive, ids=ids,
                                                 types=types, names=names):
                    yield args


#
# def get_chunk_heiarchy_by_id(chunks: List[AbstractChunk], id: str = None, recursive: bool = True) -> ChunkHeiarchy:
#     for path, chunk in walk_chunks(chunks, recursive=recursive):
#         if chunk.header.id == id:
#             return path, chunk
#     raise KeyError(id)
#
#
# def get_all_chunk_heiarchys_by_id(chunks: List[AbstractChunk], type: str = None, flat: bool = False) -> List[ChunkHeiarchy]:
#     for path, chunk in walk_chunks(chunks, recursive=recursive):
#         if chunk.header.id == id:
#             return path, chunk
#     raise KeyError(id)
#
#
# def get_chunk_by_name(chunks: List[AbstractChunk], name: str = None, *, strict_case: bool = False,
#                       flat: bool = False) -> AbstractChunk:
#     for c in walk_chunks(chunks, flat=flat):
#         if strict_case:
#             if c.name == name:
#                 return c
#         else:
#             if c.name.lower() == name.lower():
#                 return c
#     raise KeyError()


@dataclass
class ChunkCollection:
    chunks: List[AbstractChunk]

    def walk_chunks_filtered(
            self, recursive: bool = True, *, ids: List[str] = None,
            types: List[ChunkType] = None, names: List[str] = None
    ) -> Iterable[WalkResult]:
        return walk_chunks_filtered(self.chunks, recursive=recursive, ids=ids, types=types, names=names)

    def walk_chunks(self, recursive: bool = True) -> Iterable[WalkResult]:
        return walk_chunks(self.chunks, recursive=recursive)

    def get_chunks(self, recursive: bool = True, *, id: str = None, type: ChunkType = None, name: str = None) -> \
    Iterable[AbstractChunk]:
        for _, _, folders, data in self.walk_chunks_filtered(recursive=recursive, ids=id, types=type, names=name):
            for folder in folders:
                yield folder
            for d in data:
                yield d

    def get_chunk(self, recursive: bool = True, *, id: str = None, type: ChunkType = None, name: str = None,
                  optional: bool = False) -> AbstractChunk:
        for chunk in self.get_chunks(recursive=recursive, id=id, type=type, name=name):
            return chunk
        if optional:
            return None
        raise Exception(f"Chunk not found! ('{id}' '{type}' '{name}'). To allow missing chunks, set optional=True")
