from dataclasses import dataclass
from enum import Enum
from struct import Struct
from typing import BinaryIO, Optional

from relic.sga.archive_info import ArchiveInfo
from relic.sga.data_offset_info import DataOffsetInfo, ArchiveSubHeader
from relic.sga.offset_info import OffsetInfo
from relic.sga.shared import read_name
from relic.sga.version import Version
from relic.shared import unpack_from_stream


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
    __v2_LAYOUT = Struct("< L L L L L")
    __v5_LAYOUT = Struct("< L L L L L H")

    name_offset: int
    data_offset: int
    decompressed_size: int
    compressed_size: int
    # V2 Exclusive
    compression_flag: Optional[FileCompressionFlag] = None
    # V5 Exclusive
    unk_v5_a: Optional[int] = None
    unk_v5_b: Optional[int] = None

    @property
    def compressed(self):
        if self.compression_flag:
            return self.compression_flag.compressed()
        else:
            return self.compressed_size < self.decompressed_size

    @classmethod
    def unpack(cls, stream: BinaryIO, version: Version = Version.DowI_Version()) -> 'FileHeader':
        if Version.DowI_Version() == version:
            name_offset, compression_flag_value, data_offset, decompressed_size, compressed_size = unpack_from_stream(
                cls.__v2_LAYOUT, stream)
            compression_flag = FileCompressionFlag(compression_flag_value)
            return FileHeader(name_offset, data_offset, decompressed_size, compressed_size,
                              compression_flag=compression_flag)
        elif version == Version.DowII_Version():
            name_off, data_off, comp_size, decomp_size, unk_a, unk_b = unpack_from_stream(cls.__v5_LAYOUT, stream)
            # Name, File, Compressed, Decompressed, ???, ???
            return FileHeader(name_off, data_off, decomp_size, comp_size, unk_v5_a=unk_a, unk_v5_b=unk_b)
        else:
            raise NotImplementedError(version)

    def read_name(self, stream: BinaryIO, info: ArchiveInfo) -> str:
        return read_name(stream, info, self.name_offset)

    def read_data(self, stream: BinaryIO, offset: ArchiveSubHeader) -> bytes:
        stream.seek(offset.data_offset + self.data_offset)
        return stream.read(self.compressed_size)
