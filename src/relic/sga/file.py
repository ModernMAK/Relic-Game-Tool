import zlib
from dataclasses import dataclass
from typing import BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.file_header import FileHeader


@dataclass
class File:
    header: FileHeader
    name: str
    data: bytes

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: FileHeader) -> 'File':
        name = info.read_name(stream, archive_info.filenames_info)
        data = info.read_data(stream, archive_info.data_info)
        return File(info, name, data)

    def decompress(self) -> bytes:
        if self.header.compressed:
            return zlib.decompress(self.data)
        else:
            return self.data

