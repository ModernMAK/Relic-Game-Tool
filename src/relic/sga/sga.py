import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from os.path import join
from typing import ClassVar, Iterator, List, Tuple, Union, BinaryIO, Optional, Dict, Iterable, ForwardRef, Callable

from archive_tools.structx import Struct

from ..shared import Magic, MagicWalker, Version, VersionEnum, VersionLike, fix_extension_list, filter_path_by_extension, KW_LIST

ArchiveWalkResult = Tuple[str, Iterable['Folder'], Iterable['File']]

ARCHIVE_MAGIC = Magic(Struct("< 8s"), "_ARCHIVE")
ARCHIVE_MAGIC_WALKER = MagicWalker(ARCHIVE_MAGIC)

# Foward Refs
File = ForwardRef("File")
ArchiveInfo = ForwardRef("ArchiveInfo")
ArchiveSubHeader = ForwardRef("ArchiveSubHeader")
FolderHeader = ForwardRef("FolderHeader")


class SgaVersion(VersionEnum):
    Unsupported = None
    Dow = Version(2)
    Dow2 = Version(5)
    Dow3 = Version(9)


class FileCompressionFlag(Enum):
    # Compression flag is either 0 (Decompressed) or 16/32 which are both compressed
    # Aside from 0; these appear to be the Window-Sizes for the Zlib Compression (In KibiBytes)
    Decompressed = 0

    Compressed16 = 16
    Compressed32 = 32

    def compressed(self) -> bool:
        return self != FileCompressionFlag.Decompressed


@dataclass
class FileHeader:
    name_offset: int
    data_offset: int
    decompressed_size: int
    compressed_size: int

    @classmethod
    def unpack_version(cls, stream: BinaryIO, version: Version = SgaVersion.Dow) -> 'FileHeader':
        VERSIONS: Dict[VersionLike, Callable] = {
            SgaVersion.Dow: DowIFileHeader.unpack,
            SgaVersion.Dow2: DowIIFileHeader.unpack,
            SgaVersion.Dow3: DowIIIFileHeader.unpack,
        }
        unpacker = VERSIONS[version]
        return unpacker(stream)

    def pack_version(self, stream: BinaryIO, version: Version = SgaVersion.Dow) -> int:
        VERSIONS: Dict[VersionLike, Callable] = {
            SgaVersion.Dow: DowIFileHeader.pack,
            SgaVersion.Dow2: DowIIFileHeader.pack,
            SgaVersion.Dow3: DowIIIFileHeader.pack,
        }
        packer = VERSIONS[version]
        return packer(self, stream)

    @property
    def compressed(self):
        return self.compressed_size < self.decompressed_size

    def read_name_from_lookup(self, lookup: Dict[int, str], info: Optional[ArchiveInfo] = None) -> str:
        # If info is provided; use absolute values
        if info:
            offset = info.sub_header.toc_offset + info.table_of_contents.filenames_info.offset_relative + self.name_offset
        else:
            offset = self.name_offset
        try:
            return lookup[offset]
        except KeyError as e:
            raise KeyError(e, offset, lookup)

    def read_data(self, stream: BinaryIO, offset: ArchiveSubHeader) -> bytes:
        stream.seek(offset.data_offset + self.data_offset)
        return stream.read(self.compressed_size)


@dataclass
class DowIFileHeader(FileHeader):
    LAYOUT = Struct(f"<5L")
    compression_flag: FileCompressionFlag

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'DowIFileHeader':
        name_offset, compression_flag_value, data_offset, decompressed_size, compressed_size = cls.LAYOUT.unpack_stream(stream)
        compression_flag = FileCompressionFlag(compression_flag_value)
        return DowIFileHeader(name_offset, data_offset, decompressed_size, compressed_size, compression_flag)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.name_offset, self.compression_flag.value, self.data_offset, self.decompressed_size, self.compressed_size)

    @property
    def compressed(self):
        return self.compression_flag.compressed()


@dataclass
class DowIIFileHeader(FileHeader):
    LAYOUT = Struct(f"<5L H")
    unk_a: int
    unk_b: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'DowIIFileHeader':
        name_off, data_off, comp_size, decomp_size, unk_a, unk_b = cls.LAYOUT.unpack_stream(stream)
        # Name, File, Compressed, Decompressed, ???, ???
        return DowIIFileHeader(name_off, data_off, decomp_size, comp_size, unk_a, unk_b)

    def pack(self, stream: BinaryIO) -> int:
        return self.LAYOUT.pack_stream(stream, self.name_offset, self.data_offset, self.compressed_size, self.decompressed_size, self.unk_a, self.unk_b)


