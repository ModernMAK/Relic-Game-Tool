from io import BytesIO

from relic.chunky import RelicChunky, DataChunk, FolderChunk, ChunkyVersion
# from relic.sga import Archive, writer, File, Folder
from write_chunky_samples import build_sample_chunky_v1_1


def assert_chunies(left: RelicChunky, right: RelicChunky):
    # ASSERT HEADER
    assert left.header == right.header, "Chunky Version Mismatch"
    v = left.header.version
    assert len(left.chunks) == len(right.chunks), "Chunk Count Mismatch"
    for left, right in zip(left.walk_chunks(True, False), right.walk_chunks(True, False)):
        l_path, l_folders, l_datas = left
        r_path, r_folders, r_datas = right

        assert l_path == r_path, "Chunk Path Mismatch"
        assert len(l_folders) == len(r_folders), "Chunk Folder Count Mismatch"
        for l_folder, r_folder in zip(l_folders, r_folders):
            l_folder: FolderChunk
            r_folder: FolderChunk
            # WE do it manualy since we don't expect size to be correct for manually built chunkies
            assert l_folder.header.version == r_folder.header.version, "Chunk Folder Header ('Version') Mismatch"
            assert l_folder.header.name == r_folder.header.name, "Chunk Folder Header ('Name') Mismatch"
            assert l_folder.header.type == r_folder.header.type, "Chunk Folder Header ('Type') Mismatch"
            assert l_folder.header.id == r_folder.header.id, "Chunk Folder Header ('Id') Mismatch"
            if v == ChunkyVersion.v3_1:
                assert l_folder.header.unk_v3_1 == r_folder.header.unk_v3_1, "Chunk Folder Header ('Unks v3.1') Mismatch"

        assert len(l_datas) == len(r_datas), "Chunk Data Count Mismatch"
        for l_data, r_data in zip(l_datas, r_datas):
            l_data: DataChunk
            r_data: DataChunk
            assert l_data.header.equal(r_data.header, v), "Chunk Data Header Mismatch"
            assert len(l_data.data) == len(r_data.data), "Chunk Data Size Mismatch"
            for i in range(len(l_data.data)):
                assert l_data.data[i] == r_data.data[i], f"Chunk Data Mismatch @{i}"

    # for path, folders, datas in left.walk_chunks()

    # assert len(r_lookup) == len(l_lookup), "Drive Count"
    # for key in l_lookup:
    #     assert key in r_lookup, "Drive Not Found"
    #
    # for path, folders, files in left.walk(True):
    #     for l_folder in folders:
    #         r_folder: Folder = right.get_from_path(path, l_folder.name)
    #         assert r_folder is not None, "Folder Not Found"
    #         assert r_folder.name == l_folder.name, "Foldern Name"
    #         assert r_folder.folder_count() == l_folder.folder_count(), "Folder Subfolder Count"
    #         assert r_folder.file_count() == l_folder.file_count(), "Folder File Count"
    #     for l_file in files:
    #         r_data: File = right.get_from_path(path, l_file.name)
    #         assert r_data is not None, "File Not Found"
    #         assert r_data.name == l_file.name, "File Name"
    #         assert len(r_data.data) == len(l_file.data), f"File Data Length"
    #         for i in range(len(r_data.data)):
    #             assert r_data.data[i] == l_file.data[i], f"File Data Mismatch @{i}"
    #         assert r_data.header.decompressed_size == l_file.header.decompressed_size, "File Decompressed Size"
    #         assert r_data.header.compressed_size == l_file.header.compressed_size, "File Compressed Size"
    #         # TODO assert file flags


def run_test(chunky: RelicChunky):
    with BytesIO() as buffer:
        chunky.pack(buffer)
        buffer.seek(0)
        generated = RelicChunky.unpack(buffer)
        assert_chunies(chunky, generated)


def test_chunky_v1_1():
    archive = build_sample_chunky_v1_1()
    run_test(archive)
