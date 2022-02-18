from dataclasses import dataclass
from archive_tools.structx import Struct
from typing import BinaryIO, Optional

from relic.sga.shared import ARCHIVE_MAGIC, Version, FilenameOffsetInfo, OffsetInfo, SgaVersion


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

    def __eq__(self, other) -> bool:
        if self is other:
            return True
        elif isinstance(other, ArchiveHeader):
            if self.version == other.version:
                if self.version in [SgaVersion.Dow2, SgaVersion.Dow]:
                    if self.checksum_a != other.checksum_a or self.checksum_b != other.checksum_b:
                        return False
                return self.name == other.name
            else:
                return False

    def __ne__(self, other):
        return not (self == other)

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveHeader':
        if read_magic:
            ARCHIVE_MAGIC.assert_magic_word(stream, True)
        version_args = cls.__VERSION_LAYOUT.unpack_stream(stream)
        version = Version(*version_args)
        if version == SgaVersion.Dow3:
            args = cls.__v9_LAYOUT.unpack_stream( stream)
            name = args[0].decode("utf-16-le").rstrip("\x00")
            return ArchiveHeader(version, name)

        elif version in [SgaVersion.Dow2, SgaVersion.Dow]:
            args = cls.__v2_LAYOUT.unpack_stream(stream)
            md5_a = args[0]
            name = args[1].decode("utf-16-le").rstrip("\x00")
            md5_b = args[2]
            return ArchiveHeader(version, name, md5_a, md5_b)
        else:
            raise NotImplementedError(version)

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        written = 0
        if write_magic:
            written += ARCHIVE_MAGIC.write_magic_word(stream)
            written += self.__VERSION_LAYOUT.pack_stream(stream, self.version.major, self.version.minor)
        if self.version == SgaVersion.Dow3:
            written += self.__v9_LAYOUT.pack_stream(stream, self.name.encode("utf-16-le"))
        elif self.version in [SgaVersion.Dow2, SgaVersion.Dow]:
            args = self.checksum_a, self.name.encode("utf-16-le"), self.checksum_b
            written += self.__v2_LAYOUT.pack_stream(stream, *args)
        else:
            raise NotImplementedError(self.version)
        return written


@dataclass
class ArchiveTableOfContents:
    drive_info: OffsetInfo
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

    @classmethod
    def get_size(cls, version: SgaVersion) -> int:
        _sizes = {SgaVersion.Dow: 24, SgaVersion.Dow2: 24, SgaVersion.Dow3: 32}
        return _sizes[version]

    def pack(self, stream: BinaryIO, version: Version) -> int:
        written = 0
        written += self.drive_info.pack(stream, version)
        written += self.folders_info.pack(stream, version)
        written += self.files_info.pack(stream, version)
        written += self.filenames_info.pack(stream, version)
        return written


# Alias
ArchiveToC = ArchiveTableOfContents


