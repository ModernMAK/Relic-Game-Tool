from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, BinaryIO

from ..file.header import FileHeader
from ..folder.header import FolderHeader
from .toc_ptr import ArchiveTableOfContentsPtr
from ..vdrive.header import VirtualDriveHeader
from ...common import VersionLike

_NULL = "\0".encode("ascii")
_KIBI = 1024
_BUFFER_SIZE = 64 * _KIBI


@dataclass
class ArchiveTableOfContentsHeaders:
    drives: List[VirtualDriveHeader]
    folders: List[FolderHeader]
    files: List[FileHeader]
    names: Dict[int, str]

    @classmethod
    def unpack(cls, stream: BinaryIO, ptr: ArchiveTableOfContentsPtr, version: VersionLike = None) -> ArchiveTableOfContentsHeaders:
        version = version or ptr.version  # abusing the fact that the classes know their own version to avoid explicitly passing it in

        local_ptr = ptr.virtual_drive_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            virtual_drives = [VirtualDriveHeader.unpack(handle, version) for _ in range(local_ptr.count)]

        local_ptr = ptr.folder_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            folders = [FolderHeader.unpack(handle, version) for _ in range(local_ptr.count)]

        local_ptr = ptr.file_ptr
        with local_ptr.stream_jump_to(stream) as handle:
            files = [FileHeader.unpack(handle, version) for _ in range(local_ptr.count)]

        # This gets a bit wierd
        local_ptr = ptr.name_ptr
        names: Dict[int, str] = {}
        with local_ptr.stream_jump_to(stream) as handle:
            start = stream.tell()  # use stream to avoid invalidating window
            while len(names) < local_ptr.count:
                remaining = local_ptr.count - len(names)
                current = stream.tell()  # Get relative pos to start
                buffer = handle.read(_BUFFER_SIZE)
                terminal_null = buffer.endswith(_NULL)
                parts = buffer.split(_NULL, remaining)

                offset = 0
                for i, p in enumerate(parts):
                    if i == len(parts) - 1:
                        break
                    names[current - start + offset] = p.decode("ascii")
                    offset += len(p) + 1  # +1 to include null terminal

                if not terminal_null:
                    stream.seek(current + offset)

        return ArchiveTableOfContentsHeaders(virtual_drives, folders, files, names)
