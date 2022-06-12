# # To write an Archive
# import zlib
# from abc import abstractmethod
# from io import BytesIO
# from typing import List, BinaryIO, Dict, Tuple, Type, Optional
#
# from relic.sga import v9
# from relic.sga.core import DriveABC, DriveDefABC, FolderDefABC, ArchivePathable, FileDefABC, FolderABC, FileABC, FileStorageType, FileMetaABC, ArchiveABC
#
#
#
#
# if __name__ == "__main__":
#     a = v9.Archive("Test", None, [])
#     drive = DriveABC([], [], "data", "Test Archvie")
#     a.drives = [drive]
#     drive_folder = FolderABC("drive-folder-a", [], [], _parent_path=drive)
#     drive_file = FileABC("drive-file-buffer-comp-b.raw", FileMetaABC(FileStorageType.BufferCompress), b"This is a test 'buffer compress' file!", _parent_path=drive)
#     drive.folders = [drive_folder]
#     drive.files = [drive_file]
#
#     drive_folder_folder = FolderABC("drive-folder-folder-c", [], [], _parent_path=drive_folder)
#     drive_folder_file_d = FileABC("drive-folder-file-stream-comp-d.raw", FileMetaABC(FileStorageType.StreamCompress), b"This is a test 'stream compress' file!", _parent_path=drive_folder)
#     drive_folder_file_e = FileABC("drive-folder-file-store-e.raw", FileMetaABC(FileStorageType.StreamCompress), b"This is a test 'stream compress' file!", _parent_path=drive_folder)
#     drive_folder.folders = [drive_folder_folder]
#     drive_folder.files = [drive_folder_file_d, drive_folder_file_e]
#
#     with BytesIO() as name_stream:
#         with BytesIO() as data_stream:
#             writer = ArchiveFlattener(name_stream, data_stream)
#             writer.flatten_archive(a)
#             name_stream.seek(0)
#             data_stream.seek(0)
#             names = name_stream.read()
#             data = data_stream.read()
#             _ = None
