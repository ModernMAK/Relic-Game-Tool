from __future__ import annotations

from types import ModuleType
from typing import Type, Protocol, ClassVar

from relic.sga import abc_, protocols
from relic.sga.common import ArchiveVersion


class APIvX(Protocol):
    """
    Allows us to have a TYPED OBJECT with required types for each version

    """

    version:ClassVar[ArchiveVersion]
    # Archive
    Archive: Type[protocols.Archive]
    ArchiveHeader: Type[protocols.ArchiveHeader]
    # Table Of Contents
    ArchiveToCPtr: Type[abc_.ArchiveToCPtrABC]
    ArchiveTableOfContentsHeaders: Type[abc_.ArchiveTableOfContentsHeadersABC]
    # Files
    FileHeader: Type[abc_.FileHeaderABC]
    File: Type[protocols.File]
    # Folders
    FolderHeader: Type[abc_.FolderHeaderABC]
    Folder: Type[protocols.Folder]
    # VDrive
    VirtualDriveHeader: Type[abc_.VirtualDriveHeaderABC]
    VirtualDrive: Type[protocols.VirtualDrive]


"""Modules implementing vX should define all of the following attributes"""
required_attrs = APIvX.__annotations__.keys()


def is_module_api(module: ModuleType):
    return all(hasattr(module, attr) for attr in required_attrs)
