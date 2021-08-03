import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Iterable

from relic.sga.archive_info import ArchiveInfo
from relic.sga.file_header import FileHeader
from relic.shared import fix_extension_list, filter_path_by_extension, KW_LIST


@dataclass
class File:
    header: FileHeader
    name: str
    data: bytes
    _decompressed: bool = False

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: FileHeader) -> 'File':
        name = info.read_name(stream, archive_info)
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
