from dataclasses import dataclass
from os.path import join
from typing import List, Iterable, Tuple


ArchiveWalkResult = Tuple[str, Iterable['Folder'], Iterable['File']]

@dataclass
class AbstractDirectory:

    folders: List['Folder']
    files: List['File']

    @classmethod
    def __safe_join(cls, parent: str, *args):
        parent = parent or ""
        return join(parent, *args)

    def _walk(self, name: str = None) -> ArchiveWalkResult:
        yield name, (f for f in self.folders), (f for f in self.files)
        for folder in self.folders:
            parent = self.__safe_join(name, folder.name)
            for child_walk in folder._walk(parent):
                yield child_walk

    def walk(self) -> ArchiveWalkResult:
        return self._walk() # Default, no name given