@dataclass
class DowIIIFileHeader(FileHeader):
    LAYOUT = Struct("< 7L H L")
    unk_a: int
    unk_b: int
    unk_c: int
    unk_d: int  # 256?
    unk_e: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'DowIIIFileHeader':
        name_off, unk_a, data_off, unk_b, comp_size, decomp_size, unk_c, unk_d, unk_e = cls.LAYOUT.unpack_stream(stream)
        # assert unk_a == 0, (unk_a, 0)
        # assert unk_b == 0, (unk_b, 0)

        # UNK_D is a new compression flag?!
        # if comp_size != decomp_size:
        #     assert unk_d in [256,512], ((comp_size, decomp_size), (unk_d, [256,512]), (name_off, unk_a, data_off, unk_b, comp_size, decomp_size, unk_c, unk_d, unk_e))
        # Pulling stuff out of my ass; but dividing them by the max block size gets you 7, 6 repsectively

        # Name, File, Compressed, Decompressed, ???, ???
        return DowIIIFileHeader(name_off, data_off, decomp_size, comp_size, unk_a, unk_b, unk_c, unk_d, unk_e)

    def pack(self, stream: BinaryIO) -> int:
        args = self.name_offset, self.unk_a, self.data_offset, self.unk_b, self.compressed_size, self.decompressed_size, self.unk_c, self.unk_d, self.unk_e
        return self.LAYOUT.pack_stream(stream, *args)


@dataclass
class File:
    header: FileHeader
    name: str
    data: bytes
    _decompressed: bool = False
    _parent_folder: Optional['Folder'] = None
    _parent_drive: Optional['VirtualDrive'] = None

    def __hash__(self):
        return id(self)

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: FileHeader,
               name_lookup: Dict[int, str]) -> 'File':
        name = info.read_name_from_lookup(name_lookup)
        data = info.read_data(stream, archive_info.sub_header)
        _decompressed = not info.compressed
        return File(info, name, data, _decompressed)

    def get_decompressed(self) -> bytes:
        if self._decompressed or not self.header.compressed:
            return self.data
        else:
            # zlib_header = Struct("2B").unpack(self.data[:2])
            # full_zlib_header = (zlib_header[0] & 0xF0) >> 4, zlib_header[0] & 0xF, \
            #                    (zlib_header[1] & 0b11000000) >> 6, (zlib_header[1] >> 5) & 0b1, zlib_header[1] & 0b11111
            # convert = {7: 32, 6: 16}
            # assert convert[full_zlib_header[0]] == self.header.compression_flag.value
            return zlib.decompress(self.data)

    def decompress(self):
        if not self._decompressed:
            self.data = self.get_decompressed()
            self._decompressed = True

    # Helper to read data from a stream; decompress will not modify the data field
    @contextmanager
    def open_readonly_stream(self, decompress: bool = True) -> BinaryIO:
        """Opens the 'File' for reading. The file is decompressed before reading if decompress is specified. The compressed data remains in
        self.data'."""
        buffer = self.get_decompressed() if decompress else self.data
        with BytesIO(buffer) as handle:
            yield handle

    @classmethod
    def filter_by_extension(cls, walk: Iterable['File'], whitelist: KW_LIST = None, blacklist: KW_LIST = None) -> \
            Iterable['File']:
        whitelist = fix_extension_list(whitelist)
        blacklist = fix_extension_list(blacklist)

        for f in walk:
            if filter_path_by_extension(f.name, whitelist, blacklist):
                yield f


@dataclass
class AbstractDirectory:
    folders: List['Folder']
    files: List['File']
    # Unfortunately these can't be 'defaults' or else they mess with subclasses
    __folder_count: Optional[int]
    __file_count: Optional[int]

    def folder_count(self, recalculate: bool = False) -> int:
        if not self.__folder_count or recalculate:
            self.__folder_count = len(self.folders)
            for f in self.folders:
                self.__folder_count += f.folder_count(recalculate)
        return self.__folder_count

    def file_count(self, recalculate: bool = False) -> int:
        if not self.__file_count or recalculate:
            self.__file_count = len(self.files)
            for f in self.folders:
                self.__file_count += f.file_count(recalculate)
        return self.__file_count

    @classmethod
    def __safe_join(cls, parent: str, *args):
        parent = parent or ""
        return join(parent, *args)

    # Folder names are full paths
    # File names are not?
    def _walk(self, name: str = None) -> ArchiveWalkResult:
        yield name, (f for f in self.folders), (f for f in self.files)
        for folder in self.folders:
            # parent = self.__safe_join(name, folder.name)
            # for child_walk in folder._walk(parent):
            for child_walk in folder.walk():
                yield child_walk

    def walk(self) -> ArchiveWalkResult:
        return self._walk()  # Default, no name given

    def get_from_path(self, *parts: str) -> Optional[Union['Folder', 'File']]:
        if len(parts) > 1:
            if parts[0][-1] == ":":  # If the first part is a drive
                full_path = parts[0] + join(*parts[1:])
            else:
                full_path = join(*parts)
        else:
            full_path = parts[0]

        folder_split = full_path.replace("/", "\\").split("\\", 1)
        if len(folder_split) > 1:
            folder_name, remaining_path = folder_split
            for folder in self.folders:
                if folder.name == folder_name:
                    return folder.get_from_path(remaining_path)
        else:
            remaining_path = folder_split[0]
            for folder in self.folders:
                if folder.name == remaining_path:
                    return folder
            for file in self.files:
                if file.name == remaining_path:
                    return file
            return None


