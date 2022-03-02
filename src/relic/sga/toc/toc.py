from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, BinaryIO, TYPE_CHECKING

from .toc_headers import ArchiveTableOfContentsHeaders

if TYPE_CHECKING:
    from ..file.file import File
    from ..folder.folder import Folder
    from ..vdrive.virtual_drive import VirtualDrive


@dataclass
class ArchiveTableOfContents:
    drives: List[VirtualDrive]
    folders: List[Folder]
    files: List[File]
    names: Dict[int, str]

    @classmethod
    def create(cls, toc_headers: ArchiveTableOfContentsHeaders) -> ArchiveTableOfContents:
        from ..vdrive.virtual_drive import VirtualDrive
        from ..file.file import File
        from ..folder.folder import Folder

        drives = [VirtualDrive.create(header) for header in toc_headers.drives]
        folders = [Folder.create(header) for header in toc_headers.folders]
        files = [File.create(header) for header in toc_headers.files]

        return ArchiveTableOfContents(drives, folders, files, toc_headers.names)

    def load_data(self, stream: BinaryIO):
        for _ in self.files:
            _.load_data(stream)

    def load_toc(self):
        for _ in self.drives:
            _.load_toc(self)
        for _ in self.folders:
            _.load_toc(self)
        for _ in self.files:
            _.load_toc(self)

    def build_tree(self):
        for _ in self.drives:
            _.build_tree()


ArchiveTOC = ArchiveTableOfContents
