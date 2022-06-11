from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import BinaryIO, List, ClassVar, Any, Dict

from serialization_tools.structx import Struct

from relic.sga_old.abc_ import _VirtualDriveDefinition, VirtualDrive, Folder, FolderDefABC, File, _FileMeta, FileSparseInfo
from relic.sga_old.common import FileStorageType, FileVerificationType, ArchiveVersion
from relic.sga_old.protocols import ArchivePath
from relic.sga_old.v7 import VirtualDriveDefinition, FolderDefinition

"""
index_size is UInt16 when version <= 4 else Uint32
Format According to ArchiveViewer (CoH2 Mod tools)
Magic: b'Archive_'
Version: UInt16
Product: UInt16 (I call this minor)
NiceName: bytes[128]/str[64] (utf-16-le)
Header Size: UInt32
Data Pos : UInt32
Header Pos : (cached position in file here)
ToC Rel Pos: UInt32
ToC Count : index_size
Folder Rel Pos: UInt32
Folder Count : index_size
File Rel Pos: UInt32
File Count : index_size
Name Buffer Pos : UInt32
Name Buffer Count/Size ??? : index_size
unk??? : uint32
Block Size : Uint32
~~~
ToC


"""
_UTF_NAME = "128s"

version = ArchiveVersion(7)


class VirtualDriveDefinition_v4(_VirtualDriveDefinition):
    LAYOUT = Struct("64s 64s 5H")


@dataclass
class FileMeta(_FileMeta):
    modified: datetime
    verification: FileVerificationType
    storage: FileStorageType
    crc: int
    hash: bytes


class FolderDefinition_v4(FolderDefABC):
    LAYOUT = Struct("I 4H")


@dataclass
class FileDefABC:
    name_rel_pos: int
    data_rel_pos: int
    length: int
    store_length: int
    modified: datetime  # Unix EPOCH
    verification_type: FileVerificationType
    storage_type: FileStorageType
    crc: int
    hash_pos: int

    LAYOUT: ClassVar[Struct] = Struct("=5I 2B 2I")

    @classmethod
    def unpack(cls, stream: BinaryIO):
        args: List[Any] = list(cls.LAYOUT.unpack_stream(stream))
        # args2 = Struct(f"<5L BB 2L").unpack_stream(stream)
        # _arg4 = args[4]
        args[4] = datetime.fromtimestamp(args[4], timezone.utc)
        args[5] = FileVerificationType(args[5])
        args[6] = FileStorageType(args[6])
        return cls(*args)




@dataclass
class ArchiveMeta:
    unk_a: int
    block_size: int


#   Archives consist of 3 'Blobs' + some Metadata
#       Magic (Metadata)
#       Version / Product (Metadata)
#       Meta Blob ( ToC Ptrs / Header Ptr / Data Ptr / other Metadata)
#       Header Blob
#           ToC Header
#           ToC Definitions
#       Data Blob
#           Raw Bytes for sub-files