@dataclass
class ArchiveRange:
    start: int
    end: int
    __iterable: Optional[Iterator] = None

    @property
    def size(self) -> int:
        return self.end - self.start

    # We don't use iterable to avoid x
    def __iter__(self) -> 'ArchiveRange':
        self.__iterable = iter(range(self.start, self.end))
        return self

    def __next__(self) -> int:
        return next(self.__iterable)


@dataclass
class OffsetInfo:
    __v2_LAYOUT = Struct("< L H")  # 6 bytes
    __v5_LAYOUT = __v2_LAYOUT
    __v9_LAYOUT = Struct("< L L")  # 8 bytes
    _LAYOUT = {SgaVersion.Dow3: __v9_LAYOUT, SgaVersion.Dow2: __v5_LAYOUT, SgaVersion.Dow: __v2_LAYOUT}

    toc_offset: int
    offset_relative: int
    count: int

    @property
    def offset_absolute(self) -> int:
        return self.toc_offset + self.offset_relative

    @offset_absolute.setter
    def offset_absolute(self, abs_offset: int):
        self.offset_relative = abs_offset - self.toc_offset

    @classmethod
    def unpack(cls, stream: BinaryIO, toc_offset: int, version: SgaVersion) -> 'OffsetInfo':

        if version in cls._LAYOUT:
            layout = cls._LAYOUT[version]
            args = layout.unpack_stream(stream)
            return OffsetInfo(toc_offset, *args)
        else:
            raise NotImplementedError(version)

    def pack(self, stream: BinaryIO, version: SgaVersion) -> int:
        if version in self._LAYOUT:
            layout = self._LAYOUT[version]
            args = (self.offset_relative, self.count)
            return layout.pack_stream(stream, *args)
        else:
            raise NotImplementedError(version)


@dataclass
class FilenameOffsetInfo(OffsetInfo):
    count: Optional[int] = None
    byte_size: Optional[int] = None

    @classmethod
    def read_string(cls, stream: BinaryIO, chunk_size: int = 512, strip_terminal: bool = True) -> str:
        start = stream.tell()
        prev = start
        while True:
            b = stream.read(chunk_size)
            now = stream.tell()
            if prev == now:
                raise EOFError()
            try:
                index = b.index(0x00) + 1  # +1 to include \00
                offset = prev - start
                stream.seek(start)
                s = stream.read(offset + index).decode("ascii")
                if strip_terminal:
                    s = s.rstrip("\x00")
                return s
            except ValueError:
                prev = now
                continue

    def get_name_lookup(self, stream: BinaryIO, use_absolute: bool = True) -> Dict[int, str]:
        temp = stream.tell()
        start = self.toc_offset + self.offset_relative
        stream.seek(start)
        d = {}
        if self.byte_size:
            buffer = stream.read(self.byte_size)
            with BytesIO(buffer) as reader:
                while reader.tell() != len(buffer):
                    offset = reader.tell()
                    if use_absolute:
                        offset += start  # Add because offset is relative to the start position
                    name = self.read_string(reader)
                    d[offset] = name
        elif self.count:
            for _ in range(self.count):
                offset = stream.tell()
                if not use_absolute:
                    offset -= start  # Subtract because offset is already abosolute
                name = self.read_string(stream)
                d[offset] = name
        else:
            raise NotImplementedError
        stream.seek(temp)
        return d

    @classmethod
    def unpack(cls, stream: BinaryIO, toc_offset: int, version: SgaVersion) -> 'FilenameOffsetInfo':
        basic = OffsetInfo.unpack(stream, toc_offset, version)
        if version == SgaVersion.Dow3:
            return FilenameOffsetInfo(basic.toc_offset, basic.offset_relative, None, basic.count)
        elif version in [SgaVersion.Dow2, SgaVersion.Dow]:
            return FilenameOffsetInfo(basic.toc_offset, basic.offset_relative, basic.count, None)

    def pack(self, stream: BinaryIO, version: SgaVersion) -> int:
        if version in self._LAYOUT:
            layout = self._LAYOUT[version]
            if version == SgaVersion.Dow3:
                args = self.offset_relative, self.byte_size
            elif version in [SgaVersion.Dow2, SgaVersion.Dow]:
                args = self.offset_relative, self.count
            else:
                raise NotImplementedError(version)

            return layout.pack_stream(stream, *args)
        else:
            raise NotImplementedError(version)


