# from types import ModuleType
# from typing import Type, Protocol
#
# from relic.sga.protocols import Archive, File, Folder, Drive
#
#
# class APIvX(Protocol):
#     """
#     Allows us to have a TYPED OBJECT with required types for each version
#
#     """
#
#     version: Version
#     # Archive
#     Archive: Type[Archive]
#     # ArchiveHeader: Type[protocols.ArchiveHeader]
#     # # Table Of Contents
#     # ArchiveToCPtr: Type[abc_.ArchiveToCPtrABC]
#     # ArchiveTableOfContentsHeaders: Type[abc_.ArchiveTableOfContentsHeadersABC]
#     # # Files
#     # FileHeader: Type[abc_.FileHeaderABC]
#     File: Type[FileABC]
#     # # Folders
#     # FolderHeader: Type[abc_.FolderHeaderABC]
#     Folder: Type[FolderABC]
#     # # VDrive
#     # VirtualDriveHeader: Type[abc_.VirtualDriveHeaderABC]
#     Drive: Type[DriveABC]
#
#
# """Modules implementing vX should define all of the following attributes"""
# required_attrs = APIvX.__annotations__.keys()
#
#
# def is_module_api(module: ModuleType):
#     return all(hasattr(module, attr) for attr in required_attrs)
