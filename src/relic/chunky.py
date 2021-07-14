import os
import struct
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from os.path import join, dirname
from typing import BinaryIO, List, Union, Tuple

from relic.sga import walk_ext

_FILE_MAGIC = "Relic Chunky"
_FILE_MAGIC_STRUCT = struct.Struct("< 12s")
_FILE_HEADER_STRUCT = struct.Struct("< 4s L L")

_DATA_MAGIC = "DATA"
_FOLDER_MAGIC = "FOLD"
_HEADER_STRUCT = struct.Struct("< 4s 4s L L L")

class ChunkType(Enum):
    DATA = "DATA"
    FOLDER = "FOLD"

    @classmethod
    def from_str(cls, value: str) -> 'ChunkType':
        if value == "DATA":
            return ChunkType.DATA
        elif value == "FOLD":
            return ChunkType.FOLDER
        return value


@dataclass
class ChunkHeader:
    type: ChunkType
    id: str
    version: int
    size: int
    name: str

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'ChunkHeader':
        buffer = stream.read(_HEADER_STRUCT.size)
        type_str, id, version, size, name_size = _HEADER_STRUCT.unpack(buffer)

        name = stream.read(name_size)

        type_str = type_str.decode("ascii")
        id = id.decode("ascii")
        type = ChunkType.from_str(type_str)
        name = name.decode("ascii")

        header = ChunkHeader(type, id, version, size, name)
        if validate and type not in [ChunkType.FOLDER, ChunkType.DATA]:
            err_pos = stream.tell() - _HEADER_STRUCT.size
            raise TypeError(f"Type not valid! '{header.type}' @{err_pos} ~ 0x {hex(err_pos)[2:]} ~ [{buffer}]")
        return header


def read_all_chunks(stream: BinaryIO) -> List[Union['DataChunk', 'FolderChunk']]:
    chunks = []
    origin = stream.tell()
    stream.seek(0, 2)
    terminal = stream.tell()
    stream.seek(origin, 0)

    while stream.tell() < terminal:
        header = ChunkHeader.unpack(stream, True)

        if header.type == ChunkType.FOLDER:
            c = FolderChunk.unpack(stream, header)
        elif header.type == ChunkType.DATA:
            c = DataChunk.unpack(stream, header)
        else:
            raise Exception(f"Header isn't folder or data! ({header.type}) This should have been caught earlier!")
        chunks.append(c)
    return chunks


@dataclass
class DataChunk:
    header: ChunkHeader
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'DataChunk':
        data = stream.read(header.size)
        return DataChunk(header, data)


def walk_data_chunks(chunks: List[Union[DataChunk, 'FolderChunk']], parent: str = None) -> Tuple[str, DataChunk]:
    parent = parent or ""
    for i, chunk in enumerate(chunks):
        if isinstance(chunk, FolderChunk):
            for name, chunk in chunk.walk_data():
                full = join(parent, name)
                yield full, chunk
        elif isinstance(chunk, DataChunk):
            # safe_name = chunk.name.replace("\\","_").replace("/","_")
            # yield join(parent, f"{chunk.header.id}-{safe_name}"), chunk
            yield join(parent, f"{chunk.header.id}-{i}"), chunk
        else:
            raise Exception("Data / Folder type error")


def walk_chunks(chunks: List[Union[DataChunk, 'FolderChunk']], flat: bool = False) -> Tuple[
    Union[DataChunk, 'FolderChunk']]:
    for chunk in chunks:
        yield chunk
        if not flat:
            if isinstance(chunk, FolderChunk):
                for chunk in walk_chunks(chunk.chunks):
                    yield chunk


def get_chunk_by_id(chunks: List[Union[DataChunk, 'FolderChunk']], id: str = None, flat: bool = False) -> Union[
    DataChunk, 'FolderChunk']:
    for c in walk_chunks(chunks, flat=flat):
        if c.header.id == id:
            return c
    raise KeyError(id)


