from dataclasses import dataclass
from enum import Enum
from struct import Struct
from typing import BinaryIO

from relic.sga.data_offset_info import DataOffsetInfo
from relic.sga.offset_info import OffsetInfo
from relic.sga.shared import read_name
from relic.shared import unpack_from_stream


# Compression flag is either 0 (Decompressed) or 16/32 which are both compressed
#   idk the difference, both work fine via zlib
class FileCompressionFlag(Enum):
    Decompressed = 0

    Compressed16 = 16
    Compressed32 = 32

    def compressed(self) -> bool:
        return self != FileCompressionFlag.Decompressed


@dataclass
class FileHeader:
    __FILE_HEADER_LAYOUT = Struct("< L L L L L")

    name_offset: int
    compression_flag: FileCompressionFlag
    file_offset: int
    decompressed_size: int
    compressed_size: int

    @property
    def compressed(self):
        return self.compression_flag.compressed()

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'FileHeader':
        args = unpack_from_stream(cls.__FILE_HEADER_LAYOUT, stream)
        pre = args[0:1]
        compression_flag = FileCompressionFlag(args[1])
        post = args[2:5]
        return FileHeader(*pre, compression_flag, *post)

    def read_name(self, stream: BinaryIO, offset: OffsetInfo) -> str:
        return read_name(stream, offset, self.name_offset)

    def read_data(self, stream: BinaryIO, offset: DataOffsetInfo) -> bytes:
        stream.seek(offset.offset_absolute + self.file_offset)
        return stream.read(self.compressed_size)
