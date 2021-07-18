from dataclasses import dataclass
from os.path import splitext
from typing import List, BinaryIO, Tuple, Iterable

from relic.sga.archive_info import ArchiveInfo
from relic.sga.file import File
from relic.sga.sparse_foler import SparseFolder
from relic.shared import fix_exts


@dataclass
class Folder:
    _info: SparseFolder
    name: str
    folders: List['Folder']
    files: List[File]
    _folder: 'Folder' = None

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: SparseFolder) -> 'Folder':
        name = info.read_name(stream, archive_info.filenames_info)
        folders = [None] * (info.last_sub - info.first_sub)
        files = [None] * (info.last_filename - info.first_filename)
        return Folder(info, name, folders, files, None)

    def load_folders(self, folders: List['Folder']):
        if self._info.first_sub < len(folders):
            for i in range(self._info.first_sub, self._info.last_sub):
                i_0 = i - self._info.first_sub
                self.folders[i_0] = folders[i]
                if self == folders[i]:
                    raise Exception("Cyclic Folder!")
                if folders[i]._folder is not None:
                    raise Exception("File matches multiple folders!")
                folders[i]._folder = self

    def load_files(self, files: List['File']):
        if self._info.first_filename < len(files):
            for i in range(self._info.first_filename, self._info.last_filename):
                i_0 = i - self._info.first_filename
                self.files[i_0] = files[i]
                if files[i]._folder is not None:
                    raise Exception("File matches multiple folders!")
                files[i]._folder = self

    def walk_files(self, exts: List[str] = None) -> Iterable[Tuple[str, str, 'File']]:
        if exts:
            exts = fix_exts(exts)


        for f in self.files:
            if exts:
                _, ext = splitext(f.name)
                if ext not in exts:
                    continue
            yield self.name, f.name, f

        for f in self.folders:
            for p in f.walk_files(exts):
                yield p

