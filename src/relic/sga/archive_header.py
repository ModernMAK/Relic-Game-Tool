from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO, Optional

from relic.sga.shared import ARCHIVE_MAGIC, Version, FilenameOffsetInfo, OffsetInfo, DowIII_Version, DowI_Version, \
    DowII_Version
from relic.shared import unpack_from_stream


@dataclass
class ArchiveHeader:
    __NAME_SIZE = 128
    __VERSION_LAYOUT = Struct(f"< 2H")
    __v2_LAYOUT = Struct(f"< 16s {__NAME_SIZE}s 16s")
    __v5_LAYOUT = __v2_LAYOUT
    __v9_LAYOUT = Struct(f"< {__NAME_SIZE}s")

    version: Version
    name: str
    checksum_a: Optional[bytes] = None
    checksum_b: Optional[bytes] = None

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveHeader':
        if read_magic:
            ARCHIVE_MAGIC.assert_magic_word(stream, True)
        version_args = unpack_from_stream(cls.__VERSION_LAYOUT, stream)
        version = Version(*version_args)
        if version == DowIII_Version:
            args = unpack_from_stream(cls.__v9_LAYOUT, stream)
            name = args[0].decode("utf-16-le").rstrip("\x00")
            return ArchiveHeader(version, name)

        elif version in [DowII_Version, DowI_Version]:
            args = unpack_from_stream(cls.__v2_LAYOUT, stream)
            md5_a = args[0]
            name = args[1].decode("utf-16-le").rstrip("\x00")
            md5_b = args[2]
            return ArchiveHeader(version, name, md5_a, md5_b)
        else:
            raise NotImplementedError(version)

    # def repack(self, stream: BinaryIO, write_magic: bool = True) -> int:
    #     written = 0
    #     if write_magic:
    #         written += ARCHIVE_MAGIC.write_magic_word(stream)
    #     args = astuple(self)
    #     pre = (args[0].major, args[0].minor)
    #     name = args[5].encode("utf-16-le")
    #     # padding_size = _NAME_SIZE - len(name)
    #     # name += bytes([0x00] * padding_size)
    #     post = args[6:10]
    #     written += pack_into_stream(_HEADER_LAYOUT, stream, *pre, name, *post)
    #     return written


@dataclass
class ArchiveTableOfContents:  # 24 bytes
    # Knowing my luck this is also subject to change
    descriptions_info: OffsetInfo
    folders_info: OffsetInfo
    files_info: OffsetInfo
    filenames_info: FilenameOffsetInfo

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version) -> 'ArchiveTableOfContents':
        toc_offset = stream.tell()
        descriptions_info = OffsetInfo.unpack(stream, toc_offset, version)
        folders_info = OffsetInfo.unpack(stream, toc_offset, version)
        files_info = OffsetInfo.unpack(stream, toc_offset, version)
        filenames_info = FilenameOffsetInfo.unpack(stream, toc_offset, version)
        return ArchiveTableOfContents(descriptions_info, folders_info, files_info, filenames_info)


# Alias
ArchiveToC = ArchiveTableOfContents


@dataclass
class ArchiveSubHeader:
    __v2_LAYOUT = Struct("< 2L")
    __v5_LAYOUT = Struct("< 6L")
    __v9_LAYOUT = Struct("< Q L Q 4L 256s")
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
    def unpack(cls, stream: BinaryIO, version: Version = DowI_Version) -> 'ArchiveSubHeader':
        if DowI_Version == version:
            toc_size, data_off = unpack_from_stream(cls.__v2_LAYOUT, stream)
            toc_offset = stream.tell()
            if toc_size + toc_offset != data_off:
                raise Exception(
                    f"Invalid Data Offset, rel: '{toc_size}', abs_off: '{data_off}' dif: '{data_off - toc_size}'")
            return ArchiveSubHeader(toc_size, data_off, toc_offset)
        elif DowII_Version == version:
            toc_size, data_off, toc_off, unk_one, unk_zero, unk_b = unpack_from_stream(cls.__v5_LAYOUT, stream)
            return ArchiveSubHeader(toc_size, data_off, toc_off, unk_v5_one=unk_one, unk_v5_zero=unk_zero,
                                    unk_v5_b=unk_b)
        elif DowIII_Version == version:
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
class ArchiveInfo:
    header: ArchiveHeader
    sub_header: ArchiveSubHeader
    table_of_contents: ArchiveToC

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveInfo':
        header = ArchiveHeader.unpack(stream, read_magic=read_magic)
        sub_header = ArchiveSubHeader.unpack(stream, header.version)
        stream.seek(sub_header.toc_offset)
        toc = ArchiveToC.unpack(stream, header.version)
        return ArchiveInfo(header, sub_header, toc)
