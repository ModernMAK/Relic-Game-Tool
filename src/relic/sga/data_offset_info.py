from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO

from relic.sga.shared import ARCHIVE_HEADER_OFFSET
from relic.shared import unpack_from_stream, pack_into_stream


@dataclass
class DataOffsetInfo:
    __DATA_OFFSET_LAYOUT = Struct("< L L")

    offset_relative: int
    offset_absolute: int

    @property
    def start_relative(self):
        return self.offset_relative

    @property
    def start_abs(self):
        return self.offset_relative + ARCHIVE_HEADER_OFFSET

    @property
    def end(self):
        return self.offset_absolute

    @property
    def size(self):
        return self.end - self.start_abs

    @property
    def valid(self) -> bool:
        return self.offset_absolute == self.start_abs

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'DataOffsetInfo':
        args = unpack_from_stream(cls.__DATA_OFFSET_LAYOUT, stream)
        archive = DataOffsetInfo(*args)
        # DONE
        if validate and not archive.valid:
            raise Exception("Invalid Data Offset")

        return archive

    def pack(self, stream: BinaryIO) -> int:
        args = (self.offset_relative, self.offset_absolute)
        return pack_into_stream(self.__DATA_OFFSET_LAYOUT, stream, *args)
