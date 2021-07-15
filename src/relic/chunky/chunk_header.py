import struct
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO

_data_chunk_magic_word = "DATA"
_folder_chunk_magic_word = "FOLD"
_chunk_header_layout = struct.Struct("< 4s 4s L L L")


class ChunkType(Enum):
    Folder = "FOLD"
    Data = "DATA"


#class ChunkId(Enum):
    # Info = "INFO"


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
        buffer = stream.read(_chunk_header_layout.size)
        type_str, id_str, version, size, name_size = _chunk_header_layout.unpack(buffer)
        type = ChunkType(type_str.decode("ascii"))
        id = id_str.decode("ascii")
        name = stream.read(name_size).decode("ascii").rstrip("\x00")

        header = ChunkHeader(type, id, version, size, name)
        if validate and type not in [ChunkType.Folder, ChunkType.Data]:
            err_pos = stream.tell() - _chunk_header_layout.size
            raise TypeError(f"Type not valid! '{header.type}' @{err_pos} ~ 0x {hex(err_pos)[2:]} ~ [{buffer}]")
        return header
