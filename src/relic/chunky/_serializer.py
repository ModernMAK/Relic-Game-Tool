from __future__ import annotations

from typing import BinaryIO

from serialization_tools.structx import Struct

from relic.chunky._core import ChunkType, ChunkFourCC
from relic.chunky.errors import ChunkTypeError
from relic.chunky.protocols import StreamSerializer


class ChunkTypeSerializer(StreamSerializer[ChunkType]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> ChunkType:
        buffer: bytes
        buffer, = self.layout.unpack_stream(stream)
        try:
            value: str = buffer.decode("ascii")
        except UnicodeDecodeError:
            raise ChunkTypeError(buffer)
        else:
            try:
                return ChunkType(value)
            except ValueError:
                raise ChunkTypeError(value)

    def pack(self, stream: BinaryIO, packable: ChunkType) -> int:
        return self.layout.pack_stream(stream, packable.value)


class ChunkFourCCSerializer(StreamSerializer[ChunkFourCC]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> ChunkFourCC:
        buffer: bytes
        buffer, = self.layout.unpack_stream(stream)
        value: str = buffer.decode("ascii")
        return ChunkFourCC(value)

    def pack(self, stream: BinaryIO, packable: ChunkFourCC) -> int:
        return self.layout.pack_stream(stream, packable.code)


chunk_type_serializer = ChunkTypeSerializer(Struct("<4s"))
chunk_cc_serializer = ChunkFourCCSerializer(Struct("<4s"))
