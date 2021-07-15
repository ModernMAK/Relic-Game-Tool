import os
from os.path import join, dirname
from typing import List

from relic.chunky.chunk_header import ChunkType
from relic.chunky.relic_chunky import RelicChunky
from relic.shared import walk_ext


def dump_chunky(full_in: str, full_out: str, ignore_errors: bool = False):
    print(full_in)
    with open(full_in, "rb") as handle:
        try:
            chunky = RelicChunky.unpack(handle)
        except Exception as e:
            if ignore_errors:
                print("!!!\t\t", e)
            else:
                raise

                # except TypeError as e:
        #     # if skip_fatal:
        #     #     print(f"\tIgnoring:\n\t\t'{e}'\n\t- - -")
        #     #     return
        #     # print(f"\tDumping?!\n\t\t'{e}'")
        #     # log = full_out + ".crash"
        #     # print(f"\n\n@ {log}")
        #     # with open(log, "wb") as crash:
        #     #     handle.seek(0, 0)
        #     #     crash.write(handle.read())
        #     #     raise
        # except ValueError as e:
        #     print(f"\tNot Chunky?!\n\t\t'{e}'")
        #     if skip_fatal:
        #         return
        #     raise

        # print("\tWriting Assets...")
        for path, _, _, data in chunky.walk_chunks():
            for i, chunk in enumerate(data):
                dump_name = join(full_out, path, f"{chunk.header.id}-{i + 1}")
                try:
                    os.makedirs(dirname(dump_name))
                except FileExistsError:
                    pass
                with open(dump_name, "wb") as writer:
                    writer.write(chunk.data)


def dump_all_chunky(full_in: str, full_out: str, exts: List[str] = None):
    for root, file in walk_ext(full_in, exts):
        i = join(root, file)
        j = i.replace(full_in, "", 1)
        j = j.lstrip("\\")
        j = j.lstrip("/")
        o = join(full_out, j)
        dump_chunky(i, o)


if __name__ == "__main__":
    dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-chunky", [".whm"])
    # import cProfile
    # cProfile.run('dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whm-chunky", [".whm"])')
