# TODO Dig through this and see how much can be moved to TOC and if any of it must be a separate file

# # Cycles aren't supported (and will crash)
# # Multiple parents will be copied
#
#
# def flatten_folders(collection: AbstractDirectory, flattened: List[Folder]) -> Tuple[int, int]:
#     start = len(flattened)
#     flattened.extend(collection.folders)
#     stop = len(flattened)
#     return start, stop
#
#
# def flatten_files(collection: AbstractDirectory, flattened: List[File]) -> Tuple[int, int]:
#     start = len(flattened)
#     flattened.extend(collection.files)
#     stop = len(flattened)
#     return start, stop
#
#
# # Offset, Count (Items), Size (Bytes)
# def write_virtual_drives(stream: BinaryIO, archive: Archive, version: Version, name_table: Dict[any, int],
#                          recalculate: bool = False) -> Tuple[int, int, int]:
#     running_folder = 0
#     running_file = 0
#     written = 0
#
#     offset = stream.tell()
#     for drive in archive.drives:
#         folder_count = drive.folder_count(recalculate)
#         file_count = drive.file_count(recalculate)
#
#         folder = ArchiveRange(running_folder, running_folder + folder_count)
#         files = ArchiveRange(running_file, running_file + file_count)
#
#         running_folder += folder_count
#         running_file += file_count
#
#         header = VirtualDriveHeader(drive.path, drive.name, folder, files, folder.start)
#         written += header.pack(stream, version)
#
#     return offset, len(archive.drives), written
#
#
# def write_names(stream: BinaryIO, archive: Archive) -> Tuple[int, int, int, Dict[str, int]]:
#     offset = stream.tell()
#     running_total = 0
#     lookup = {}
#     written = 0
#
#     def try_write_null_terminated(name: str) -> int:
#         if name in lookup:
#             return 0
#         # We must use relative offset to data_origin
#         lookup[name] = stream.tell() - offset
#         terminated_name = name
#         if name[-1] != "\0":
#             terminated_name += "\0"
#         encoded = terminated_name.encode("ascii")
#         return stream.write(encoded)
#
#     # This will not re-use repeated names; we could change it, but I won't since my brain is over-optimizing this
#     #   By allowing names to repeat, we avoid perform hash checks in a dictionary (or equality comparisons in a list)
#     for drive in archive.drives:
#         for _, folders, files in drive.walk():
#             for f in folders:
#                 written += try_write_null_terminated(f.name)
#                 running_total += 1
#             for f in files:
#                 written += try_write_null_terminated(f.name)
#                 running_total += 1
#
#     return offset, running_total, written, lookup
#
#
# # Offset, Count (Items), Size (Bytes)
# def write_folders(stream: BinaryIO, archive: Archive, version: Version, name_lookup: Dict[str, int],
#                   recalculate: bool = False) -> Tuple[
#     int, int, int]:
#     running_folder = 0
#     running_file = 0
#     written = 0
#     total_folders = 0
#     offset = stream.tell()
#     for drive in archive.drives:
#         for _, folders, _ in drive.walk():
#             for folder in folders:
#                 total_folders += 1
#                 folder_count = folder.folder_count(recalculate)
#                 file_count = folder.file_count(recalculate)
#
#                 folder_range = ArchiveRange(running_folder, running_folder + folder_count)
#                 file_range = ArchiveRange(running_file, running_file + file_count)
#
#                 running_folder += folder_count
#                 running_file += file_count
#
#                 name_offset = name_lookup[folder.name]
#
#                 header = FolderHeader(name_offset, folder_range, file_range)
#                 written += header.pack(stream, version)
#
#     return offset, total_folders, written
#
#
# def get_v2_compflag(comp_data: bytes, decomp_data: bytes):
#     if len(comp_data) == len(decomp_data):
#         return FileCompressionFlag.Decompressed
#     flag = (comp_data[0] & 0xF0) >> 4
#     lookup = {7: FileCompressionFlag.Compressed32, 6: FileCompressionFlag.Compressed16}
#     return lookup[flag]
#
#
# def get_v9_compflag(comp_data: bytes, decomp_data: bytes):
#     if len(comp_data) == len(decomp_data):
#         return 0
#     flag = (comp_data[0] & 0xF0) >> 4
#     lookup = {7: FileCompressionFlag.Compressed32, 6: FileCompressionFlag.Compressed16}
#     return lookup[flag]
#
#
# # Lookup ~ Offset, Copmressed, Decompressed, Version Args
# # Offset, Count, Byte Size
# def write_file_data(stream: BinaryIO, archive: Archive, version: Version, auto_compress: bool = True) -> Tuple[
#     int, int, int, Dict[File, FileHeader]]:
#     offset = stream.tell()
#
#     KIBI = 1024
#     Kb16 = 16 * KIBI
#     Kb32 = 32 * KIBI
#
#     lookup = {}
#
#     def write_info(compressed_data: bytes, decompressed_data: bytes) -> FileHeader:
#         # We must use relative offset to data_origin
#         data_offset = stream.tell() - offset
#
#         if version == ArchiveVersion.Dow:
#             compression_flag = get_v2_compflag(decompressed_data, decompressed_data)
#             header = DowIFileHeader(None, data_offset, len(decompressed_data), len(compressed_data), compression_flag)
#         elif version == ArchiveVersion.Dow2:
#             header = DowIIFileHeader(None, data_offset, len(decompressed_data), len(compressed_data), 0, 0)
#         elif version == ArchiveVersion.Dow3:
#             # TODO rename unk_d to compression_flag
#             compression_flag = get_v9_compflag(decompressed_data, decompressed_data)
#             header = DowIIIFileHeader(None, data_offset, len(decompressed_data), len(compressed_data), 0, 0, 0, compression_flag, 0)
#         else:
#             raise NotImplementedError(version)
#         stream.write(compressed_data)
#         return header
#
#     for drive in archive.drives:
#         for _, _, files in drive.walk():
#             for file in files:
#                 comp_data = file.data
#                 decomp_data = file.get_decompressed()
#
#                 if not auto_compress:  # Just dump it and GO!
#                     header = write_info(comp_data, decomp_data)
#                 else:
#                     # This is rather arbitrary, but these are my rules for auto-copmression:
#                     # Don't compress files that...
#                     #   Are compressed (duh)
#                     #   Are smaller than the largest (16-KibiBytes) compression window
#                     # When Compressing Files...
#                     #   If the data size is less than 256 KibiBytes
#                     #       Use 16-KbB Window
#                     #   Otherwise
#                     #       Use 32-KbB Window
#                     if len(comp_data) != len(decomp_data):  # Compressed; just write as is
#                         header = write_info(comp_data, decomp_data)
#                     elif len(decomp_data) < Kb16:  # Too small
#                         header = write_info(comp_data, decomp_data)
#                     else:
#                         if len(decomp_data) < KIBI:  # Use Window 16KbB
#                             compressor = zlib.compressobj(wbits=14)
#                         else:  # Use Window 32KbB
#                             compressor = zlib.compressobj(wbits=15)
#                         # Compress; because we are using compression obj, we need to use a temp
#                         with BytesIO() as temp:
#                             temp.write(compressor.compress(comp_data))
#                             temp.write(compressor.flush())
#                             temp.seek(0)
#                             comp_data = temp.read()
#                         header = write_info(comp_data, decomp_data)
#                 lookup[file] = header
#
#     stop = stream.tell()
#     size = stop - offset
#     return offset, len(lookup), size, lookup
#
#
# def write_files(stream: BinaryIO, archive: Archive, version: Version, name_lookup: Dict[str, int],
#                 data_lookup: Dict[File, FileHeader]) -> Tuple[int, int, int]:
#     offset = stream.tell()
#     written = 0
#     file_count = 0
#
#     for drive in archive.drives:
#         for _, _, files in drive.walk():
#             for file in files:
#                 header = data_lookup[file]
#                 header.name_subptr = name_lookup[file.name]
#                 written += header.pack_version(stream, version)
#                 file_count += 1
#
#     return offset, file_count, written
#
#
# def write_table_of_contents(stream: BinaryIO, archive: Archive, version: Version,
#                             data_lookup: Dict[File, FileHeader], recalculate_totals: bool = True) -> Tuple[int, int]:
#     if recalculate_totals:
#         for d in archive.drives:
#             d.folder_count(True)
#             d.file_count(True)
#
#     toc_offset = stream.tell()
#     toc_size = ArchiveToC.get_size(version)
#     stream.write(bytes([0x00] * toc_size))
#
#     # Names needs to be computer first, but DOW's layout is Drives, Folders, Files, Names (not that it HAS to be)
#     #   I follow their pattern for consistency if nothing else
#     #       THIS ONLY WORKS BECAUSE OFFSETS ARE RELATIVE TO THE NAME OFFSET
#     with BytesIO() as name_buffer:
#         _, name_count, name_size, name_lookup = write_names(name_buffer, archive)
#
#         vd_offset, vd_count, vd_size = write_virtual_drives(stream, archive, version, name_lookup)
#         vd_part = OffsetInfo(toc_offset, vd_offset - toc_offset, vd_count)
#
#         fold_offset, fold_count, fold_size = write_folders(stream, archive, version, name_lookup)
#         fold_part = OffsetInfo(toc_offset, fold_offset - toc_offset, fold_count)
#
#         file_offset, file_count, file_size = write_files(stream, archive, version, name_lookup, data_lookup)
#         file_part = OffsetInfo(toc_offset, file_offset - toc_offset, file_count)
#
#         name_offset = stream.tell()
#         name_buffer.seek(0)
#         stream.write(name_buffer.read())
#         name_part = FilenameOffsetInfo(toc_offset, name_offset - toc_offset, name_count, name_size)
#
#         end = stream.tell()
#         # Writeback proper TOC
#         toc = ArchiveTableOfContents(vd_part, fold_part, file_part, name_part)
#         stream.seek(toc_offset)
#         toc.pack(stream, version)
#
#         stream.seek(end)
#         return toc_offset, end - toc_offset
#
#
# def write_archive(stream: BinaryIO, archive: Archive, auto_compress: bool = True, recalculate_totals: bool = True) -> int:
#     version = archive.info.header.version
#
#     if version not in [ArchiveVersion.Dow, ArchiveVersion.Dow2, ArchiveVersion.Dow3]:
#         raise NotImplementedError(version)
#
#     start = stream.tell()
#     # PRIMARY HEADER
#     archive.info.header.pack(stream)
#
#     # SUB HEADER SETUP
#     #   We need to do a write-back once we know the offsets, sizes, what have you
#     subheader_offset = stream.tell()
#
#     subheader = ArchiveSubHeader.default(version)
#     subheader.pack(stream, version)  # Write filler data
#
#     # TOC & DATA
#     if version == ArchiveVersion.Dow:
#         # Unfortunately, we depend on Data Buffer to write TOC, and TOC 'MUST' come immediately after the Sub Header in Sga-V2.0
#         #   So we write data to a memory buffer before rewriting to a
#         with BytesIO() as data_buffer:
#             _, _, _, data_lookup = write_file_data(data_buffer, archive, version, auto_compress)
#             toc_offset, toc_size = write_table_of_contents(stream, archive, version, data_lookup, recalculate_totals)
#             data_offset = stream.tell()
#             data_buffer.seek(0)
#             stream.write(data_buffer.read())
#         subheader = ArchiveSubHeader(toc_size, data_offset, toc_offset)
#
#     elif version in [ArchiveVersion.Dow2, ArchiveVersion.Dow3]:
#         # Since these formats can point to TOC specifically, I write to the stream directly
#         data_offset, _, data_size, data_lookup = write_file_data(stream, archive, version, auto_compress)
#         toc_offset, toc_size = write_table_of_contents(stream, archive, version, data_lookup, recalculate_totals)
#         if version == ArchiveVersion.Dow2:
#             subheader = ArchiveSubHeader(toc_size, data_offset, toc_offset, 1, 0, 0)
#         elif version == ArchiveVersion.Dow3:
#             subheader = ArchiveSubHeader(toc_size, data_offset, toc_offset, None, None, None, 0, 0, 1,
#                                          bytes([0x00] * 256), data_size)
#         else:
#             raise NotImplementedError(version)  # In case I add to the list in the above if and forget to add it here
#
#     end = stream.tell()
#     stream.seek(subheader_offset)
#     subheader.pack(stream, version)
#
#     stream.seek(end)
#     return end - start
