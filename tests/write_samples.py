from io import BytesIO
from os.path import join

from relic.sga import Archive, ArchiveInfo, VirtualDrive, File, FileHeader, Folder, FolderHeader, \
    ArchiveHeader
from relic.sga.file import FileCompressionFlag
from relic.sga.shared import SgaVersion
import zlib
from helpers import get_testdata_root_folder
from relic.sga.writer import write_archive


def compress16(b: bytes) -> bytes:
    compressor = zlib.compressobj(wbits=14)
    with BytesIO() as stream:
        stream.write(compressor.compress(b))
        stream.write(compressor.flush())
        stream.seek(0)
        return stream.read()


def compress32(b: bytes) -> bytes:
    compressor = zlib.compressobj(wbits=15)
    with BytesIO() as stream:
        stream.write(compressor.compress(b))
        stream.write(compressor.flush())
        stream.seek(0)
        return stream.read()


def build_sample_dow1_archive():
    header = ArchiveHeader(SgaVersion.Dow.value, "DowI Test Data", bytes([0x00] * 16), bytes([0x00] * 16))

    info = ArchiveInfo(header, None, None)
    raw_content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua." \
                  " Malesuada fames ac turpis egestas. Accumsan lacus vel facilisis volutpat est velit." \
                  " Turpis egestas pretium aenean pharetra magna ac placerat vestibulum lectus. Tellus cras adipiscing enim eu turpis egestas." \
                  " Pellentesque adipiscing commodo elit at imperdiet dui accumsan sit. Massa enim nec dui nunc mattis." \
                  " Gravida in fermentum et sollicitudin ac orci phasellus egestas." \
                  " Eu volutpat odio facilisis mauris sit amet massa vitae. Diam quis enim lobortis scelerisque fermentum dui faucibus.".encode(
        "ascii")
    comp_16_content = compress16(raw_content)
    comp_32_content = compress32(raw_content)

    raw_file = File(FileHeader(None, None, len(raw_content), len(raw_content), FileCompressionFlag.Decompressed),
                    "Lorem Ipsum Raw", raw_content)
    comp16_file = File(FileHeader(None, None, len(raw_content), len(comp_16_content), FileCompressionFlag.Compressed16),
                       "Lorem Ipsum Zlib-16", comp_16_content)
    comp32_file = File(FileHeader(None, None, len(raw_content), len(comp_32_content), FileCompressionFlag.Compressed32),
                       "Lorem Ipsum Zlib-32", comp_32_content)
    lorem_folder = Folder([], [raw_file, comp16_file, comp32_file], 0, 3, FolderHeader(None, None, None), "Lorem Ipsum")
    test_drive = VirtualDrive([lorem_folder], [], 1, 0, "test", "Test Drive", None)

    archive = Archive(info, [test_drive])
    return archive


def build_sample_dow2_archive():
    header = ArchiveHeader(SgaVersion.Dow2.value, "DowII Test Data", bytes([0x00] * 16), bytes([0x00] * 16))

    info = ArchiveInfo(header, None, None)
    raw_content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua." \
                  " Malesuada fames ac turpis egestas. Accumsan lacus vel facilisis volutpat est velit." \
                  " Turpis egestas pretium aenean pharetra magna ac placerat vestibulum lectus. Tellus cras adipiscing enim eu turpis egestas." \
                  " Pellentesque adipiscing commodo elit at imperdiet dui accumsan sit. Massa enim nec dui nunc mattis." \
                  " Gravida in fermentum et sollicitudin ac orci phasellus egestas." \
                  " Eu volutpat odio facilisis mauris sit amet massa vitae. Diam quis enim lobortis scelerisque fermentum dui faucibus.".encode(
        "ascii")
    comp_16_content = compress16(raw_content)
    comp_32_content = compress32(raw_content)

    raw_file = File(FileHeader(None, None, len(raw_content), len(raw_content), None, 0, 0),
                    "Lorem Ipsum Raw", raw_content)
    comp16_file = File(FileHeader(None, None, len(raw_content), len(comp_16_content), None, 0, 0),
                       "Lorem Ipsum Zlib-16", comp_16_content)
    comp32_file = File(FileHeader(None, None, len(raw_content), len(comp_32_content), None, 0, 0),
                       "Lorem Ipsum Zlib-32", comp_32_content)
    lorem_folder = Folder([], [raw_file, comp16_file, comp32_file], 0, 3, FolderHeader(None, None, None), "Lorem Ipsum")
    test_drive = VirtualDrive([lorem_folder], [], 1, 0, "test", "Test Drive", None)

    archive = Archive(info, [test_drive])
    return archive

def build_sample_dow3_archive():
    header = ArchiveHeader(SgaVersion.Dow3.value, "DowIII Test Data")

    info = ArchiveInfo(header, None, None)
    raw_content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua." \
                  " Malesuada fames ac turpis egestas. Accumsan lacus vel facilisis volutpat est velit." \
                  " Turpis egestas pretium aenean pharetra magna ac placerat vestibulum lectus. Tellus cras adipiscing enim eu turpis egestas." \
                  " Pellentesque adipiscing commodo elit at imperdiet dui accumsan sit. Massa enim nec dui nunc mattis." \
                  " Gravida in fermentum et sollicitudin ac orci phasellus egestas." \
                  " Eu volutpat odio facilisis mauris sit amet massa vitae. Diam quis enim lobortis scelerisque fermentum dui faucibus.".encode(
        "ascii")
    comp_16_content = compress16(raw_content)
    comp_32_content = compress32(raw_content)

    raw_file = File(FileHeader(None, None, len(raw_content), len(raw_content), None, None, None, 0, 0, 0, 0, 0),
                    "Lorem Ipsum Raw", raw_content)
    comp16_file = File(FileHeader(None, None, len(raw_content), len(comp_16_content), None, None, None, 0, 0, 0, 0, 0),
                       "Lorem Ipsum Zlib-16", comp_16_content)
    comp32_file = File(FileHeader(None, None, len(raw_content), len(comp_32_content), None, None, None, 0, 0, 0, 0, 0),
                       "Lorem Ipsum Zlib-32", comp_32_content)
    lorem_folder = Folder([], [raw_file, comp16_file, comp32_file], 0, 3, FolderHeader(None, None, None), "Lorem Ipsum")
    test_drive = VirtualDrive([lorem_folder], [], 1, 0, "test", "Test Drive", None)

    archive = Archive(info, [test_drive])
    return archive

if __name__ == "__main__":
    root = get_testdata_root_folder()
    archive = build_sample_dow1_archive()
    with open(join(root, "archive-v2_0.sga"), "wb") as file:
        write_archive(file, archive)

    archive2 = build_sample_dow2_archive()
    with open(join(root, "archive-v5_0.sga"), "wb") as file:
        write_archive(file, archive2)

    archive3 = build_sample_dow3_archive()
    with open(join(root, "archive-v9_0.sga"), "wb") as file:
        write_archive(file, archive3)
