import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from struct import Struct
from typing import BinaryIO, Optional, Dict, Iterable

from relic.sga.archive_header import ArchiveInfo, ArchiveSubHeader
from relic.sga.shared import Version, DowI_Version, DowII_Version, DowIII_Version
from relic.shared import fix_extension_list, filter_path_by_extension, KW_LIST, unpack_from_stream


# Compression flag is either 0 (Decompressed) or 16/32 which are both compressed
#   idk the difference, both work fine via zlib
#       Should clarify; this flag (if it is a flag) doesn't affect ZLib; but zlib handles both the 16-flag case and the 32-flag case without issue
class FileCompressionFlag(Enum):
    Decompressed = 0

    Compressed16 = 16
    Compressed32 = 32

    def compressed(self) -> bool:
        return self != FileCompressionFlag.Decompressed


@dataclass
class FileHeader:
    __v2_LAYOUT = Struct("< 5L")  # 20 Bytes
    __v5_LAYOUT = Struct("< 5L H")  # 22 Bytes
    __v9_LAYOUT = Struct("< 7L H L")  # 34 Bytes

    name_offset: int
    data_offset: int
    decompressed_size: int
    compressed_size: int
    # V2 Exclusive
    compression_flag: Optional[FileCompressionFlag] = None
    # V5 Exclusive
    unk_v5_a: Optional[int] = None
    unk_v5_b: Optional[int] = None
    # V9 Exclusive
    unk_v9_a: Optional[int] = None
    unk_v9_b: Optional[int] = None
    unk_v9_c: Optional[int] = None
    unk_v9_d: Optional[int] = None  # 256?
    unk_v9_e: Optional[int] = None

    @property
    def compressed(self):
        if self.compression_flag:
            return self.compression_flag.compressed()
        else:
            return self.compressed_size < self.decompressed_size

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version = DowI_Version) -> 'FileHeader':
        if DowI_Version == version:
            name_offset, compression_flag_value, data_offset, decompressed_size, compressed_size = unpack_from_stream(
                cls.__v2_LAYOUT, stream)
            compression_flag = FileCompressionFlag(compression_flag_value)
            return FileHeader(name_offset, data_offset, decompressed_size, compressed_size,
                              compression_flag=compression_flag)
        elif version == DowII_Version:
            name_off, data_off, comp_size, decomp_size, unk_a, unk_b = unpack_from_stream(cls.__v5_LAYOUT, stream)
            # Name, File, Compressed, Decompressed, ???, ???
            return FileHeader(name_off, data_off, decomp_size, comp_size, unk_v5_a=unk_a, unk_v5_b=unk_b)
        elif version == DowIII_Version:
            name_off, unk_a, data_off, unk_b, comp_size, decomp_size, unk_c, unk_d, unk_e = unpack_from_stream(
                cls.__v9_LAYOUT,
                stream)
            # assert unk_a == 0, (unk_a, 0)
            # assert unk_b == 0, (unk_b, 0)

            # UNK_D is a new compression flag?!
            # if comp_size != decomp_size:
            #     assert unk_d in [256,512], ((comp_size, decomp_size), (unk_d, [256,512]), (name_off, unk_a, data_off, unk_b, comp_size, decomp_size, unk_c, unk_d, unk_e))

            # Name, File, Compressed, Decompressed, ???, ???
            return FileHeader(name_off, data_off, decomp_size, comp_size,
                              unk_v9_a=unk_a, unk_v9_b=unk_b,
                              unk_v9_c=unk_c, unk_v9_d=unk_d, unk_v9_e=unk_e)
        else:
            raise NotImplementedError(version)

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
class File:
    header: FileHeader
    name: str
    data: bytes
    _decompressed: bool = False
    _parent: Optional['Folder'] = None

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: FileHeader, name_lookup: Dict[int, str]) -> 'File':
        name = info.read_name_from_lookup(name_lookup)
        data = info.read_data(stream, archive_info.sub_header)
        _decompressed = not info.compressed
        return File(info, name, data, _decompressed)

    def get_decompressed(self) -> bytes:
        if self._decompressed or not self.header.compressed:
            return self.data
        else:
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
