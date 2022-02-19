from io import BytesIO
from relic.sga.sga import Archive, File, Folder, write_archive
from write_sga_samples import build_sample_dow1_archive, build_sample_dow3_archive, build_sample_dow2_archive


def assert_archives(left: Archive, right: Archive):
    # ASSERT HEADER
    assert left.info.header == right.info.header, (left.info.header, right.info.header)
    v = left.info.header.version

    # # ASSERT TOC
    # l_toc, r_toc = left.info.table_of_contents, right.info.table_of_contents
    # assert l_toc.drive_info.count == r_toc.drive_info.count
    # assert l_toc.files_info.count == r_toc.files_info.count
    # if l_toc.filenames_info.count:
    #     assert l_toc.filenames_info.count == r_toc.filenames_info.count
    # else:
    #     assert l_toc.filenames_info.byte_size == r_toc.filenames_info.byte_size
    # assert l_toc.folders_info.count == r_toc.folders_info.count

    r_lookup = {d.path: d for d in right.drives}
    l_lookup = {d.path: d for d in left.drives}
    assert len(r_lookup) == len(l_lookup), "Drive Count"
    for key in l_lookup:
        assert key in r_lookup, "Drive Not Found"

    for path, folders, files in left.walk(True):
        for l_folder in folders:
            r_folder: Folder = right.get_from_path(path, l_folder.name)
            assert r_folder is not None, "Folder Not Found"
            assert r_folder.name == l_folder.name, "Foldern Name"
            assert r_folder.folder_count() == l_folder.folder_count(), "Folder Subfolder Count"
            assert r_folder.file_count() == l_folder.file_count(), "Folder File Count"
        for l_file in files:
            r_file: File = right.get_from_path(path, l_file.name)
            assert r_file is not None, "File Not Found"
            assert r_file.name == l_file.name, "File Name"
            assert len(r_file.data) == len(l_file.data), f"File Data Length"
            for i in range(len(r_file.data)):
                assert r_file.data[i] == l_file.data[i], f"File Data Mismatch @{i}"
            assert r_file.header.decompressed_size == l_file.header.decompressed_size, "File Decompressed Size"
            assert r_file.header.compressed_size == l_file.header.compressed_size, "File Compressed Size"
            # TODO assert file flags


def run_test(archive: Archive):
    with BytesIO() as buffer:
        write_archive(buffer, archive)
        buffer.seek(0)
        gen_archive = Archive.unpack(buffer)
        assert_archives(archive, gen_archive)


def test_archive_DowI():
    archive = build_sample_dow1_archive()
    run_test(archive)


def test_archive_Dow2():
    archive = build_sample_dow2_archive()
    run_test(archive)


def test_archive_Dow3():
    archive = build_sample_dow3_archive()
    run_test(archive)
