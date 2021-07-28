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
    # BLANK = "\x00\x00\x00\x00"


@dataclass
class ChunkHeader:
    type: ChunkType
    id: str
    version: int
    size: int
    # name_size: int
    name: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ChunkHeader':
        args = unpack_from_stream(_chunk_header_layout, stream)
        try:
            type = ChunkType(args[0].decode("ascii"))
        except ValueError:
            err_pos = stream.tell() - _chunk_header_layout.size
            raise TypeError(f"Type not valid! '{args[0]}' @{err_pos} ~ 0x {hex(err_pos)[2:]}")

        id = args[1].decode("ascii").strip("\x00")  # .lstrip("\x00")
        version, size = args[2:4]
        raw_name = stream.read(args[4])
        try:
            name = raw_name.decode("ascii").rstrip("\x00")
        except UnicodeError:
            err_pos = stream.tell() - _chunk_header_layout.size
            raise TypeError(f"Name not valid! '{raw_name}' @{err_pos} ~ 0x {hex(err_pos)[2:]}")

        header = ChunkHeader(type, id, version, size, name)
        return header
