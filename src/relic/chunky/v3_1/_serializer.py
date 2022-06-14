from dataclasses import dataclass
from typing import BinaryIO, Union, List

from serialization_tools.structx import Struct

from relic.chunky import _abc
from relic.chunky._abc import _ChunkLazyInfo
from relic.chunky._core import ChunkType, MagicWord, Version
from relic.chunky._serializer import ChunkTypeSerializer, chunk_type_serializer, RawChunk
from relic.chunky.errors import ChunkNameError
from relic.chunky.protocols import StreamSerializer, T
from relic.chunky.v3_1.core import ChunkMeta, FolderChunk, RawDataChunk, Chunky, ChunkyMetadata, version


@dataclass
class _ChunkHeader:
    chunk_type: ChunkType
    chunk_id: str
    version: int
    size: int
    name: str
    unk_a: int
    unk_b: int


@dataclass
class ChunkHeaderSerializer(StreamSerializer[_ChunkHeader]):
    chunk_type_serializer: ChunkTypeSerializer
    layout: Struct

    def unpack(self, stream: BinaryIO) -> _ChunkHeader:
        chunk_type = self.chunk_type_serializer.unpack(stream)
        chunk_id, version, size, name_size, unk_a, unk_b = self.layout.unpack_stream(stream)
        name_buffer = stream.read(name_size)
        try:
            name = name_buffer.rstrip(b"\0").decode("ascii")
        except UnicodeDecodeError as e:
            raise ChunkNameError(name_buffer) from e
        return _ChunkHeader(chunk_type, chunk_id, version, size, name, unk_a, unk_b)

    def pack(self, stream: BinaryIO, packable: _ChunkHeader) -> int:
        written = 0
        written += self.chunk_type_serializer.pack(stream, packable.chunk_type)
        name_buffer = packable.name.encode("ascii")
        args = packable.chunk_id, packable.version, packable.chunk_type, len(name_buffer), packable.unk_a, packable.unk_b
        written += self.layout.pack(args)
        written += stream.write(name_buffer)
        return written


AnyRawChunk = Union[FolderChunk, RawChunk]


@dataclass
class RawChunkSerializer(StreamSerializer[RawChunk]):
    header_serializer: ChunkHeaderSerializer

    @staticmethod
    def _unpack_data(stream: BinaryIO, header: _ChunkHeader):
        metadata = ChunkMeta(header.name, header.version, header.unk_a, header.unk_b)
        start, size = stream.tell(), header.size
        lazy_info = _ChunkLazyInfo(start, size, stream)
        stream.seek(size, 1)  # advance stream
        return _abc.RawDataChunk(header.chunk_id, metadata, None, None, lazy_info)

    def _pack_data(self, stream: BinaryIO, chunk: RawDataChunk):
        header = _ChunkHeader(chunk.type, chunk.id, chunk.metadata.version, len(chunk.data), chunk.metadata.name, chunk.metadata.unk_a, chunk.metadata.unk_b)
        written = 0
        written += self.header_serializer.pack(stream, header)
        written += stream.write(chunk.data)
        return written

    def _unpack_folder(self, stream: BinaryIO, header: _ChunkHeader):
        metadata = ChunkMeta(header.name, header.version, header.unk_a, header.unk_b)
        start, size = stream.tell(), header.size
        sub_folders = []
        data_chunks = []
        root = FolderChunk(header.chunk_id, metadata, folders=sub_folders, data_chunks=data_chunks, parent=None)
        while start + size <= stream.tell():
            chunk = self.unpack(stream)
            chunk.parent = root
            if chunk.type == ChunkType.Data:
                data_chunks.append(chunk)
            elif chunk.type == ChunkType.Folder:
                sub_folders.append(chunk)
            else:
                raise NotImplementedError
        if start + size != stream.tell():
            raise NotImplementedError

        return root

    def _pack_folder(self, stream: BinaryIO, chunk: FolderChunk):
        jump_back = stream.tell()
        header = _ChunkHeader(chunk.type.value, chunk.id, chunk.metadata.version, 0, chunk.metadata.name, chunk.metadata.unk_a, chunk.metadata.unk_b)
        written = 0
        written += self.header_serializer.pack(stream, header)
        size = 0
        for data in chunk.data_chunks:
            size += self._pack_data(stream, data)
        for folder in chunk.folders:
            size += self._pack_folder(stream, folder)
        written += size

        # Fix size
        jump_to = stream.tell()
        stream.seek(jump_back)
        header.size = size
        self.header_serializer.pack(stream, header)  # already accounted for written; don't increase again
        stream.seek(jump_to)

        return written

    def unpack(self, stream: BinaryIO) -> RawChunk:
        header = self.header_serializer.unpack(stream)
        if header.chunk_type == ChunkType.Data:
            return self._unpack_data(stream, header)
        elif header.chunk_type == ChunkType.Folder:
            return self._unpack_folder(stream, header)

    def pack(self, stream: BinaryIO, packable: RawChunk) -> int:
        if packable.type == ChunkType.Data:
            return self._pack_data(stream, packable)
        elif packable.type == ChunkType.Folder:
            return self._pack_folder(stream, packable)
        else:
            raise NotImplementedError


