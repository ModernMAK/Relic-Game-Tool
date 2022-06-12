# from __future__ import annotations

# from io import BytesIO
# from relic.sga import Archive
# from write_sga_samples import build_sample_dow1_archive, build_sample_dow3_archive, build_sample_dow2_archive
#
#
# def assert_archives(left: Archive, right: Archive):
#     # ASSERT HEADER
#     assert left.header == right.header, (left.header, right.header)
#     v = left.header.version
#
#     # # ASSERT TOC
#     # l_toc, r_toc = left.info.table_of_contents, right.info.table_of_contents
#     # assert l_toc.drive_info.count == r_toc.drive_info.count
#     # assert l_toc.files_info.count == r_toc.files_info.count
#     # if l_toc.filenames_info.count:
#     #     assert l_toc.filenames_info.count == r_toc.filenames_info.count
#     # else:
#     #     assert l_toc.filenames_info.byte_size == r_toc.filenames_info.byte_size
#     # assert l_toc.folders_info.count == r_toc.folders_info.count
#
#     r_lookup = {d.path: d for d in right.drives}
#     l_lookup = {d.path: d for d in left.drives}
#     assert len(r_lookup) == len(l_lookup), "Drive Count"
#     for key in l_lookup:
#         assert key in r_lookup, "Drive Not Found"
#
#     # TODO assert folders and files
#
#
# def run_test(archive: Archive):
#     with BytesIO() as buffer:
#         archive.pack(buffer, True)
#         buffer.seek(0)
#         gen_archive = Archive.unpack(buffer)
#         assert_archives(archive, gen_archive)
#
#
# def test_archive_DowI():
#     archive = build_sample_dow1_archive()
#     run_test(archive)
#
#
# def test_archive_Dow2():
#     archive = build_sample_dow2_archive()
#     run_test(archive)
#
#
# def test_archive_Dow3():
#     archive = build_sample_dow3_archive()
#     run_test(archive)
