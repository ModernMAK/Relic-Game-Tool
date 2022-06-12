from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from relic.sga import _abc
from relic.sga._abc import FileDefABC
from relic.sga._core import VerificationType
from relic.sga._serializers import _Md5ChecksumHelper
from relic.sga.errors import Version

version = Version(5)


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
    unk_a:int


@dataclass
class FileDef(FileDefABC):
    modified: datetime
    verification: VerificationType


@dataclass
class FileMetadata:
    modified: datetime
    verification: VerificationType


Archive = _abc.Archive[ArchiveMetadata]
Folder = _abc.Folder
File = _abc.File[FileMetadata]
Drive = _abc.Drive
