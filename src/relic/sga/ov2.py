# from __future__ import annotations
#
# import hashlib
# from dataclasses import dataclass
# from typing import BinaryIO, Tuple, List, Dict, ClassVar, Optional
#
# from serialization_tools.size import KiB
# from serialization_tools.structx import Struct
#
# from relic.sga.core import ArchiveABC, ArchiveMetaABC, BlobPtrs, FileDefABC, ToCPtrsABC, DriveDefABC, FolderDefABC, FileStorageType, FileMetaABC, FileSparseInfo, FileABC, FolderABC, Version, DriveABC, MD5MismatchError
# from relic.sga.vX import APIvX
#
#
# class _ToCPtrs(ToCPtrsABC):
#     LAYOUT = ToCPtrsABC.LAYOUT_UINT16
#
#
# class _DriveDef(DriveDefABC):
#     LAYOUT = DriveDefABC.LAYOUT_UINT16
#
#
# class _FolderDef(FolderDefABC):
#     LAYOUT = FolderDefABC.LAYOUT_UINT16
#
#
# version = Version(2)
#
#
# @dataclass
# class FileDef(FileDefABC):
#     LAYOUT = Struct("<5I")
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO):
#         name_rel_pos, storage_type_val_v2, data_rel_pos, length, store_length = cls.LAYOUT.unpack_stream(stream)
#         storage_type_map = {0: FileStorageType.Store, 16: FileStorageType.StreamCompress, 32: FileStorageType.BufferCompress}
#         storage_type = storage_type_map[storage_type_val_v2]
#         return cls(name_rel_pos, data_rel_pos, length, store_length, storage_type)
#
#
# FileMeta = FileMetaABC
# File = FileABC
# Folder = FolderABC
# Drive = DriveABC
#
#
# @dataclass
# class ArchiveMeta(ArchiveMetaABC):
#     file_md5: bytes
#     header_md5: bytes
#     blob_ptr: BlobPtrs  # Cached for MD5
#     FILE_MD5_EIGEN: ClassVar = b"E01519D6-2DB7-4640-AF54-0A23319C56C3"
#     HEADER_MD5_EIGEN: ClassVar = b"DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF"
#
#     @staticmethod
#     def _validate_md5(stream: BinaryIO, start: int, size: Optional[int], eigen: bytes, expected: bytes):
#         _BUF_SIZE = 256 * KiB
#         hasher = hashlib.md5(eigen)
#         stream.seek(start)
#         if size is None:
#             while True:
#                 buffer = stream.read(_BUF_SIZE)
#                 hasher.update(buffer)
#                 if len(buffer) != _BUF_SIZE:
#                     break
#         else:
#             read = 0
#             while read < size:
#                 buffer = stream.read(min(_BUF_SIZE, size - read))
#                 read += len(buffer)
#                 hasher.update(buffer)
#         md5 = bytes.fromhex(hasher.hexdigest())
#         if md5 != expected:
#             raise MD5MismatchError(md5, expected)
#
#     def validate_file_md5(self, stream: BinaryIO):
#         self._validate_md5(stream, self.blob_ptr.header_pos, None, self.FILE_MD5_EIGEN, self.file_md5)
#
#     def validate_header_md5(self, stream: BinaryIO):
#         self._validate_md5(stream, self.blob_ptr.header_pos, self.blob_ptr.header_size, self.HEADER_MD5_EIGEN, self.header_md5)
#
#
# class Archive(ArchiveABC):
#     meta: ArchiveMeta
#     # drives: List[Drive]  # typing
#
#     TOC_PTRS = _ToCPtrs
#     VDRIVE_DEF = _DriveDef
#     FOLDER_DEF = _FolderDef
#     FILE_DEF = FileDef
#     VERSION = version
#     META_PREFIX_LAYOUT = Struct("<16s 128s 16s 2I")
#
#     @classmethod
#     def _assemble_files(cls, file_defs: List[FileDef], names: Dict[int, str], data_pos: int):
#         files = []
#         for f_def in file_defs:
#             meta = FileMeta(f_def.storage_type)
#             sparse = FileSparseInfo(f_def.storage_type, data_pos + f_def.data_rel_pos, f_def.length, f_def.store_length)
#             file = File(names[f_def.name_rel_pos], meta, None, sparse)
#             files.append(file)
#         return files
#
#     @classmethod
#     def _unpack_meta(cls, stream: BinaryIO) -> Tuple[str, ArchiveMetaABC, BlobPtrs, ToCPtrsABC]:
#         encoded_name: bytes
#         file_md5, encoded_name, header_md5, header_size, data_pos = cls.META_PREFIX_LAYOUT.unpack_stream(stream)
#         decoded_name = encoded_name.decode("utf-16-le").rstrip("\0")
#         header_pos = stream.tell()
#         toc_ptrs = cls.TOC_PTRS.unpack(stream)
#         blob_ptrs = BlobPtrs(header_pos, header_size, data_pos, None)
#         meta = ArchiveMeta(file_md5, header_md5, blob_ptrs)
#         return decoded_name, meta, blob_ptrs, toc_ptrs
#
#
# class API(APIvX):
#     version = version
#     Archive = Archive
#     File = File
#     Folder = Folder
#     Drive = Drive