@dataclass
class VirtualDriveHeader:
    __v2_LAYOUT = Struct("< 64s 64s 5H")
    __v5_LAYOUT = __v2_LAYOUT
    __v9_LAYOUT = Struct("< 64s 64s 5L")
    __LAYOUT_MAP: ClassVar[Dict[VersionLike, Struct]] = {SgaVersion.Dow: __v2_LAYOUT, SgaVersion.Dow2: __v5_LAYOUT, SgaVersion.Dow3: __v9_LAYOUT}
    # The path of the drive (used in resolving archive paths)
    # E.G. 'data'
    path: str
    # The name of the drive (used in viewing assets?)
    # E.G. 'All'
    name: str
    # If this is a root folder; I bet this is first & last; just like Folder
    # first_subfolder: int
    # last_subfolder: int
    # first_file: int
    # last_file: int

    subfolder_range: ArchiveRange
    file_range: ArchiveRange
    # Special field for V_Drive, flags maybe?
    unk_a: int  # 0

    @classmethod
    def unpack(cls, stream: BinaryIO, version: VersionLike) -> 'VirtualDriveHeader':
        if version in cls.__LAYOUT_MAP:
            args = cls.__LAYOUT_MAP[version].unpack_stream(stream)
        else:
            raise NotImplementedError(version)

        category = args[0].decode("ascii").rstrip("\x00")
        name = args[1].decode("ascii").rstrip("\x00")
        subfolder_range = ArchiveRange(args[2], args[3])
        file_range = ArchiveRange(args[4], args[5])
        assert args[6] == args[2], args[2:]
        return VirtualDriveHeader(category, name, subfolder_range, file_range, args[6])

    def pack(self, stream: BinaryIO, version: VersionLike) -> int:
        if version in self.__LAYOUT_MAP:
            layout = self.__LAYOUT_MAP[version]
        else:
            raise NotImplementedError(version)
        args = self.path.encode("ascii"), self.name.encode("ascii"), self.subfolder_range.start, self.subfolder_range.end, self.file_range.start, self.file_range.end, self.unk_a
        return layout.pack_stream(stream, *args)


@dataclass
class VirtualDrive(AbstractDirectory):
    path: str
    name: str
    _info: VirtualDriveHeader

    @classmethod
    def create(cls, header: VirtualDriveHeader):
        path, name = header.path, header.name
        return VirtualDrive([], [], None, None, path, name, header)

    def load_folders(self, folders: List['Folder']):
        if self._info.subfolder_range.start < len(folders):
            for i in self._info.subfolder_range:
                if not folders[i]._parent_folder:
                    f = folders[i]
                    f._parent_drive = self
                    self.folders.append(f)

    def load_files(self, files: List['File']):
        if self._info.file_range.start < len(files):
            for i in self._info.file_range:
                if not files[i]._parent_folder:
                    f = files[i]
                    f._parent_drive = self
                    self.folders.append(f)

    def walk(self, specify_drive: bool = True) -> ArchiveWalkResult:  # Specify name for
        for root, folders, files in self._walk():
            if root:
                true_root = f"{self.path}:{root}" if specify_drive else root
            else:
                true_root = f"{self.path}:" if specify_drive else None

            yield true_root, folders, files

    # def build_header(self, ):


