from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO

from relic.sga.offset_info import OffsetInfo
from relic.sga.shared import read_name
from relic.shared import unpack_from_stream


@dataclass
class FolderHeader:
    __FOLDER_HEADER_LAYOUT = Struct("< L H H H H")

    name_offset: int
    first_sub: int
    last_sub: int
    first_filename: int
    last_filename: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'FolderHeader':
        return FolderHeader(*unpack_from_stream(cls.__FOLDER_HEADER_LAYOUT, stream))

    def read_name(self, stream: BinaryIO, offset: OffsetInfo) -> str:
        return read_name(stream, offset, self.name_offset)
