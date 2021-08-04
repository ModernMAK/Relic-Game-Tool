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
    __v9_LAYOUT = Struct("< Q L Q 4L 160s")
    # V2.0 2L (8)
    #   Relative Offset (TOC SIZE!!!)
    #       While reading my notes, I realaized that 'Relative Offset' would be the size of the TOC Header + TOC Data
    #       Specifically 'data_offset - toc_offset'
    #           If Data_Offset is aboslute offset, and TOC Offset is always 180 (which it is in v2)
    #           Then TOC size lines up with what we know about this field!
    #   Absolute Offset
    # V5.0 6L (24)
    #   TOC Size
    #   Data Offset (Absolute)
    #   TOC Offset (Absolute)
    #   1
    #   ??? (0)
    #   ??? (Garbage?)
    # V9.0
    #   TOC Offset (Absolute) (Long?)
    #   TOC Size
    #   Data Offset?        This points to 78 DA which is standard for a zlib header (Long?)
    #   Data Size?          This value is the difference between TOC offset and Data Offset
    #   ??? (0)
    #   ??? (1)
    #   ??? (Garbage?)
    #   160 bytes of ???

    # This is the size of the TOC Header + TOC Data
    # For DOW 2; this is typically the size of the file - toc_offset
    # For DOW 1; this is typically the data_offset - toc_offset
    toc_size: int
    data_offset: int
    # To make reading TOC easier (code-wise); this is always included, despite not exisitng before v5
    toc_offset: int
    # V5 Exclusives
    unk_v5_one: Optional[int] = None
    unk_v5_zero: Optional[int] = None
    unk_v5_b: Optional[int] = None
    # V9 Exclusives
    unk_v9_a: Optional[int] = None
    unk_v9_zero: Optional[int] = None
    unk_v9_one: Optional[int] = None
    unk_v9_160_bytes: Optional[bytes] = None
    unk_v9_data_size: Optional[int] = None

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version = Version.DowI_Version()) -> 'ArchiveSubHeader':
        if version.DowI_Version() == version:
            toc_size, data_off = unpack_from_stream(cls.__v2_LAYOUT, stream)
            toc_offset = stream.tell()
            if toc_size + toc_offset != data_off:
                raise Exception(
                    f"Invalid Data Offset, rel: '{toc_size}', abs_off: '{data_off}' dif: '{data_off - toc_size}'")
            return ArchiveSubHeader(toc_size, data_off, toc_offset)
        elif version.DowII_Version() == version:
            toc_size, data_off, toc_off, unk_one, unk_zero, unk_b = unpack_from_stream(cls.__v5_LAYOUT, stream)
            return ArchiveSubHeader(toc_size, data_off, toc_off, unk_v5_one=unk_one, unk_v5_zero=unk_zero,
                                    unk_v5_b=unk_b)
        elif version.DowIII_Version() == version:
            args = unpack_from_stream(cls.__v9_LAYOUT, stream)
            unk_zero_c, unk_one_d, unk_e = args[4], args[5], args[6]
            unk_160 = args[7]

            toc_offset, toc_size, data_offset, data_size = args[0], args[1], args[2], args[3]

            assert unk_zero_c == 0, (unk_zero_c, 0, (args))
            assert unk_one_d == 1, (unk_one_d, 1, (args))

            return ArchiveSubHeader(
                toc_size, data_offset, toc_offset,
                unk_v9_zero=unk_zero_c, unk_v9_one=unk_one_d, unk_v9_a=unk_e, unk_v9_160_bytes=unk_160)
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
