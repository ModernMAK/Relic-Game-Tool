from archive_tools.structx import Struct
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, Optional, List

from relic.chunky.version import ChunkyVersion
from relic.shared import Version

_data_chunk_magic_word = "DATA"
_folder_chunk_magic_word = "FOLD"
_chunk_header_layout = Struct("< 4s 4s L L L")


class ChunkType(Enum):
    Folder = "FOLD"
    Data = "DATA"
    # BLANK = "\x00\x00\x00\x00"


_v3_1_unks = Struct("< L L")


@dataclass
class ChunkHeader:
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
        args = _chunk_header_layout.unpack_stream(stream)
        try:
            type = ChunkType(args[0].decode("ascii"))
        except ValueError:
            err_pos = stream.tell() - _chunk_header_layout.size
            raise TypeError(f"Type not valid! '{args[0]}' @{err_pos} ~ 0x {hex(err_pos)[2:]}")

        unks_v3 = _v3_1_unks.unpack_stream(stream) if chunky_version == ChunkyVersion.v3_1 else None

        # ID can have nulls on both Left-side and right-side
        id = args[1].decode("ascii").strip("\x00")
        version, size = args[2:4]

        raw_name = stream.read(args[4])
        try:
            name = raw_name.decode("ascii").rstrip("\x00")
        except UnicodeError:
            err_pos = stream.tell() - _chunk_header_layout.size
            raise TypeError(f"Name not valid! '{raw_name}' @{err_pos} ~ 0x {hex(err_pos)[2:]}")

        header = ChunkHeader(type, id, version, size, name, unks_v3)
        return header

    def pack(self, stream: BinaryIO, chunky_version: Version) -> int:
        args = self.type.value.encode("ascii"), self.id.encode("ascii"), self.version, self.size, len(self.name)
        written = _chunk_header_layout.pack_stream(stream, *args)
        written += stream.write(self.name.encode("ascii"))
        if chunky_version == ChunkyVersion.v3_1:
            written += _v3_1_unks.pack_stream( stream, self.unk_v3_1)
        return written

    def copy(self) -> 'ChunkHeader':
        """Provided as a safe method of modifying Chunk Headers for packing."""
        unks_v3_1_copy = [v for v in self.unk_v3_1] if self.unk_v3_1 else None
        return ChunkHeader(self.type, self.id, self.version, self.size, self.name, unks_v3_1_copy)