# @dataclass
# class RawChunkySerializer(StreamSerializer[RawChunky]):

@dataclass
class APISerializer(_abc.APISerializer[Chunky]):
    version:Version
    # _chunky_meta_serializer:StreamSerializer[] # NO META in v1.1
    _chunk_serializer: RawChunkSerializer
    _chunky_meta_serializer: StreamSerializer[ChunkyMetadata]

    def read(self, stream: BinaryIO, lazy: bool = False) -> Chunky:
        MagicWord.read_magic_word(stream)
        version = Version.unpack(stream)
        if version != self.version:
            raise NotImplementedError # VersionMismatchError()
        meta = self._chunky_meta_serializer.unpack(stream)
        start = stream.tell()
        stream.seek(0, 2)  # jump to end
        end = stream.tell()
        stream.seek(start)
        folders: List[FolderChunk] = []
        data_chunks: List[RawDataChunk] = []
        while stream.tell() < end:
            chunk = self._chunk_serializer.unpack(stream)
            if chunk.type == ChunkType.Data:
                data_chunks.append(chunk)
            elif chunk.type == ChunkType.Folder:
                folders.append(chunk)
            else:
                raise NotImplementedError

        if not lazy:
            for dchunk in data_chunks:
                if dchunk._lazy_info is not None:
                    dchunk.data = dchunk._lazy_info.read()
                    dchunk._lazy_info = None
                else:
                    raise NotImplementedError
            for folder in folders:
                for _, _, sub_dchunks in folder.walk():
                    for dchunk in sub_dchunks:
                        if dchunk._lazy_info is not None:
                            dchunk.data = dchunk._lazy_info.read()
                            dchunk._lazy_info = None
                        else:
                            raise NotImplementedError
        return Chunky(meta, folders, data_chunks)

    def write(self, stream: BinaryIO, chunky: Chunky) -> int:
        written = 0
        written += MagicWord.write_magic_word(stream)
        written += self._chunky_meta_serializer.pack(stream, chunky.metadata)
        # writing is so much easier than reading
        for folder in chunky.folders:
            written += self._chunk_serializer.pack(stream, folder)
        for file in chunky.folders:
            written += self._chunk_serializer.pack(stream, file)
        return written


@dataclass
class ChunkyMetadataSerializer(StreamSerializer[ChunkyMetadata]):
    layout: Struct

    def unpack(self, stream: BinaryIO) -> ChunkyMetadata:
        _36, _28, _1 = self.layout.unpack_stream(stream)
        if (_36, _28, _1) != ChunkyMetadata.RESERVED:
            raise NotImplementedError  # MismatchError
        return ChunkyMetadata(_36, _28, _1)

    def pack(self, stream: BinaryIO, packable: ChunkyMetadata) -> int:
        args = packable.rsv_a_thirty_six, packable.rsv_b_twenty_eight, packable.rsv_c_one
        if args != ChunkyMetadata.RESERVED:
            raise NotImplementedError  # MismatchError
        return self.layout.pack_stream(stream, *args)


# instantiate
chunk_header_serializer = ChunkHeaderSerializer(chunk_type_serializer, Struct("<4s 3L 2L"))
raw_chunk_serializer = RawChunkSerializer(chunk_header_serializer)
chunky_meta_serializer = ChunkyMetadataSerializer(Struct("3I"))
api_serializer = APISerializer(version,raw_chunk_serializer, chunky_meta_serializer)
