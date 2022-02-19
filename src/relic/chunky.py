from dataclasses import dataclass
from enum import Enum
from os.path import join
from typing import BinaryIO, List, Optional, Tuple, Iterable

from archive_tools.structio import BinaryWindow, end_of_stream
from archive_tools.structx import Struct

from .shared import Version, VersionEnum, Magic, MagicWalker


class RelicChunkyVersion(VersionEnum):
    Unsupported = None
    v1_1 = Version(1, 1)
    v3_1 = Version(3, 1)
    v4_1 = Version(4, 1)


# Alias
ChunkyVersion = RelicChunkyVersion

RelicChunkyMagic = Magic(Struct("< 12s"), "Relic Chunky")
RELIC_CHUNKY_MAGIC_WALKER = MagicWalker(RelicChunkyMagic)


class ChunkType(Enum):
    Folder = "FOLD"
    Data = "DATA"


@dataclass
class ChunkHeader:
    LAYOUT = Struct("< 4s 4s 3L")
    LAYOUT_V3_1 = Struct("< 2L")

    type: ChunkType
    id: str
    version: int
    size: int
    # name_size: int
    name: str
    unk_v3_1: Optional[List[int]] = None

    def equal(self, other: 'ChunkHeader', chunky_version: Version):
        if chunky_version == ChunkyVersion.v3_1:
            for i in range(len(self.unk_v3_1)):
                if self.unk_v3_1[i] != other.unk_v3_1[i]:
                    return False
        return self.type == other.type and self.id == other.id and self.version == other.version and self.size == other.size and self.name == other.name

    @classmethod
    def unpack(cls, stream: BinaryIO, chunky_version: Version) -> 'ChunkHeader':
        args = cls.LAYOUT.unpack_stream(stream)
        try:
            chunk_type = ChunkType(args[0].decode("ascii"))
        except ValueError:
            err_pos = stream.tell() - cls.LAYOUT_V3_1.size
            raise TypeError(f"Type not valid! '{args[0]}' @{err_pos} ~ 0x {hex(err_pos)[2:]}")

        unks_v3 = cls.LAYOUT_V3_1.unpack_stream(stream) if chunky_version == ChunkyVersion.v3_1 else None

        # ID can have nulls on both Left-side and right-side
        chunk_id = args[1].decode("ascii").strip("\x00")
        version, size = args[2:4]

        raw_name = stream.read(args[4])
        try:
            name = raw_name.decode("ascii").rstrip("\x00")
        except UnicodeError:
            err_pos = stream.tell() - cls.LAYOUT_V3_1.size
            raise TypeError(f"Name not valid! '{raw_name}' @{err_pos} ~ 0x {hex(err_pos)[2:]}")

        header = ChunkHeader(chunk_type, chunk_id, version, size, name, unks_v3)
        return header

    def pack(self, stream: BinaryIO, chunky_version: Version) -> int:
        args = self.type.value.encode("ascii"), self.id.encode("ascii"), self.version, self.size, len(self.name)
        written = self.LAYOUT.pack_stream(stream, *args)
        written += stream.write(self.name.encode("ascii"))
        if chunky_version == ChunkyVersion.v3_1:
            written += self.LAYOUT_V3_1.pack_stream(stream, self.unk_v3_1)
        return written

    def copy(self) -> 'ChunkHeader':
        """Provided as a safe method of modifying Chunk Headers for packing."""
        unks_v3_1_copy = [v for v in self.unk_v3_1] if self.unk_v3_1 else None
        return ChunkHeader(self.type, self.id, self.version, self.size, self.name, unks_v3_1_copy)


@dataclass
class AbstractChunk:
    """A base class for all chunks."""
    header: ChunkHeader


@dataclass
class UnpackableChunk(AbstractChunk):
    """An interface for packing/unpacking chunks"""

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'UnpackableChunk':
        """Unpacks the chunk from the stream, using the chunk header provided."""
        raise NotImplementedError

    def pack(self, stream: BinaryIO, chunky_version: Version) -> int:
        """Packs the chunk instance into the stream, using the proper format for the given chunky_version."""
        raise NotImplementedError


