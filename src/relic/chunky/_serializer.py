from __future__ import annotations
from enum import Enum
from typing import Union, ClassVar, BinaryIO

from archive_tools.structx import Struct

from relic.chunky._core import ChunkType
from relic.chunky.errors import ChunkTypeError
from relic.chunky.protocols import StreamSerializer, T


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


chunk_type_serializer = ChunkTypeSerializer(Struct("<4s"))
