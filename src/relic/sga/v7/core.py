from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from relic.sga import _abc
from relic.sga._abc import FileDefABC
from relic.sga.errors import Version
from relic.sga._core import VerificationType

version = Version(7)


@dataclass
class ArchiveMetadata:
    unk_a: int
    block_size:int


@dataclass
class FileDef(FileDefABC):
    modified: datetime
    verification: VerificationType
    crc: int
    hash_pos: int


@dataclass
class FileMetadata:
    modified: datetime
    verification: VerificationType
    crc: int
    hash_pos: int


Archive = _abc.Archive[ArchiveMetadata]
Folder = _abc.Folder
File = _abc.File[FileMetadata]
Drive = _abc.Drive
