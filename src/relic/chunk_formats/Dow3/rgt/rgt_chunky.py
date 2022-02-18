# D
import zlib
from math import log
from os.path import join
from struct import Struct

# I must be missing something obvious; This seemes to be a DDS (DXT) image with mips; but it also seems to be compressed with zlib deflate?

if __name__ == "__main__":
    root_path = r"D:\Dumps\DOW_III\full_dump\art\armies\astra_militarum\troops\cadian\armour\varlock_guard_standard_common\varlock_guard_standard_common_dif\TSET-1\TXTR-1\DXTC-1"
    tman_file = join(root_path, r"TMAN-Chunk-0.bin")
    tdat_file = r"TDAT-Chunk-1.bin"

    tdat_out_file = r"TDAT-Chunk-1.decompressed-{}.bin"

    with open(join(root_path,tman_file), "rb") as tman_handle:
        # with open(out_file, "wb") as out_handle:
        tman_handle.seek(4)
        tex_width, tex_height = Struct("< L L").unpack(tman_handle.read(8))
    mips = max(log(tex_width, 2), log(tex_height, 2))
    with open(join(root_path,tdat_file), "rb") as tdat_handle:
        tdat_handle.seek(4)
        buffer = tdat_handle.read()
        H = bytes([0x78, 0xDA])
        parts = buffer.split(H)
        fixed_parts = [H+p for p in parts[1:]]
    assert len(fixed_parts) == mips
    for i, data in enumerate(fixed_parts):
        with open(join(root_path,tdat_out_file.format(i)), "wb") as tdat_out_handle:
            decomp = zlib.decompress(data)
            tdat_out_handle.write(decomp)

#
# if __name__ == "__main__":
#     root_path = r"D:\Dumps\DOW_III\full_dump\art\armies\astra_militarum\troops\cadian\armour\varlock_guard_standard_common\varlock_guard_standard_common_dif\TSET-1\TXTR-1\DXTC-1"
#     in_file = join(root_path, r"TDAT-Chunk-1.bin")
#     out_file = join(root_path, r"TDAT-Chunk-1.decompressed.bin")
#
#     with open(in_file, "rb") as in_handle:
#         with open(out_file, "wb") as out_handle:
#             value = in_handle.read(4)
#             buffer = in_handle.read()
#             decomp_buffer = zlib.decompress(buffer)
#             out_handle.write(decomp_buffer)
