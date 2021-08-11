from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO, Optional, List

from relic.chunky.version import ChunkyVersion
from relic.shared import Version
from relic.util.struct_util import unpack_from_stream, pack_into_stream

RELIC_CHUNKY_HEADER_LAYOUT = Struct("< 4s L L")

V3_1_LAYOUT = Struct("< L L L")


@dataclass
class RelicChunkyHeader:
    type_br: str
    version: Version
    three_point_one_args: Optional[List[int]] = None

    @classmethod
    def unpack(cls, stream: BinaryIO):
        type_br, v_major, v_minor = unpack_from_stream(RELIC_CHUNKY_HEADER_LAYOUT, stream)
        version = Version(v_major, v_minor)
        type_br = type_br.decode("ascii")
        v3_args = None
        if version == ChunkyVersion.v3_1:
            v3_args = unpack_from_stream(V3_1_LAYOUT, stream)
            # Always these 3 values from what I've looked at so far. Why?
            # 36 is the position of the first chunk  in the ones I've looked at
            assert v3_args[0] == 36
            # 28 is a pointer to itself (28); perhaps the size of the Header?
            assert v3_args[1] == 28
            # Reserved 1?
            assert v3_args[2] == 1

        return RelicChunkyHeader(type_br, version, v3_args)

    def pack(self, stream: BinaryIO) -> int:
        written = 0
        args = self.type_br.encode("ascii"), self.version.major, self.version.minor
        written += pack_into_stream(RELIC_CHUNKY_HEADER_LAYOUT, stream, *args)
        if self.version == ChunkyVersion.v3_1:
            v3_args = self.three_point_one_args
            written += pack_into_stream(V3_1_LAYOUT, stream, *v3_args)
        return written

    @classmethod
    def default(cls, version: Version = None) -> 'RelicChunkyHeader':
        version = version or Version(1, 1)
        return RelicChunkyHeader("\r\n\x1a\0", version)

    def __eq__(self, other):
        if self is other:
            return True
        elif other is None:
            return False
        elif isinstance(other, RelicChunkyHeader):
            if self.version != other.version:
                return False
            if self.version == ChunkyVersion.v3_1:
                for l, r in zip(self.three_point_one_args, other.three_point_one_args):
                    if l != r:
                        return False
            return self.type_br == other.type_br
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    def copy(self) -> 'RelicChunkyHeader':
        v3_1_args = [v for v in self.three_point_one_args] if self.three_point_one_args else None
        return RelicChunkyHeader(self.type_br, self.version, v3_1_args)
