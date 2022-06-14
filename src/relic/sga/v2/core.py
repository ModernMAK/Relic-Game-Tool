from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from relic.sga import _abc
from relic.sga._serializers import _Md5ChecksumHelper
from relic.sga.errors import Version

version = Version(2)


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


Archive: Type[_abc.Archive[ArchiveMetadata]] = _abc.Archive
Folder = _abc.Folder
File = _abc.File
Drive = _abc.Drive
