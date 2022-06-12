from typing import Optional, List, BinaryIO
from relic.sga._serializers import _Md5ChecksumHelper
from relic.sga import StorageType
from relic.sga.protocols import IOContainer
from relic.sga.v2 import API, core, _serializers as _s


def generate_file(name: str, data: bytes, storage: StorageType, compressed: bool = False, parent: Optional[IOContainer] = None) -> API.File:
    return core.File(name, data, storage, compressed, None, parent, None)


def generate_folder(name: str, folders: Optional[List[API.Folder]] = None, files: Optional[List[API.File]] = None, parent: Optional[IOContainer] = None) -> API.Folder:
    folders = [] if folders is None else folders
    files = [] if files is None else files
    return core.Folder(name, folders, files, parent=parent)


def generate_drive(name: str, folders: Optional[List[API.Folder]] = None, files: Optional[List[API.File]] = None, alias: str = "data") -> API.Drive:
    folders = [] if folders is None else folders
    files = [] if files is None else files
    return core.Drive(alias, name, folders, files)


def generate_archive_meta(stream: BinaryIO, header_pos: int, header_size: int) -> core.ArchiveMetadata:
    header_helper = _Md5ChecksumHelper(None, None, header_pos, header_size, _s.APISerializers.HEADER_MD5_EIGEN)
    file_helper = _Md5ChecksumHelper(None, None, header_pos, None, _s.APISerializers.FILE_MD5_EIGEN)
    # Setup expected MD5 results
    header_helper.expected = header_helper.read(stream)
    file_helper.expected = file_helper.read(stream)
    return core.ArchiveMetadata(file_helper, header_helper)


def generate_archive(name: str, meta: core.ArchiveMetadata =None, drives: Optional[List[API.Drive]] = None) -> API.Archive:
    drives = [] if drives is None else drives
    return core.Archive(name,meta,drives)

