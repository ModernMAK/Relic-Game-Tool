import os
from os.path import join, dirname, splitext
from typing import List, Iterable, Tuple, Optional

from relic.chunky.relic_chunky import RelicChunky
from relic.sga.archive import Archive
from relic.sga.file import File
from relic.sga.file_collection import ArchiveWalkResult
from relic.sga.magic import ARCHIVE_MAGIC_WALKER
from relic.shared import filter_walk_by_extension, collapse_walk_on_files, filter_walk_by_keyword, KW_LIST, \
    filter_path_by_extension, fix_extension_list


#
# def dump_chunky(full_in: str, full_out: str, ignore_errors: bool = False):
#     print(full_in)
#     with open(full_in, "rb") as handle:
#         try:
#             chunky = RelicChunky.unpack(handle)
#         except Exception as e:
#             if ignore_errors:
#                 print("!!!\t\t", e)
#             else:
#                 raise
#
#                 # except TypeError as e:
#         #     # if skip_fatal:
#         #     #     print(f"\tIgnoring:\n\t\t'{e}'\n\t- - -")
#         #     #     return
#         #     # print(f"\tDumping?!\n\t\t'{e}'")
#         #     # log = full_out + ".crash"
#         #     # print(f"\n\n@ {log}")
#         #     # with open(log, "wb") as crash:
#         #     #     handle.seek(0, 0)
#         #     #     crash.write(handle.read())
#         #     #     raise
#         # except ValueError as e:
#         #     print(f"\tNot Chunky?!\n\t\t'{e}'")
#         #     if skip_fatal:
#         #         return
#         #     raise
#
#         # print("\tWriting Assets...")
#         for path, _, _, data in chunky.walk_chunks():
#             for i, chunk in enumerate(data):
#                 dump_name = join(full_out, path, f"{chunk.header.id}-{i + 1}")
#                 try:
#                     os.makedirs(dirname(dump_name))
#                 except FileExistsError:
#                     pass
#                 with open(dump_name, "wb") as writer:
#                     writer.write(chunk.data)
#
#
# def dump_all_chunky(full_in: str, full_out: str, exts: List[str] = None):
#     for file in collapse_walk_on_files(filter_walk_by_extension(os.walk(full_in), exts)):
#         dump = file.replace(full_in, full_out, 1)
#         dump_chunky(file, dump)



if __name__ == "__main__":
    # dump all Warhammer Models as bin
    dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\chunky-bin", "whm")
    # import cProfile
    # cProfile.run('dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-chunky", [".whm"])')
