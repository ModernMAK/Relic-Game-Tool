from __future__ import annotations

from contextlib import contextmanager
from pathlib import PurePath
from types import ModuleType
from typing import TypeVar, Protocol, List, Optional, ForwardRef, Tuple, Iterable, BinaryIO, Type, runtime_checkable, Sequence

from relic.sga._core import StorageType, Version

TFile = TypeVar("TFile")
TFolder = TypeVar("TFolder")
TDrive = TypeVar("TDrive")
TArchive = TypeVar("TArchive")
TMetadata = TypeVar("TMetadata")
TFileMetadata = TypeVar("TFileMetadata")
TFile_co = TypeVar("TFile_co", covariant=True)
TFolder_co = TypeVar("TFolder_co", covariant=True)
T = TypeVar("T")


@runtime_checkable
class StreamSerializer(Protocol[T]):
    def unpack(self, stream: BinaryIO) -> T:
        raise NotImplementedError

    def pack(self, stream: BinaryIO, value: T) -> int:
        raise NotImplementedError


@runtime_checkable
class IOPathable(Protocol):
    @property
    def path(self) -> PurePath:
        raise NotImplementedError


class IONode(Protocol):
    parent: Optional[IOContainer]


class IOContainer(IONode, Protocol[TFolder, TFile]):
    sub_folders: List[TFolder]
    files: List[TFile]


IOWalkStep = Tuple[IOContainer, Sequence[TFolder_co], Sequence[TFile_co]]
IOWalk = Iterable[IOWalkStep]


class IOWalkable(Protocol[TFolder_co, TFile_co]):
    def walk(self) -> IOWalk:
        raise NotImplementedError


class File(IOPathable, IONode, Protocol[TFileMetadata]):
    name: str

    @property
    def data(self) -> bytes:
        raise NotImplementedError

    @data.setter
    def data(self, value: bytes) -> None:
        raise NotImplementedError

    storage_type: StorageType
    metadata: TFileMetadata

    @property
    def is_compressed(self) -> bool:
        raise NotImplementedError

    def compress(self) -> None:
        raise NotImplementedError

    def decompress(self) -> None:
        raise NotImplementedError

    @contextmanager
    def open(self, read_only: bool = True) -> BinaryIO:
        raise NotImplementedError


class Folder(IOWalkable, IOPathable, IOContainer, Protocol):
    name: str


class Drive(IOWalkable, IOPathable, IOContainer, Protocol):
    alias: str
    name: str


class Archive(IOWalkable, Protocol[TMetadata]):
    name: str
    metadata: TMetadata
    drives: List[Drive]


class API(Protocol[TArchive, TDrive, TFolder, TFile]):
    version: Version
    Archive: Type[TArchive]
    Drive: Type[TDrive]
    Folder: Type[TFolder]
    File: Type[TFile]

    def read(self, stream: BinaryIO, lazy: bool = False, decompress: bool = True) -> TArchive:
        raise NotImplementedError

    def write(self, stream: BinaryIO, archive: TArchive) -> int:
        raise NotImplementedError


# Hard coded-ish but better then nothing
_required_api_attrs = API.__annotations__.keys()
_required_api_callables = ["read", "write"]


def is_module_api(module: ModuleType):
    has_attr = all(hasattr(module, attr) for attr in _required_api_attrs)
    funcs = dir(module)
    has_callables = all(func in funcs for func in _required_api_callables)
    return has_attr and has_callables