def read_all_chunks(stream: BinaryIO, chunky_version: Version) -> List[AbstractChunk]:
    chunks: List[AbstractChunk] = []

    while not end_of_stream(stream):
        header = ChunkHeader.unpack(stream, chunky_version)
        with BinaryWindow.slice(stream, header.size).as_parsing_window() as window:
            if header.type == ChunkType.Folder:
                c = FolderChunk.unpack(window, header, chunky_version)
            elif header.type == ChunkType.Data:
                c = DataChunk.unpack(window, header)
            else:
                raise Exception("Header isn't folder or data! This should have been caught earlier!")
        chunks.append(c)
    return chunks


def write_all_chunks(stream: BinaryIO, chunks: List[AbstractChunk], chunky_version: Version) -> int:
    written = 0
    for chunk in chunks:
        written += chunk.pack(stream, chunky_version)
    return written


# Path / Folders / Data
ChunkWalkResult = Tuple[str, List['Folder'], List['File']]


def walk_chunks(chunks: List[AbstractChunk], path: str = None, recursive: bool = True, unique: bool = True) -> Iterable[ChunkWalkResult]:
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
            for i, sub_folder in enumerate(folders):
                folder_path = join(parent_path, f"{sub_folder.header.id}-{i + 1}")
                for args in walk_chunks_filtered(sub_folder.chunks, sub_folder, folder_path, recursive, ids=ids,
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

    def get_chunk_list(self, recursive: bool = True, *, chunk_id: str = None, chunk_type: ChunkType = None, name: str = None,
                       optional: bool = False) -> Optional[List[AbstractChunk]]:
        chunks = [chunk for chunk in self.get_chunks(recursive, chunk_id=chunk_id, chunk_type=chunk_type, name=name)]
        if len(chunks) == 0:
            if not optional:
                raise Exception(
                    f"No chunk found! ('{chunk_id}' '{chunk_type}' '{name}'). To allow missing chunks, set optional=True")
            else:
                return None
        else:
            return chunks

    def get_chunks(self, recursive: bool = True, *, chunk_id: str = None, chunk_type: ChunkType = None, name: str = None) -> \
            Iterable[AbstractChunk]:
        for _, folders, data in self.walk_chunks_filtered(recursive=recursive, ids=chunk_id, types=chunk_type, names=name):
            for folder in folders:
                yield folder
            for d in data:
                yield d

    def get_chunk(self, recursive: bool = True, *, chunk_id: str = None, chunk_type: ChunkType = None, name: str = None,
                  optional: bool = False) -> AbstractChunk:
        if recursive not in [True, False]:
            raise ValueError(
                "Recursive not boolean value, likely due to using old get_chunk syntax; to specify id, use id=")

        for chunk in self.get_chunks(recursive=recursive, chunk_id=chunk_id, chunk_type=chunk_type, name=name):
            return chunk
        if optional:
            return None
        raise Exception(f"Chunk not found! ('{chunk_id}' '{chunk_type}' '{name}'). To allow missing chunks, set optional=True")

    # Utils for common cases
    def get_data_chunk(self, chunk_id: str, optional: bool = False) -> 'DataChunk':
        return self.get_chunk(recursive=False, chunk_id=chunk_id, chunk_type=ChunkType.Data, optional=optional)

    def get_data_chunks(self, chunk_id: str) -> Iterable['DataChunk']:
        return self.get_chunks(recursive=False, chunk_id=chunk_id, chunk_type=ChunkType.Data)

    def get_folder_chunk(self, chunk_id: str, optional: bool = False) -> 'FolderChunk':
        return self.get_chunk(recursive=False, chunk_id=chunk_id, chunk_type=ChunkType.Folder, optional=optional)

    def get_folder_chunks(self, chunk_id: str) -> Iterable['FolderChunk']:
        return self.get_chunks(recursive=False, chunk_id=chunk_id, chunk_type=ChunkType.Folder)


@dataclass
class FolderChunk(UnpackableChunk, ChunkCollection):

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader, chunky_version: Version) -> 'FolderChunk':
        chunks = read_all_chunks(stream, chunky_version)
        return FolderChunk(chunks, header)

    def pack(self, stream: BinaryIO, chunky_version: Version) -> int:
        start = stream.tell()  # We need to do a write-back
        header = self.header.copy()

        header.pack(stream, chunky_version)
        header.size = write_all_chunks(stream, self.chunks, chunky_version)

        end = stream.tell()

        stream.seek(start)  # Write-back
        header.pack(stream, chunky_version)

        stream.seek(end)
        return end - start


