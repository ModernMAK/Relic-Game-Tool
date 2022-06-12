from __future__ import annotations

from typing import BinaryIO, Dict, ClassVar, Optional

from serialization_tools.structx import Struct

from relic.sga import _abc, _serializers as _s
from relic.sga._abc import FileDefABC as FileDef, Archive
from relic.sga.v2 import core
from relic.sga.core import MagicWord, Version
from relic.sga.protocols import StreamSerializer, StorageType

folder_layout = Struct("<I 4H")
folder_serializer = _s.FolderDefSerializer(folder_layout)

drive_layout = Struct("<64s 64s 5H")
drive_serializer = _s.DriveDefSerializer(drive_layout)

file_layout = Struct("<5I")


class FileDefSerializer(StreamSerializer[FileDef]):
    STORAGE2INT: Dict[StorageType, int] = {
        StorageType.Store: 0,
        StorageType.BufferCompress: 16,
        StorageType.StreamCompress: 32
    }
    INT2STORAGE: Dict[int, StorageType] = {value: key for key, value in STORAGE2INT.items()}  # reverse the dictionary

    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> FileDef:
        storage_type: int
        name_pos, storage_type, data_pos, length_on_disk, length_in_archive = self.layout.unpack_stream(stream)
        storage_type: StorageType = self.INT2STORAGE[storage_type]
        return FileDef(name_pos, data_pos, length_on_disk, length_in_archive, storage_type)

    def pack(self, stream: BinaryIO, value: FileDef) -> int:
        storage_type = self.STORAGE2INT[value.storage_type]
        args = value.name_pos, storage_type, value.data_pos, value.length_on_disk, value.length_in_archive
        return self.layout.pack_stream(stream, *args)


file_serializer = FileDefSerializer(file_layout)
toc_layout = Struct("<IH IH IH IH")
toc_header_serializer = _s.TocHeaderSerializer(toc_layout)


class APISerializers(_abc.APISerializer):
    FILE_MD5_EIGEN: ClassVar = b"E01519D6-2DB7-4640-AF54-0A23319C56C3"
    HEADER_MD5_EIGEN: ClassVar = b"DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF"

    def read(self, stream: BinaryIO, lazy: bool = False, decompress: bool = True) -> Archive:
        MagicWord.read_magic_word(stream)
        version = Version.unpack(stream)
        version.assert_version_matches(self.version)

        name: bytes
        file_md5, name, header_md5, header_size, data_pos = self.layout.unpack_stream(stream)
        header_pos = stream.tell()
        # Seek to header; but we skip that because we are already there
        toc_header = self.TocHeader.unpack(stream)
        drive_defs, folder_defs, file_defs = _s._read_toc_definitions(stream, toc_header, header_pos, self.DriveDef, self.FolderDef, self.FileDef)
        names = _s._read_toc_names_as_count(stream, toc_header.name_info, header_pos)
        drives, files = _s._assemble_io_from_defs(drive_defs, folder_defs, file_defs, names, data_pos, stream)

        if not lazy:
            for file in files:
                lazy_info: Optional[_abc._FileLazyInfo] = file._lazy_info
                if lazy_info is None:
                    raise Exception("API read files, but failed to create lazy info!")
                else:
                    file.data = lazy_info.read(decompress)
                    file._lazy_info = None

        name: str = name.rstrip(b"").decode("utf-16-le")
        file_md5_helper = core._Md5ChecksumHelper(file_md5, stream, header_pos, eigen=self.FILE_MD5_EIGEN)
        header_md5_helper = core._Md5ChecksumHelper(file_md5, stream, header_pos, header_size, eigen=self.FILE_MD5_EIGEN)
        metadata = core.ArchiveMetadata(file_md5_helper, header_md5_helper)

        return Archive(name, metadata, drives)

    def write(self, stream: BinaryIO, archive: Archive) -> int:
        raise NotImplementedError

    def __init__(self):
        self.DriveDef = drive_serializer
        self.FolderDef = folder_serializer
        self.FileDef = file_serializer
        self.TocHeader = toc_header_serializer
        self.version = core.version
        self.layout = Struct("<16s 128s 16s 2I")