@dataclass
class ArchiveHeader:
    __NAME_SIZE = 128
    __VERSION_LAYOUT = Struct(f"< 2H")
    __v2_LAYOUT = Struct(f"< 16s {__NAME_SIZE}s 16s")
    __v5_LAYOUT = __v2_LAYOUT
    __v9_LAYOUT = Struct(f"< {__NAME_SIZE}s")

    version: VersionLike
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
            args = cls.__v9_LAYOUT.unpack_stream(stream)
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
    def unpack(cls, stream: BinaryIO, version: VersionLike) -> 'ArchiveTableOfContents':
        toc_offset = stream.tell()
        descriptions_info = OffsetInfo.unpack(stream, toc_offset, version)
        folders_info = OffsetInfo.unpack(stream, toc_offset, version)
        files_info = OffsetInfo.unpack(stream, toc_offset, version)
        filenames_info = FilenameOffsetInfo.unpack(stream, toc_offset, version)
        return ArchiveTableOfContents(descriptions_info, folders_info, files_info, filenames_info)

    @classmethod
    def get_size(cls, version: VersionLike) -> int:
        _sizes: Dict[VersionLike, int] = {SgaVersion.Dow: 24, SgaVersion.Dow2: 24, SgaVersion.Dow3: 32}
        return _sizes[version]

    def pack(self, stream: BinaryIO, version: VersionLike) -> int:
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
    __DowI_LAYOUT = __v2_LAYOUT
    __v5_LAYOUT = Struct("< 6L")
    __DowII_LAYOUT = __v5_LAYOUT
    __v9_LAYOUT = Struct("< Q L Q 4L 256s")
    __DowIII_LAYOUT = __v9_LAYOUT
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
    def equal(self, other: 'ArchiveSubHeader', version: VersionLike) -> bool:
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
    def default(cls, version: VersionLike) -> 'ArchiveSubHeader':
        if version == SgaVersion.Dow:
            return ArchiveSubHeader(0, 0, 0)
        elif version == SgaVersion.Dow2:
            return ArchiveSubHeader(0, 0, 0, 1, 0, 0)
        elif version == SgaVersion.Dow3:
            return ArchiveSubHeader(0, 0, 0, None, None, None, 0, 0, 1, bytes([0x00] * 256), 0)

    @classmethod
    def unpack(cls, stream: BinaryIO, version: VersionLike = SgaVersion.Dow) -> 'ArchiveSubHeader':
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

    def pack(self, stream: BinaryIO, version: VersionLike) -> int:
        if SgaVersion.Dow == version:
            args = self.toc_size, self.data_offset
            layout = self.__DowI_LAYOUT
        elif SgaVersion.Dow2 == version:
            args = self.toc_size, self.data_offset, self.toc_offset, self.unk_v5_one, self.unk_v5_zero, self.unk_v5_b
            layout = self.__DowII_LAYOUT
        elif SgaVersion.Dow3 == version:
            args = self.toc_offset, self.toc_size, self.data_offset, self.data_size, self.unk_v9_zero, \
                   self.unk_v9_one, self.unk_v9_a, self.unk_v9_256_bytes
            layout = self.__DowIII_LAYOUT
        else:
            raise NotImplementedError(version)
        return layout.pack_stream(stream, *args)

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


@dataclass
class SparseArchive:
    info: ArchiveInfo
    drives: List[VirtualDriveHeader]
    files: List[FileHeader]
    folders: List[FolderHeader]

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'SparseArchive':
        info = ArchiveInfo.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo) -> 'SparseArchive':
        version = archive_info.header.version
        desc_info = archive_info.table_of_contents.drive_info
        stream.seek(desc_info.offset_absolute, 0)
        descriptions = [VirtualDriveHeader.unpack(stream, version) for _ in range(desc_info.count)]

        fold_info = archive_info.table_of_contents.folders_info
        stream.seek(fold_info.offset_absolute, 0)
        folders = [FolderHeader.unpack(stream, version) for _ in range(fold_info.count)]

        file_info = archive_info.table_of_contents.files_info
        stream.seek(file_info.offset_absolute, 0)
        files = [FileHeader.unpack_version(stream, version) for _ in range(file_info.count)]

        return SparseArchive(archive_info, descriptions, files, folders)


@dataclass
class Archive:
    info: ArchiveInfo
    drives: List[VirtualDrive]

    # A helper to know the total # of files without performing a full walk
    _total_files: int = 0

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'Archive':
        info = SparseArchive.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive: SparseArchive) -> 'Archive':
        info = archive.info
        name_lookup = info.table_of_contents.filenames_info.get_name_lookup(stream, use_absolute=False)
        folders = [Folder.create(f, name_lookup) for f in archive.folders]
        files = [File.create(stream, info, f, name_lookup) for f in archive.files]
        for f in folders:
            f.load_folders(folders)
            f.load_files(files)

        drives = [VirtualDrive.create(d) for d in archive.drives]
        for d in drives:
            d.load_folders(folders)
            d.load_files(files)

        total_files = len(files)

        return Archive(info, drives, total_files)

    @classmethod
    def repack(cls, stream: BinaryIO, write_magic: bool = True):
        raise NotImplementedError

    def walk(self, specify_drive: bool = False) -> ArchiveWalkResult:
        for drive in self.drives:
            for root, folders, files in drive.walk(specify_drive):
                yield root, folders, files

    def get_from_path(self, *parts: str):
        if len(parts) > 1:
            if parts[0][-1] == ":":  # If the first part is a drive
                full_path = parts[0] + join(*parts[1:])
            else:
                full_path = join(*parts)
        else:
            full_path = parts[0]
        drive_split = full_path.split(":", 1)

        if len(drive_split) > 1:
            drive_path, path_to_file = drive_split
            for drive in self.drives:
                if drive.path == drive_path:
                    return drive.get_from_path(path_to_file)
        else:
            path_to_file = drive_split[0]
            for drive in self.drives:
                result = drive.get_from_path(path_to_file)
                if result:
                    return result


