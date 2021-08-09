from dataclasses import dataclass
from os.path import join
from typing import List, Iterable, Tuple, Optional

ArchiveWalkResult = Tuple[str, Iterable['Folder'], Iterable['File']]


@dataclass
class AbstractDirectory:
    folders: List['Folder']
    files: List['File']
    # Unfortunately these can't be 'defaults' or else they mess with subclasses
    __folder_count: Optional[int]
    __file_count: Optional[int]

    def folder_count(self, recalculate: bool = False) -> int:
        if not self.__folder_count or recalculate:
            self.__folder_count = len(self.folders)
            for f in self.folders:
                self.__folder_count += f.folder_count(recalculate)
        return self.__folder_count

    def file_count(self, recalculate: bool = False) -> int:
        if not self.__file_count or recalculate:
            self.__file_count = len(self.files)
            for f in self.files:
                self.__file_count += f.file_count(recalculate)
        return self.__file_count

    @classmethod
    def __safe_join(cls, parent: str, *args):
        parent = parent or ""
        return join(parent, *args)

    # Folder names are full paths
    # File names are not?
    def _walk(self, name: str = None) -> ArchiveWalkResult:
        yield name, (f for f in self.folders), (f for f in self.files)
        for folder in self.folders:
            # parent = self.__safe_join(name, folder.name)
            # for child_walk in folder._walk(parent):
            for child_walk in folder.walk():
                yield child_walk

    def walk(self) -> ArchiveWalkResult:
        return self._walk()  # Default, no name given