def get_all_chunks_by_id(chunks: List[Union[DataChunk, 'FolderChunk']], type: str = None, flat: bool = False) -> List[
    Union[DataChunk, 'FolderChunk']]:
    for c in walk_chunks(chunks, flat=flat):
        if c.header.id == type:
            yield c


def get_chunk_by_name(chunks: List[Union[DataChunk, 'FolderChunk']], name: str = None, *, strict_case: bool = False,
                      flat: bool = False) -> Union[DataChunk, 'FolderChunk']:
    for c in walk_chunks(chunks, flat=flat):
        if strict_case:
            if c.name == name:
                return c
        else:
            if c.name.lower() == name.lower():
                return c
    raise KeyError()


@dataclass
class FolderChunk:
    header: ChunkHeader
    chunks: List[Union['FolderChunk', DataChunk]]

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'FolderChunk':
        data = stream.read(header.size)
        with BytesIO(data) as window:
            chunks = read_all_chunks(window)
        return FolderChunk(header, chunks)

    def walk_data(self) -> Tuple[str, DataChunk]:
        return walk_data_chunks(self.chunks, parent=f"{self.header.id}")

    def get_chunk(self, id: str, optional: bool = False):
        try:
            return get_chunk_by_id(self.chunks, id)
        except KeyError:
            if optional:
                return None
            else:
                raise

    def get_all_chunks(self, id: str, flat: bool = False):
        return get_all_chunks_by_id(self.chunks, id, flat)


@dataclass
class FileHeader:
    type_br: str
    unk_a: int
    unk_b: int

    @classmethod
    def unpack(cls, stream: BinaryIO):
        buffer = stream.read(_FILE_HEADER_STRUCT.size)
        type_br, a, b = _FILE_HEADER_STRUCT.unpack_from(buffer)
        type_br = type_br.decode("ascii")
        return FileHeader(type_br, a, b)


@dataclass
class RelicChunky:
    header: FileHeader
    chunks: List[Union[FolderChunk, DataChunk]]

    @classmethod
    def unpack(cls, stream: BinaryIO):
        buffer = stream.read(_FILE_MAGIC_STRUCT.size)
        magic = _FILE_MAGIC_STRUCT.unpack_from(buffer)[0].decode("ascii")
        if magic != _FILE_MAGIC:
            raise ValueError((magic, _FILE_MAGIC))
        header = FileHeader.unpack(stream)
        chunks = read_all_chunks(stream)
        return RelicChunky(header, chunks)

    def walk_data(self) -> Tuple[str, DataChunk]:
        return walk_data_chunks(self.chunks)

    def get_chunk(self, id: str):
        return get_chunk_by_id(self.chunks, id)


def dump_chunky(full_in: str, full_out: str, skip_fatal: bool = False):
    with open(full_in, "rb") as handle:
        try:
            chunky = RelicChunky.unpack(handle)
        except TypeError as e:
            if skip_fatal:
                print(f"\tIgnoring:\n\t\t'{e}'\n\t- - -")
                return
            print(f"\tDumping?!\n\t\t'{e}'")
            log = full_out + ".crash"
            print(f"\n\n@ {log}")
            with open(log, "wb") as crash:
                handle.seek(0, 0)
                crash.write(handle.read())
                raise
        except ValueError as e:
            print(f"\tNot Chunky?!\n\t\t'{e}'")
            if skip_fatal:
                return
            raise

        print("\tWriting Assets...")
        i = 0
        for name, c in chunky.walk_data():
            print(f"\t{name}")
            dump_name = join(full_out, name)
            print(f"\t=>\t{dump_name}")
            i += 1
            try:
                os.makedirs(dirname(dump_name))
            except FileExistsError:
                pass
            with open(dump_name, "wb") as writer:
                writer.write(c.data)


def dump_all_chunky(full_in: str, full_out: str, exts: List[str] = None, skip_fatal: bool = False):
    for root, file in walk_ext(full_in, exts):
        i = join(root, file)
        j = i.replace(full_in, "", 1)
        j = j.lstrip("\\")
        j = j.lstrip("/")
        o = join(full_out, j)
        dump_chunky(i, o, skip_fatal)