# a marker class to represent a data chunk, without specifying its data
@dataclass
class AbstractDataChunk(AbstractChunk):
    pass


@dataclass
class DataChunk(AbstractDataChunk, UnpackableChunk):
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, header: ChunkHeader) -> 'DataChunk':
        data = stream.read(header.size)
        assert len(data) == header.size
        return DataChunk(header, data)

    def pack(self, stream: BinaryIO, chunky_version: Version) -> int:
        header = self.header.copy()
        header.size = len(self.data)

        written = header.pack(stream, chunky_version)
        written += stream.write(self.data)
        return written


@dataclass
class RelicChunkyHeader:
    HEADER_LAYOUT = Struct("< 4s 2L")
    LAYOUT_V3_1 = Struct("< 3L")
    V3_CONST = (36, 28, 1)
    TYPE_BR = "\r\n\x1a\0".encode("ascii")  # I forgot what this was supposed to be (TODO)

    version: Version

    @classmethod
    def unpack(cls, stream: BinaryIO):
        type_br, v_major, v_minor = cls.HEADER_LAYOUT.unpack_stream(stream)
        version = Version(v_major, v_minor)
        assert type_br == cls.TYPE_BR

        if version == ChunkyVersion.v3_1:
            # Always these 3 values from what I've looked at so far. Why?
            # 36 is the position of the first chunk  in the ones I've looked at
            # 28 is a pointer to itself (28); perhaps the size of the Header?
            # Reserved 1?
            v3_args = cls.LAYOUT_V3_1.unpack_stream(stream)
            assert v3_args == cls.V3_CONST

        return RelicChunkyHeader(version)

    def pack(self, stream: BinaryIO) -> int:
        written = 0
        written += self.HEADER_LAYOUT.pack_stream(stream, self.TYPE_BR, self.version.major, self.version.minor)

        if self.version == ChunkyVersion.v3_1:
            written += self.LAYOUT_V3_1.pack_stream(stream, *self.V3_CONST)

        return written

    @classmethod
    def default(cls, version: Version = None) -> 'RelicChunkyHeader':
        version = version or Version(1, 1)
        return RelicChunkyHeader(version)

    def copy(self) -> 'RelicChunkyHeader':
        return RelicChunkyHeader(self.version)


# Added to allow specialized chunkies to preserve the header without re-declaring it
@dataclass
class AbstractRelicChunky(ChunkCollection):
    header: RelicChunkyHeader


@dataclass
class UnpackableRelicChunky(AbstractRelicChunky):
    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'UnpackableRelicChunky':
        raise NotImplementedError

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        raise NotImplementedError


@dataclass
class RelicChunky(UnpackableRelicChunky):
    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'RelicChunky':
        if read_magic:
            RelicChunkyMagic.assert_magic_word(stream)
        header = RelicChunkyHeader.unpack(stream)
        chunks = read_all_chunks(stream, header.version)
        return RelicChunky(chunks, header)

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        written = 0
        if write_magic:
            written += RelicChunkyMagic.write_magic_word(stream)
        written += self.header.pack(stream)
        written += write_all_chunks(stream, self.chunks, self.header.version)
        return written
