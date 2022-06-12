from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, BinaryIO

from relic.sga import _abc
from relic.sga._abc import FileDefABC
from relic.sga.errors import Version
from relic.sga._core import VerificationType

version = Version(9)


@dataclass
class ArchiveMetadata:
    sha_256:bytes
    unk_a: int
    unk_b: int
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
