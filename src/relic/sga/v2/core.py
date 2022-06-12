from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, BinaryIO

from relic.sga import _abc
from relic.sga.error import Version

version = Version(2)


@dataclass
class _Md5ChecksumHelper:
    expected: bytes
    stream: BinaryIO
    start: int
    size: Optional[int] = None
    eigen: Optional[bytes] = None

    def validate(self, stream: BinaryIO = None) -> None:
        stream = self.stream if stream is None else stream
        stream.seek(self.start)


@dataclass
class ArchiveMetadata:
    @property
    def file_md5(self) -> bytes:
        return self._file_md5.expected

    @property
    def header_md5(self) -> bytes:
        return self._header_md5.expected

    _file_md5: _Md5ChecksumHelper
    _header_md5: _Md5ChecksumHelper


Archive = _abc.Archive[ArchiveMetadata]
Folder = _abc.Folder
File = _abc.File
Drive = _abc.Drive
