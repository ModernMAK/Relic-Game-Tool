import os
import struct
from dataclasses import dataclass
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


@dataclass
class ChunkHeader:
    type: str

    @property
    def is_data(self):
        return self.type == _DATA_MAGIC

    @property
    def is_folder(self):
        return self.type == _FOLDER_MAGIC

    @property
    def type_valid(self):
        return self.is_data or self.is_folder

    id: str
    version: int
    size: int
    name_size: int

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'ChunkHeader':
        buffer = stream.read(_HEADER_STRUCT.size)
        args = _HEADER_STRUCT.unpack(buffer)
        header = ChunkHeader(*args)
        header.id = header.id.decode("ascii")
        header.type = header.type.decode("ascii")
        if validate and not header.type_valid:
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

        if header.is_folder:
            c = FolderChunk.unpack(stream, header)
        elif header.is_data:
            c = DataChunk.unpack(stream, header)
        else:
            raise Exception("Header isn't folder or data! This should have been caught earlier!")
        chunks.append(c)
    return chunks


@dataclass
class DataChunk:
    header: ChunkHeader
    name: str
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'DataChunk':
        name = stream.read(header.name_size).decode("ascii").rstrip("\x00")
        data = stream.read(header.size)
        return DataChunk(header, name, data)


def walk_data_chunks(chunks: List[Union[DataChunk, 'FolderChunk']], parent: str = None) -> Tuple[str, DataChunk]:
    parent = parent or ""
    for i, chunk in enumerate(chunks):
        if isinstance(chunk, FolderChunk):
            self = f"{chunk.header.id}-{i}"
            full = join(parent, self)
            for children in walk_data_chunks(chunk.chunks, full):
                yield children
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
    name: str
    chunks: List[Union['FolderChunk', DataChunk]]

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'FolderChunk':
        name = stream.read(header.name_size).decode("ascii").rstrip("\x00")
        data = stream.read(header.size)
        with BytesIO(data) as window:
            chunks = read_all_chunks(window)
        return FolderChunk(header, name, chunks)

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
