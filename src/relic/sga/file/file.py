from __future__ import annotations

import zlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import BinaryIO, Dict, Optional, TYPE_CHECKING

from .header import FileHeader
if TYPE_CHECKING:
    from ..folder.folder import Folder
    from ..toc.toc import ArchiveTableOfContents
    from ..vdrive.virtual_drive import VirtualDrive


@dataclass
class File:
    header: FileHeader
    name: str
    data: Optional[bytes] = None
    _decompressed: bool = False
    _parent: Optional[Folder] = None
    _drive: Optional[VirtualDrive] = None

    @property
    def data_loaded(self) -> bool:
        return self.data is not None

    @property
    def expects_decompress(self) -> bool:
        return self.header.compressed

    @property
    def decompressed(self) -> bool:
        if self.data_loaded:
            return self._decompressed or not self.expects_decompress
        else:
            return False

    @property
    def full_path(self) -> PurePosixPath:
        if self._parent:
            return self._parent.full_path / self.name
        elif self._drive:
            return self._drive.full_path / self.name
        else:
            return PurePosixPath(self.name)

    @classmethod
    def create(cls, header: FileHeader) -> File:
        _decompressed = False
        # noinspection PyTypeChecker
        return File(header, None, None, _decompressed)

    def load_name_from_lookup(self, name_lookup: Dict[int, str]):
        self.name = name_lookup[self.header.name_sub_ptr.offset]

    def load_toc(self, toc: ArchiveTableOfContents):
        self.load_name_from_lookup(toc.names)

    def read_data(self, stream: BinaryIO, decompress: bool = False) -> bytes:
        with self.header.data_sub_ptr.stream_jump_to(stream) as handle:
            buffer = handle.read(self.header.compressed_size)
            if decompress and self.expects_decompress:
                return zlib.decompress(buffer)
            else:
                return buffer

    def load_data(self, stream: BinaryIO, decompress: bool = False):
        self.data = self.read_data(stream, decompress)
        self._decompressed = decompress

    def get_decompressed_data(self) -> bytes:
        if self.decompressed:
            return self.data
        else:
            # zlib_header = Struct("2B").unpack(self.data[:2])
            # full_zlib_header = (zlib_header[0] & 0xF0) >> 4, zlib_header[0] & 0xF, \
            #                    (zlib_header[1] & 0b11000000) >> 6, (zlib_header[1] >> 5) & 0b1, zlib_header[1] & 0b11111
            # convert = {7: 32, 6: 16}
            # assert convert[full_zlib_header[0]] == self.header.compression_flag.value
            return zlib.decompress(self.data)

    def decompress(self):
        self.data = self.get_decompressed_data()
        self._decompressed = True