@dataclass
class ArchiveSubHeader:
    __v2_LAYOUT = Struct("< 2L")
    __v5_LAYOUT = Struct("< 6L")
    __v9_LAYOUT = Struct("< Q L Q 4L 256s")
    # V2.0 2L (8)
    #   Relative Offset (TOC SIZE!!!)
    #       While reading my notes, I realized that 'Relative Offset' would be the size of the TOC Header + TOC Data
    #       Specifically 'data_offset - toc_offset'
    #           If Data_Offset is absolute offset, and TOC Offset is always 180 (which it is in v2)
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
    # To make reading TOC easier (code-wise); this is always included, despite not existing before v5
    toc_offset: int
    # V5 Exclusives
    unk_v5_one: Optional[int] = None
    unk_v5_zero: Optional[int] = None
    unk_v5_b: Optional[int] = None
    # V9 Exclusives
    unk_v9_a: Optional[int] = None
    unk_v9_zero: Optional[int] = None
    unk_v9_one: Optional[int] = None
    unk_v9_256_bytes: Optional[bytes] = None
    data_size: Optional[int] = None

    # We need to know version to do proper comparisons
    def equal(self, other: 'ArchiveSubHeader', version: Version) -> bool:
        if version == SgaVersion.Dow:
            return self.toc_size == other.toc_size and self.data_offset == other.data_offset
        elif version == SgaVersion.Dow2:
            return self.toc_size == other.toc_size and self.data_offset == other.data_offset and \
                   self.toc_offset == other.toc_offset and self.unk_v5_one == other.unk_v5_one and \
                   self.unk_v5_zero == other.unk_v5_zero and self.unk_v5_b == other.unk_v5_b
        elif version == SgaVersion.Dow3:
            for i in range(256):
                if self.unk_v9_256_bytes[i] != other.unk_v9_256_bytes[i]:
                    return False
            return self.toc_size == other.toc_size and self.data_offset == other.data_offset and \
                   self.toc_offset == other.toc_offset and self.unk_v9_one == other.unk_v9_one and \
                   self.unk_v9_zero == other.unk_v9_zero and self.unk_v9_a == other.unk_v9_a and \
                   self.data_size == other.data_size

    @classmethod
    def default(cls, version: Version) -> 'ArchiveSubHeader':
        if version == SgaVersion.Dow:
            return ArchiveSubHeader(0, 0, 0)
        elif version == SgaVersion.Dow2:
            return ArchiveSubHeader(0, 0, 0, 1, 0, 0)
        elif version == SgaVersion.Dow3:
            return ArchiveSubHeader(0, 0, 0, None, None, None, 0, 0, 1, bytes([0x00] * 256), 0)

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version = SgaVersion.Dow) -> 'ArchiveSubHeader':
        if SgaVersion.Dow == version:
            toc_size, data_off = cls.__v2_LAYOUT.unpack_stream(stream)
            toc_offset = stream.tell()
            if toc_size + toc_offset != data_off:
                raise Exception(
                    f"Invalid Data Offset, rel: '{toc_size}', abs_off: '{data_off}' dif: '{data_off - toc_size}'")
            return ArchiveSubHeader(toc_size, data_off, toc_offset)
        elif SgaVersion.Dow2 == version:
            toc_size, data_off, toc_off, unk_one, unk_zero, unk_b = cls.__v5_LAYOUT.unpack_stream(stream)
            return ArchiveSubHeader(toc_size, data_off, toc_off, unk_v5_one=unk_one, unk_v5_zero=unk_zero,
                                    unk_v5_b=unk_b)
        elif SgaVersion.Dow3 == version:
            args = cls.__v9_LAYOUT.unpack_stream(stream)
            unk_zero_c, unk_one_d, unk_e = args[4], args[5], args[6]
            unk_160 = args[7]

            toc_offset, toc_size, data_offset, data_size = args[0], args[1], args[2], args[3]

            assert unk_zero_c == 0, (unk_zero_c, 0, args)
            assert unk_one_d == 1, (unk_one_d, 1, args)

            return ArchiveSubHeader(
                toc_size, data_offset, toc_offset,
                unk_v9_zero=unk_zero_c, unk_v9_one=unk_one_d, unk_v9_a=unk_e, unk_v9_256_bytes=unk_160)
        else:
            raise NotImplementedError(version)

    def pack(self, stream: BinaryIO, version: Version) -> int:
        if SgaVersion.Dow == version:
            args = self.toc_size, self.data_offset
            return self.__v2_LAYOUT.pack_stream(stream, *args)
        elif SgaVersion.Dow2 == version:
            args = self.toc_size, self.data_offset, self.toc_offset, self.unk_v5_one, self.unk_v5_zero, self.unk_v5_b
            return self.__v5_LAYOUT.pack_stream(stream, *args)
        elif SgaVersion.Dow3 == version:
            args = self.toc_offset, self.toc_size, self.data_offset, self.data_size, self.unk_v9_zero, \
                   self.unk_v9_one, self.unk_v9_a, self.unk_v9_256_bytes
            return self.__v9_LAYOUT.pack_stream(stream, *args)
        else:
            raise NotImplementedError(version)

    @classmethod
    def get_size(cls, version: SgaVersion):
        sizes = {SgaVersion.Dow: cls.__v2_LAYOUT.size, SgaVersion.Dow2: cls.__v5_LAYOUT.size,
                 SgaVersion.Dow3: cls.__v9_LAYOUT.size}
        return sizes[version]


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
