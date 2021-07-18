import struct
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO

from relic.shared import unpack_from_stream

_data_chunk_magic_word = "DATA"
_folder_chunk_magic_word = "FOLD"
_chunk_header_layout = struct.Struct("< 4s 4s L L L")


class ChunkType(Enum):
    Folder = "FOLD"
    Data = "DATA"



@dataclass
class ChunkHeader:
    type: ChunkType
    id: str
    version: int
    size: int
    # name_size: int
    name: str

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'ChunkHeader':
        args = unpack_from_stream(_chunk_header_layout, stream)
        type = ChunkType(args[0].decode("ascii"))
        id = args[1].decode("ascii")
        version, size = args[2:3]
        name = stream.read(args[4]).decode("ascii").rstrip("\x00")

        header = ChunkHeader(type, id, version, size, name)
        if validate and type not in [ChunkType.Folder, ChunkType.Data]:
            err_pos = stream.tell() - _chunk_header_layout.size
            raise TypeError(f"Type not valid! '{header.type}' @{err_pos} ~ 0x {hex(err_pos)[2:]} ~ [{buffer}]")
        return header
