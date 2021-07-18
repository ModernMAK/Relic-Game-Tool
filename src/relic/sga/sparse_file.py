from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO

from relic.sga.data_offset_info import DataOffsetInfo
from relic.sga.offset_info import OffsetInfo
from relic.sga.shared import read_name
from relic.shared import unpack_from_stream


@dataclass
class SparseFile:
    __FILE_HEADER_LAYOUT = Struct("< L L L L L")

    name_offset: int
    unk_a: int
    file_offset: int
    decompressed_size: int
    compressed_size: int

    @property
    def compressed(self):
        return self.decompressed_size != self.compressed_size

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'SparseFile':
        return SparseFile(*unpack_from_stream(cls.__FILE_HEADER_LAYOUT, stream))

    def read_name(self, stream: BinaryIO, offset: OffsetInfo) -> str:
        return read_name(stream, offset, self.name_offset)

    def read_data(self, stream: BinaryIO, offset: DataOffsetInfo) -> bytes:
        stream.seek(offset.offset_absolute + self.file_offset)
        return stream.read(self.compressed_size)
