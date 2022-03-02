from typing import BinaryIO, List

from serialization_tools.ioutil import BinaryWindow, has_data
from .chunk import AbstractChunk, FolderChunk, GenericDataChunk, ChunkHeader, ChunkType
from .chunky import ChunkyVersion, ChunkyMagic, ChunkyHeader, GenericRelicChunky


def read_chunky(stream: BinaryIO) -> GenericRelicChunky:
    ChunkyMagic.assert_magic_word(stream)
    header = ChunkyHeader.unpack(stream)
    chunks = read_all_chunks(stream, header.version)
    return GenericRelicChunky(chunks, header)


def write_chunky(chunky: GenericRelicChunky, stream: BinaryIO) -> int:
    written = ChunkyMagic.write_magic_word(stream)
    written += chunky.header.pack(stream)
    written += write_all_chunks(stream, chunky.chunks)
    return written


def read_folder_chunk(stream: BinaryIO, header: ChunkHeader) -> FolderChunk:
    with BinaryWindow.slice(stream, header.size) as window:  # TODO, remove, redundant, read_chunky enters a window
        chunks = read_all_chunks(window, header.chunky_version)
        return FolderChunk(chunks, header)


def write_folder_chunk(chunk: FolderChunk, stream: BinaryIO) -> int:
    start = stream.tell()  # We need to do a write-back
    header = chunk.header.copy()

    header.pack(stream)
    header.size = write_all_chunks(stream, chunk.chunks)

    end = stream.tell()

    stream.seek(start)  # Write-back
    header.pack(stream)

    stream.seek(end)
    return end - start


def read_data_chunk(stream: BinaryIO, header: ChunkHeader) -> GenericDataChunk:
    data = stream.read(header.size)
    assert len(data) == header.size
    return GenericDataChunk(header, data)


def write_data_chunk(chunk: GenericDataChunk, stream: BinaryIO) -> int:
    header = chunk.header.copy()
    header.size = len(chunk.raw_bytes)

    written = header.pack(stream)
    written += stream.write(chunk.raw_bytes)
    return written


def read_all_chunks(stream: BinaryIO, chunky_version: ChunkyVersion) -> List[AbstractChunk]:
    chunks: List[AbstractChunk] = []

    while has_data(stream):
        header = ChunkHeader.unpack(stream, chunky_version)
        with BinaryWindow.slice(stream, header.size) as window:
            if header.type == ChunkType.Folder:
                c = read_folder_chunk(window, header)
            elif header.type == ChunkType.Data:
                c = read_data_chunk(window, header)
            else:
                raise TypeError(header.type)
        chunks.append(c)
    return chunks


def write_all_chunks(stream: BinaryIO, chunks: List[AbstractChunk]) -> int:
    written = 0
    for chunk in chunks:
        if isinstance(chunk, FolderChunk):
            written += write_folder_chunk(chunk, stream)
        elif isinstance(chunk, GenericDataChunk):
            written += write_data_chunk(chunk, stream)
        else:
            raise TypeError(chunk)
    return written

#
# def walk_chunks(chunks: List[AbstractChunk], path: str = None, recursive: bool = True, unique: bool = True) -> Iterable[ChunkWalkResult]:
#     path = path or ""
#     folders: List['FolderChunk'] = []
#     data: List['GenericDataChunk'] = []
#     for chunk in chunks:
#         if chunk.header.type == ChunkType.Data:
#             data.append(chunk)
#         elif chunk.header.type == ChunkType.Folder:
#             folders.append(chunk)
#
#     yield path, folders, data
#
#     if recursive:
#         for i, folder in enumerate(folders):
#             folder_path = join(path, f"{folder.header.id}")
#
#             if unique:
#                 folder_path = f"{folder_path}-{i + 1}"
#
#             for args in walk_chunks(folder.chunks, folder_path, recursive):
#                 yield args

#
# def walk_chunks_filtered(chunks: List[AbstractChunk], parent: AbstractChunk = None, path: str = None,
#                          recursive: bool = True, *, ids: List[str] = None, types: List[ChunkType] = None,
#                          names: List[str] = None) -> Iterable[ChunkWalkResult]:
#     if not ids and not types and not names:
#         return walk_chunks(chunks, path, recursive)
#
#     # Validate filters
#     if types and not isinstance(types, List):
#         types = [types]
#     if ids and not isinstance(ids, List):
#         ids = [ids]
#     if names and not isinstance(names, List):
#         names = [names]
#
#     # we handle recursion manually due to  skip_filtered children
#     for parent_path, folders, data in walk_chunks(chunks, path, recursive=False):
#         filtered_folders = []
#         filtered_data = []
#
#         for chunk in folders:
#             # Filters
#             if ids and chunk.header.id not in ids:
#                 continue
#             if types and chunk.header.type not in types:
#                 continue
#             if names and chunk.header.name not in names:
#                 continue
#             filtered_folders.append(chunk)
#
#         for chunk in data:
#             # Filters
#             if ids and chunk.header.id not in ids:
#                 continue
#             if types and chunk.header.type not in types:
#                 continue
#             if names and chunk.header.name not in names:
#                 continue
#             filtered_data.append(chunk)
#
#         yield parent_path, filtered_folders, filtered_data
#
#         if recursive:
#             for i, sub_folder in enumerate(folders):
#                 folder_path = join(parent_path, f"{sub_folder.header.id}-{i + 1}")
#                 for args in walk_chunks_filtered(sub_folder.chunks, sub_folder, folder_path, recursive, ids=ids,
#                                                  types=types, names=names):
#                     yield args
