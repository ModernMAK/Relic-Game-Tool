# import zlib
# from io import BytesIO
# from os.path import join
#
# from archive_tools.structio import WindowPtr, Ptr
#
# from relic.sga.archive.header import DowIArchiveHeader
# from relic.sga.file.file import File
# from relic.sga.file.header import DowIFileHeader
# from relic.sga.folder.folder import Folder
# from relic.sga.vdrive.virtual_drive import VirtualDrive
# from tests.helpers import get_testdata_root_folder, lorem_ipsum
#
#
# def compress16(b: bytes) -> bytes:
#     compressor = zlib.compressobj(wbits=14)
#     with BytesIO() as stream:
#         stream.write(compressor.compress(b))
#         stream.write(compressor.flush())
#         stream.seek(0)
#         return stream.read()
#
#
# def compress32(b: bytes) -> bytes:
#     compressor = zlib.compressobj(wbits=15)
#     with BytesIO() as stream:
#         stream.write(compressor.compress(b))
#         stream.write(compressor.flush())
#         stream.seek(0)
#         return stream.read()
#
#
# def build_sample_dow1_archive():
#     header = DowIArchiveHeader("DowI Test Data", WindowPtr(None, None), Ptr(None), 0)
#
#     raw_content = lorem_ipsum.encode("ascii")
#     comp_16_content = compress16(raw_content)
#     comp_32_content = compress32(raw_content)
#
#     rf = DowIFileHeader(None,None,#, len(raw_content), len(raw_content), FileCompressionFlag.Decompressed)
#     raw_file = File(, "Lorem Ipsum Raw", raw_content))
#     comp16_file = File(DowIFileHeader(None, None, len(raw_content), len(comp_16_content), FileCompressionFlag.Compressed16), "Lorem Ipsum Zlib-16", comp_16_content)
#     comp32_file = File(DowIFileHeader(None, None, len(raw_content), len(comp_32_content), FileCompressionFlag.Compressed32), "Lorem Ipsum Zlib-32", comp_32_content)
#     lorem_folder = Folder([], [raw_file, comp16_file, comp32_file], 0, 3, FolderHeader(None, None, None), "Lorem Ipsum")
#     test_drive = VirtualDrive([lorem_folder], [], 1, 0, "test", "Test Drive", None)
#
#     archive = Archive(info, [test_drive])
#     return archive
#
# #
# # def build_sample_dow2_archive():
# #     header = ArchiveHeader(SgaVersion.Dow2.value, "DowII Test Data", bytes([0x00] * 16), bytes([0x00] * 16))
# #
# #     info = ArchiveInfo(header, None, None)
# #     raw_content = lorem_ipsum.encode("ascii")
# #     comp_16_content = compress16(raw_content)
# #     comp_32_content = compress32(raw_content)
# #
# #     raw_file = File(DowIIFileHeader(None, None, len(raw_content), len(raw_content), 0, 0), "Lorem Ipsum Raw", raw_content)
# #     comp16_file = File(DowIIFileHeader(None, None, len(raw_content), len(comp_16_content), 0, 0), "Lorem Ipsum Zlib-16", comp_16_content)
# #     comp32_file = File(DowIIFileHeader(None, None, len(raw_content), len(comp_32_content), 0, 0), "Lorem Ipsum Zlib-32", comp_32_content)
# #     lorem_folder = Folder([], [raw_file, comp16_file, comp32_file], 0, 3, FolderHeader(None, None, None), "Lorem Ipsum")
# #     test_drive = VirtualDrive([lorem_folder], [], 1, 0, "test", "Test Drive", None)
# #
# #     archive = Archive(info, [test_drive])
# #     return archive
# #
# #
# # def build_sample_dow3_archive():
# #     header = ArchiveHeader(SgaVersion.Dow3.value, "DowIII Test Data")
# #
# #     info = ArchiveInfo(header, None, None)
# #     raw_content = lorem_ipsum.encode("ascii")
# #     comp_16_content = compress16(raw_content)
# #     comp_32_content = compress32(raw_content)
# #
# #     raw_file = File(DowIIIFileHeader(None, None, len(raw_content), len(raw_content), 0, 0, 0, 0, 0),
# #                     "Lorem Ipsum Raw", raw_content)
# #     comp16_file = File(DowIIIFileHeader(None, None, len(raw_content), len(comp_16_content), 0, 0, 0, 0, 0),
# #                        "Lorem Ipsum Zlib-16", comp_16_content)
# #     comp32_file = File(DowIIIFileHeader(None, None, len(raw_content), len(comp_32_content), 0, 0, 0, 0, 0),
# #                        "Lorem Ipsum Zlib-32", comp_32_content)
# #     lorem_folder = Folder([], [raw_file, comp16_file, comp32_file], 0, 3, FolderHeader(None, None, None), "Lorem Ipsum")
# #     test_drive = VirtualDrive([lorem_folder], [], 1, 0, "test", "Test Drive", None)
# #
# #     archive = Archive(info, [test_drive])
# #     return archive
#
#
# if __name__ == "__main__":
#     root = get_testdata_root_folder()
#     archive = build_sample_dow1_archive()
#     with open(join(root, "archive-v2_0.sga"), "wb") as file:
#         archive.pack(file)
#         # write_archive(file, archive)
#
#     # archive2 = build_sample_dow2_archive()
#     # with open(join(root, "archive-v5_0.sga"), "wb") as file:
#     #     write_archive(file, archive2)
#     #
#     # archive3 = build_sample_dow3_archive()
#     # with open(join(root, "archive-v9_0.sga"), "wb") as file:
#     #     write_archive(file, archive3)