@dataclass
class FolderHeader:
    __v2_LAYOUT = Struct("< L 4H")  # 12
    __v5_LAYOUT = __v2_LAYOUT  # 12
    __v9_LAYOUT = Struct("< L 4L")  # 20
    __LAYOUT: ClassVar[Dict[Version, Struct]] = {SgaVersion.Dow: __v2_LAYOUT, SgaVersion.Dow2: __v5_LAYOUT, SgaVersion.Dow3: __v9_LAYOUT}

    name_offset: int
    subfolder_range: ArchiveRange
    file_range: ArchiveRange

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version) -> 'FolderHeader':
        if version in [SgaVersion.Dow, SgaVersion.Dow2]:
            args = cls.__v2_LAYOUT.unpack_stream(stream)
            subfolder_range = ArchiveRange(args[1], args[2])
            file_range = ArchiveRange(args[3], args[4])
            return FolderHeader(args[0], subfolder_range, file_range)
        elif version == SgaVersion.Dow3:
            args = cls.__v9_LAYOUT.unpack_stream(stream)
            subfolder_range = ArchiveRange(args[1], args[2])
            file_range = ArchiveRange(args[3], args[4])
            return FolderHeader(args[0], subfolder_range, file_range)
        else:
            raise NotImplementedError(version)

    def pack(self, stream: BinaryIO, version: Version) -> int:
        args = self.name_offset, self.subfolder_range.start, self.subfolder_range.end, \
               self.file_range.start, self.file_range.end
        if version in self.__LAYOUT:
            layout = self.__LAYOUT[version]
        else:
            raise NotImplementedError(version)

        return layout.pack_stream(stream, *args)

    def read_name_from_lookup(self, lookup: Dict[int, str], info: Optional[ArchiveInfo] = None) -> str:
        # If info is provided; use absolute values
        if info:
            offset = info.sub_header.toc_offset + info.table_of_contents.filenames_info.offset_relative + self.name_offset
        else:
            offset = self.name_offset
        return lookup[offset]


@dataclass
class Folder(AbstractDirectory):
    _info: FolderHeader
    name: str
    _parent_folder: Optional['Folder'] = None
    _parent_drive: Optional['VirtualDrive'] = None

    @classmethod
    def create(cls, info: FolderHeader, name_lookup: Dict[int, str]) -> 'Folder':
        name = info.read_name_from_lookup(name_lookup)
        folders: List['Folder'] = [None] * info.subfolder_range.size
        files: List[File] = [None] * info.file_range.size
        return Folder(folders, files, None, None, info, name)

    def load_folders(self, folders: List['Folder']):
        if self._info.subfolder_range.start < len(folders):
            for i in self._info.subfolder_range:
                i_0 = i - self._info.subfolder_range.start
                self.folders[i_0] = folders[i]
                folders[i]._parent_folder = self.folders[i_0]

    def load_files(self, files: List['File']):
        if self._info.file_range.start < len(files):
            for i in self._info.file_range:
                i_0 = i - self._info.file_range.start
                self.files[i_0] = files[i]
                files[i]._parent_folder = self.files[i_0]

    def walk(self) -> ArchiveWalkResult:  # Specify name for
        return self._walk(self.name)


# Cycles aren't supported (and will crash)
# Multiple parents will be copied


def flatten_folders(collection: AbstractDirectory, flattened: List[Folder]) -> Tuple[int, int]:
    start = len(flattened)
    flattened.extend(collection.folders)
    stop = len(flattened)
    return start, stop


def flatten_files(collection: AbstractDirectory, flattened: List[File]) -> Tuple[int, int]:
    start = len(flattened)
    flattened.extend(collection.files)
    stop = len(flattened)
    return start, stop


# Offset, Count (Items), Size (Bytes)
def write_virtual_drives(stream: BinaryIO, archive: Archive, version: Version, name_table: Dict[any, int],
                         recalculate: bool = False) -> Tuple[int, int, int]:
    running_folder = 0
    running_file = 0
    written = 0

    offset = stream.tell()
    for drive in archive.drives:
        folder_count = drive.folder_count(recalculate)
        file_count = drive.file_count(recalculate)

        folder = ArchiveRange(running_folder, running_folder + folder_count)
        files = ArchiveRange(running_file, running_file + file_count)

        running_folder += folder_count
        running_file += file_count

        header = VirtualDriveHeader(drive.path, drive.name, folder, files, folder.start)
        written += header.pack(stream, version)

    return offset, len(archive.drives), written


def write_names(stream: BinaryIO, archive: Archive) -> Tuple[int, int, int, Dict[str, int]]:
    offset = stream.tell()
    running_total = 0
    lookup = {}
    written = 0

    def try_write_null_terminated(name: str) -> int:
        if name in lookup:
            return 0
        # We must use relative offset to data_origin
        lookup[name] = stream.tell() - offset
        terminated_name = name
        if name[-1] != "\0":
            terminated_name += "\0"
        encoded = terminated_name.encode("ascii")
        return stream.write(encoded)

    # This will not re-use repeated names; we could change it, but I won't since my brain is over-optimizing this
    #   By allowing names to repeat, we avoid perform hash checks in a dictionary (or equality comparisons in a list)
    for drive in archive.drives:
        for _, folders, files in drive.walk():
            for f in folders:
                written += try_write_null_terminated(f.name)
                running_total += 1
            for f in files:
                written += try_write_null_terminated(f.name)
                running_total += 1

    return offset, running_total, written, lookup


