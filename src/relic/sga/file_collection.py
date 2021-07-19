from dataclasses import dataclass
from typing import TypeVar, Generic, List, Iterable

TFile = TypeVar('TFile')
TFolder = TypeVar('TFolder')



@dataclass
class FileCollection(Generic[TFile]):
    files: List[TFile]

    # pointless function is pointless; if I support nested file collections, then this would be meaningful
    def walk_files(self) -> Iterable[TFile]:
        for file in self.files:
            yield file


@dataclass
class FolderCollection(Generic[TFolder]):
    folders: List[TFolder]

    # pointless function is pointless; if I support nested file collections, then this would be meaningful
    def walk_folders(self) -> Iterable[TFolder]:
        for folder in self.folders:
            yield folder

