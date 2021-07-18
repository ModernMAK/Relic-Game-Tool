from dataclasses import dataclass
from os.path import split, splitext
from typing import List, BinaryIO, Iterable, Tuple

from relic.sga.archive_info import ArchiveInfo
from relic.sga.description import Description
from relic.sga.file import File
from relic.sga.folder import Folder
from relic.sga.sparse_archive import SparseArchive
from relic.shared import fix_exts


@dataclass
class FullArchive:
    info: ArchiveInfo
    descriptions: List[Description]
    folders: List[Folder]
    files: List[File]

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic:bool=True):
        info = SparseArchive.unpack(stream, read_magic)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive: SparseArchive) -> 'FullArchive':
        info = archive.info
        desc = archive.descriptions
        folders = [Folder.create(stream, info, f) for f in archive.folders]
        files = [File.create(stream, info, f) for f in archive.files]
        for f in folders:
            f.load_folders(folders)
            f.load_files(files)

        folders = [f for f in folders if f._folder is None]
        files = [f for f in files if f._folder is None]

        # for f in folders:
        #     del f._info
        #     del f._child
        # for f in files:
        #     del f._loose

        # names = archive.names

        return FullArchive(info, desc, folders, files)

    def walk_files(self, exts: List[str] = None) -> Iterable[Tuple[str, str, 'File']]:
        if exts:
            exts = fix_exts(exts)
        for folder in self.folders:
            for pair in folder.walk_files(exts):
                yield pair

        for file in self.files:
            dirname, fname = split(file.name)
            if exts:
                _, ext = splitext(fname)
                if ext.lower() not in exts:
                    continue
            yield dirname, fname, file