# Offset, Count (Items), Size (Bytes)
def write_folders(stream: BinaryIO, archive: Archive, version: Version, name_lookup: Dict[str, int],
                  recalculate: bool = False) -> Tuple[
    int, int, int]:
    running_folder = 0
    running_file = 0
    written = 0
    total_folders = 0
    offset = stream.tell()
    for drive in archive.drives:
        for _, folders, _ in drive.walk():
            for folder in folders:
                total_folders += 1
                folder_count = folder.folder_count(recalculate)
                file_count = folder.file_count(recalculate)

                folder_range = ArchiveRange(running_folder, running_folder + folder_count)
                file_range = ArchiveRange(running_file, running_file + file_count)

                running_folder += folder_count
                running_file += file_count

                name_offset = name_lookup[folder.name]

                header = FolderHeader(name_offset, folder_range, file_range)
                written += header.pack(stream, version)

    return offset, total_folders, written


def get_v2_compflag(comp_data: bytes, decomp_data: bytes):
    if len(comp_data) == len(decomp_data):
        return FileCompressionFlag.Decompressed
    flag = (comp_data[0] & 0xF0) >> 4
    lookup = {7: FileCompressionFlag.Compressed32, 6: FileCompressionFlag.Compressed16}
    return lookup[flag]


def get_v9_compflag(comp_data: bytes, decomp_data: bytes):
    if len(comp_data) == len(decomp_data):
        return 0
    flag = (comp_data[0] & 0xF0) >> 4
    lookup = {7: FileCompressionFlag.Compressed32, 6: FileCompressionFlag.Compressed16}
    return lookup[flag]


# Lookup ~ Offset, Copmressed, Decompressed, Version Args
# Offset, Count, Byte Size
def write_file_data(stream: BinaryIO, archive: Archive, version: Version, auto_compress: bool = True) -> Tuple[
    int, int, int, Dict[File, FileHeader]]:
    offset = stream.tell()

    KIBI = 1024
    Kb16 = 16 * KIBI
    Kb32 = 32 * KIBI

    lookup = {}

    def write_info(compressed_data: bytes, decompressed_data: bytes) -> FileHeader:
        # We must use relative offset to data_origin
        data_offset = stream.tell() - offset

        if version == SgaVersion.Dow:
            compression_flag = get_v2_compflag(decompressed_data, decompressed_data)
            header = DowIFileHeader(None, data_offset, len(decompressed_data), len(compressed_data), compression_flag)
        elif version == SgaVersion.Dow2:
            header = DowIIFileHeader(None, data_offset, len(decompressed_data), len(compressed_data), 0, 0)
        elif version == SgaVersion.Dow3:
            # TODO rename unk_d to compression_flag
            compression_flag = get_v9_compflag(decompressed_data, decompressed_data)
            header = DowIIIFileHeader(None, data_offset, len(decompressed_data), len(compressed_data), 0, 0, 0, compression_flag, 0)
        else:
            raise NotImplementedError(version)
        stream.write(compressed_data)
        return header

    for drive in archive.drives:
        for _, _, files in drive.walk():
            for file in files:
                comp_data = file.data
                decomp_data = file.get_decompressed()

                if not auto_compress:  # Just dump it and GO!
                    header = write_info(comp_data, decomp_data)
                else:
                    # This is rather arbitrary, but these are my rules for auto-copmression:
                    # Don't compress files that...
                    #   Are compressed (duh)
                    #   Are smaller than the largest (16-KibiBytes) compression window
                    # When Compressing Files...
                    #   If the data size is less than 256 KibiBytes
                    #       Use 16-KbB Window
                    #   Otherwise
                    #       Use 32-KbB Window
                    if len(comp_data) != len(decomp_data):  # Compressed; just write as is
                        header = write_info(comp_data, decomp_data)
                    elif len(decomp_data) < Kb16:  # Too small
                        header = write_info(comp_data, decomp_data)
                    else:
                        if len(decomp_data) < KIBI:  # Use Window 16KbB
                            compressor = zlib.compressobj(wbits=14)
                        else:  # Use Window 32KbB
                            compressor = zlib.compressobj(wbits=15)
                        # Compress; because we are using compression obj, we need to use a temp
                        with BytesIO() as temp:
                            temp.write(compressor.compress(comp_data))
                            temp.write(compressor.flush())
                            temp.seek(0)
                            comp_data = temp.read()
                        header = write_info(comp_data, decomp_data)
                lookup[file] = header

    stop = stream.tell()
    size = stop - offset
    return offset, len(lookup), size, lookup


