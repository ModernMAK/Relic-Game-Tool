from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import BinaryIO, Tuple, List, Dict, ClassVar, Optional

from serialization_tools.structx import Struct

from relic.sga.core import ArchiveABC, ArchiveMetaABC, BlobPtrs, FileDefABC, ToCPtrsABC, DriveDefABC, FolderDefABC, FileVerificationType, FileStorageType, FileMetaABC, FileSparseInfo, FileABC, FolderABC, Version, DriveABC


class _ToCPtrs(ToCPtrsABC):
    LAYOUT = ToCPtrsABC.LAYOUT_UINT32


class _DriveDef(DriveDefABC):
    LAYOUT = DriveDefABC.LAYOUT_UINT32


class _FolderDef(FolderDefABC):
    LAYOUT = FolderDefABC.LAYOUT_UINT32


@dataclass
class FileDef(FileDefABC):
    LAYOUT = Struct("<2I Q 3I 2B I")
    # v7 Specific data
    modified: datetime  # Unix EPOCH
    verification_type: FileVerificationType
    crc: int
    hash_pos: int

    @classmethod
    def unpack(cls, stream: BinaryIO):
        name_rel_pos, hash_pos, data_rel_pos, length, store_length, modified_seconds,verification_type_val, storage_type_val, crc = cls.LAYOUT.unpack_stream(stream)
        modified = datetime.fromtimestamp(modified_seconds, timezone.utc)
        storage_type = FileStorageType(storage_type_val)
        verification_type = FileVerificationType(verification_type_val)
        return cls(name_rel_pos, data_rel_pos, length, store_length, storage_type, modified, verification_type, crc, hash_pos)


@dataclass
class FileMeta(FileMetaABC):
    modified: datetime
    verification: FileVerificationType
    storage: FileStorageType
    crc: int
    hash: bytes


class File(FileABC):
    meta: FileMeta


@dataclass
class Folder(FolderABC):
    folders: List[Folder]
    files: List[File]


class Drive(DriveABC):
    folders: List[Folder]
    files: List[File]


@dataclass
class ArchiveMeta(ArchiveMetaABC):
    sha_256: bytes
    unk_a: int
    unk_b: int
    block_size: int


class Archive(ArchiveABC):
    drives: List[Drive]  # typing
    TOC_PTRS = _ToCPtrs
    VDRIVE_DEF = _DriveDef
    FOLDER_DEF = _FolderDef
    FILE_DEF = FileDef
    VERSION = Version(9)
    META_PREFIX_LAYOUT = Struct("<128s QIQQ I 256s")
    META_POSTFIX_LAYOUT = Struct("<3I")
    NAME_BUFFER_USES_COUNT = False

    @classmethod
    def _assemble_files(cls, file_defs: List[FileDef], names: Dict[int, str], data_pos: int):
        files = []
        for f_def in file_defs:
            meta = FileMeta(f_def.storage_type, f_def.modified, f_def.verification_type, f_def.crc, None)  # TODO handle hash
            sparse = FileSparseInfo(f_def.storage_type, data_pos + f_def.data_rel_pos, f_def.length, f_def.store_length)
            file = File(names[f_def.name_rel_pos], meta, None, sparse)
            files.append(file)
        return files

    @classmethod
    def _unpack_meta(cls, stream: BinaryIO) -> Tuple[str, ArchiveMetaABC, BlobPtrs, ToCPtrsABC]:
        encoded_name: bytes
        encoded_name, header_pos, header_size, data_pos, data_size, RSV_1, sha_256 = cls.META_PREFIX_LAYOUT.unpack_stream(stream)
        decoded_name = encoded_name.decode("utf-16-le").rstrip("\0")
        assert RSV_1 == 1, RSV_1
        stream.seek(header_pos)
        toc_ptrs = cls.TOC_PTRS.unpack(stream)
        unk_a, unk_b, block_size = cls.META_POSTFIX_LAYOUT.unpack_stream(stream)
        meta = ArchiveMeta(sha_256,unk_a,unk_b, block_size)
        blob_ptrs = BlobPtrs(header_pos, header_size, data_pos, data_size)
        return decoded_name, meta, blob_ptrs, toc_ptrs
