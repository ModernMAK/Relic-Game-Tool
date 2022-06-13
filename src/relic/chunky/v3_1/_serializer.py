from dataclasses import dataclass
from typing import BinaryIO

from serialization_tools.structx import Struct

from relic.chunky.protocols import StreamSerializer
from relic.chunky.v3_1.core import ChunkyMetadata


@dataclass
class ChunkyMetadataSerializer(StreamSerializer[ChunkyMetadata]):
    layout: Struct

    def unpack(self, stream: BinaryIO) -> ChunkyMetadata:
        args = self.layout.unpack_stream(stream)
        assert args == ChunkyMetadata.RESERVED
        return ChunkyMetadata(*args)


    def pack(self, stream: BinaryIO, packable: ChunkyMetadata) -> int:
        assert pa
        return ChunkyMetadata()