def write_files(stream: BinaryIO, archive: Archive, version: Version, name_lookup: Dict[str, int],
                data_lookup: Dict[File, FileHeader]) -> Tuple[int, int, int]:
    offset = stream.tell()
    written = 0
    file_count = 0

    for drive in archive.drives:
        for _, _, files in drive.walk():
            for file in files:
                header = data_lookup[file]
                header.name_offset = name_lookup[file.name]
                written += header.pack_version(stream, version)
                file_count += 1

    return offset, file_count, written


def write_table_of_contents(stream: BinaryIO, archive: Archive, version: Version,
                            data_lookup: Dict[File, FileHeader], recalculate_totals: bool = True) -> Tuple[int, int]:
    if recalculate_totals:
        for d in archive.drives:
            d.folder_count(True)
            d.file_count(True)

    toc_offset = stream.tell()
    toc_size = ArchiveToC.get_size(version)
    stream.write(bytes([0x00] * toc_size))

    # Names needs to be computer first, but DOW's layout is Drives, Folders, Files, Names (not that it HAS to be)
    #   I follow their pattern for consistency if nothing else
    #       THIS ONLY WORKS BECAUSE OFFSETS ARE RELATIVE TO THE NAME OFFSET
    with BytesIO() as name_buffer:
        _, name_count, name_size, name_lookup = write_names(name_buffer, archive)

        vd_offset, vd_count, vd_size = write_virtual_drives(stream, archive, version, name_lookup)
        vd_part = OffsetInfo(toc_offset, vd_offset - toc_offset, vd_count)

        fold_offset, fold_count, fold_size = write_folders(stream, archive, version, name_lookup)
        fold_part = OffsetInfo(toc_offset, fold_offset - toc_offset, fold_count)

        file_offset, file_count, file_size = write_files(stream, archive, version, name_lookup, data_lookup)
        file_part = OffsetInfo(toc_offset, file_offset - toc_offset, file_count)

        name_offset = stream.tell()
        name_buffer.seek(0)
        stream.write(name_buffer.read())
        name_part = FilenameOffsetInfo(toc_offset, name_offset - toc_offset, name_count, name_size)

        end = stream.tell()
        # Writeback proper TOC
        toc = ArchiveTableOfContents(vd_part, fold_part, file_part, name_part)
        stream.seek(toc_offset)
        toc.pack(stream, version)

        stream.seek(end)
        return toc_offset, end - toc_offset


def write_archive(stream: BinaryIO, archive: Archive, auto_compress: bool = True, recalculate_totals: bool = True) -> int:
    version = archive.info.header.version

    if version not in [SgaVersion.Dow, SgaVersion.Dow2, SgaVersion.Dow3]:
        raise NotImplementedError(version)

    start = stream.tell()
    # PRIMARY HEADER
    archive.info.header.pack(stream)

    # SUB HEADER SETUP
    #   We need to do a write-back once we know the offsets, sizes, what have you
    subheader_offset = stream.tell()

    subheader = ArchiveSubHeader.default(version)
    subheader.pack(stream, version)  # Write filler data

    # TOC & DATA
    if version == SgaVersion.Dow:
        # Unfortunately, we depend on Data Buffer to write TOC, and TOC 'MUST' come immediately after the Sub Header in Sga-V2.0
        #   So we write data to a memory buffer before rewriting to a
        with BytesIO() as data_buffer:
            _, _, _, data_lookup = write_file_data(data_buffer, archive, version, auto_compress)
            toc_offset, toc_size = write_table_of_contents(stream, archive, version, data_lookup, recalculate_totals)
            data_offset = stream.tell()
            data_buffer.seek(0)
            stream.write(data_buffer.read())
        subheader = ArchiveSubHeader(toc_size, data_offset, toc_offset)

    elif version in [SgaVersion.Dow2, SgaVersion.Dow3]:
        # Since these formats can point to TOC specifically, I write to the stream directly
        data_offset, _, data_size, data_lookup = write_file_data(stream, archive, version, auto_compress)
        toc_offset, toc_size = write_table_of_contents(stream, archive, version, data_lookup, recalculate_totals)
        if version == SgaVersion.Dow2:
            subheader = ArchiveSubHeader(toc_size, data_offset, toc_offset, 1, 0, 0)
        elif version == SgaVersion.Dow3:
            subheader = ArchiveSubHeader(toc_size, data_offset, toc_offset, None, None, None, 0, 0, 1,
                                         bytes([0x00] * 256), data_size)
        else:
            raise NotImplementedError(version)  # In case I add to the list in the above if and forget to add it here

    end = stream.tell()
    stream.seek(subheader_offset)
    subheader.pack(stream, version)

    stream.seek(end)
    return end - start
