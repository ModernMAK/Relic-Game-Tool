from dataclasses import dataclass
from os.path import join
from typing import TypeVar, Generic, List, Iterable, Tuple

from relic.sga.file import File
from relic.sga.folder import Folder

ArchiveWalkResult = Tuple[str, Iterable[Folder], Iterable[File]]


#
# @dataclass
# class FileCollection:
#     files: List[File]
#
#     # Read only iterator
#     def walk_files(self) -> Iterable[File]:
#         return (f for f in self.files)
#
#     def walk(self, parent: str = None) -> FolderWalkResult:
#         yield parent, (), self.walk_files()
#
#
# @dataclass
# class FolderCollection:
#     folders: List[Folder]
#
#     # Read only iterator
#     def walk_folders(self) -> Iterable[Folder]:
#         return (f for f in self.folders)
#
#
# @dataclass
# class DirectoryCollection(FileCollection, FolderCollection):
#     @classmethod
#     def __safe_join(cls, parent: str, *args):
#         parent = parent or ""
#         return join(parent, *args)
#
#     def _walk(self, parent: str = None) -> FolderWalkResult:
#         yield parent, self.walk_folders(), self.walk_files()
#         for folder in self.folders:
#             parent = self.__safe_join(parent, folder.name)
#             for child_walk in folder.walk(parent):
#                 yield child_walk

@dataclass
class AbstractDirectory:
    folders: List[Folder]
    files: List[File]

    @classmethod
    def __safe_join(cls, parent: str, *args):
        parent = parent or ""
        return join(parent, *args)

    def _walk(self, name: str = None) -> ArchiveWalkResult:
        yield name, (f for f in self.files), (f for f in self.folders)
        for folder in self.folders:
            parent = self.__safe_join(name, folder.name)
            for child_walk in folder.walk(parent):
                yield child_walk

    def walk(self) -> ArchiveWalkResult:
        return self._walk() # Default, no name given