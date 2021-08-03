from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO, Optional

from relic.sga.shared import ARCHIVE_HEADER_OFFSET
from relic.sga.version import Version
from relic.shared import unpack_from_stream, pack_into_stream


@dataclass
class ArchiveSubHeader:
    __v2_LAYOUT = Struct("< 2L")
    __v5_LAYOUT = Struct("< 6L")
    # V2.0 2L (8)
    #   Relative Offset
    #   Absolute Offset
    # V5.0 6L (24)
    #   ???
    #   Data Offset (Absolute)
    #   TOC Offset (Absolute)
    #   1
    #   ??? (0)
    #   ??? (Garbage?)
    data_offset: int
    # To make reading TOC easier (code-wise); this is always included, despite not exisitng before v5
    toc_offset: int
    unk_a: Optional[int] = None
    unk_one: Optional[int] = None
    unk_zero: Optional[int] = None
    unk_b: Optional[int] = None

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version = Version.DowI_Version()) -> 'ArchiveSubHeader':
        if version.DowI_Version() == version:
            rel_off, abs_off = unpack_from_stream(cls.__v2_LAYOUT, stream)
            if rel_off + ARCHIVE_HEADER_OFFSET != abs_off:
                raise Exception(
                    f"Invalid Data Offset, rel: '{rel_off}', abs_off: '{abs_off}' dif: '{abs_off - rel_off}'")
            toc_offset = stream.tell()
            return ArchiveSubHeader(data_offset=abs_off, toc_offset=toc_offset)
        elif version.DowII_Version() == version:
            unk_a, data_off, toc_off, unk_one, unk_zero, unk_b = unpack_from_stream(cls.__v5_LAYOUT, stream)
            return ArchiveSubHeader(data_off, toc_off, unk_a, unk_one, unk_zero, unk_b)
        else:
            raise NotImplementedError(version)
        # args = unpack_from_stream(cls.__DATA_OFFSET_LAYOUT, stream)
        # archive = DataOffsetInfo(*args)
        # DONE
        # if validate and not archive.valid:
        #     raise Exception("Invalid Data Offset")

        # return archive


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
        # print("R:",self.offset_relative,"\tA:", self.offset_absolute)
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
