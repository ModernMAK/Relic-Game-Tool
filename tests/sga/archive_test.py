# from contextlib import contextmanager
# from typing import BinaryIO
#
# from relic.sga.archive import Archive
# from relic.sga.archive_info import ArchiveInfo
# from relic.sga.magic import ARCHIVE_MAGIC
# from relic.sga.sparse_archive import SparseArchive
# from tests.helpers import get_testdata_path
#
# TEST_BIN_PATH = get_testdata_path("archive.sga")
#
# TEST_ARCHIVE_FILES = []
# TEST_ARCHIVE_FOLDERS = []
# TEST_ARCHIVE = Archive(TEST_ARCHIVE_FILES, TEST_ARCHIVE_FOLDERS, ArchiveInfo())
#
#
# @contextmanager
# def open_testdata(read_magic: bool) -> BinaryIO:
#     with open(TEST_BIN_PATH, "rb") as handle:
#         # Manually read the word to avoid reading a separate file
#         if not read_magic:
#             ARCHIVE_MAGIC.read_magic_word(handle)
#         yield handle
#
#
# def unpack_helper(read_magic: bool) -> Archive:
#     with open_testdata(read_magic) as handle:
#         return Archive.unpack(handle, read_magic)
#
#
# def create_helper(read_magic: bool) -> Archive:
#     with open_testdata(read_magic) as handle:
#         sparse = SparseArchive.unpack(handle, read_magic)
#         return Archive.create(handle, sparse)
