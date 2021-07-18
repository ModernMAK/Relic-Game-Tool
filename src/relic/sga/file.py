import zlib
from dataclasses import dataclass
from typing import BinaryIO

from relic.sga.archive_info import ArchiveInfo
from relic.sga.sparse_file import SparseFile


@dataclass
class File:
    info: SparseFile
    name: str
    data: bytes
    _folder: 'Folder' = None

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: SparseFile) -> 'File':
        name = info.read_name(stream, archive_info.filenames_info)
        data = info.read_data(stream, archive_info.data_info)
        return File(info, name, data)

    def decompress(self) -> bytes:
        if self.info.compressed:
            return zlib.decompress(self.data)
        else:
            return self.data

    @property
    def folder(self) -> 'Folder':
        return self._folder

