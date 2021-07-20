import json
import os
from os.path import join

from relic.chunk_formats.shared.imag.writer import get_imag_chunk_extension, create_image
from relic.chunk_formats.wtp.writer import create_mask_image
from relic.chunk_formats.wtp.wtp_chunky import WtpChunky
# from relic.chunky.dumper import dump_all_chunky
from relic.chunky.relic_chunky import RelicChunky
# from relic.shared import EnhancedJSONEncoder, walk_ext

WTP_LAYER_NAMES = {
    0: "Primary",
    1: "Secondary",
    2: "Trim",
    3: "Weapon",
    4: "Detail",  # AKA Trim2

    # This appears to be a mask texture; with black being use the WTP layers and white being the base image color
    # I named it dirt because the first texture I saw of it; was a dirt texture
    # Despite being dirt, its also general scuffs and damage done to armor
    5: "Dirt",
}

#
# def raw_dump():
#     dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\wtp-chunky", [".wtp"])
#
#
# def meta_dump():
#     for root, file in walk_ext(r"D:\Dumps\DOW I\sga", [".wtp"]):
#         full = join(root, file)
#         print_meta(full)
#
#
# def print_meta(f: str):
#     with open(f, "rb") as handle:
#         try:
#             chunky = RelicChunky.unpack(handle)
#         except TypeError as e:
#             print(e)
#             return
#         rsh = WtpChunky.create(chunky)
#         meta = json.dumps(rsh, indent=4, cls=EnhancedJSONEncoder)
#         print(meta)
#
#
# def dump_wtp_as_image(f: str, o: str):
#     wtp = get_wtp(f)
#     if not wtp:
#         print(f"Cant parse '{f}'")
#         return
#
#     imag = wtp.tpat.imag
#     ext = get_imag_chunk_extension(imag.attr.img)
#     try:
#         os.makedirs(o)
#     except FileExistsError:
#         pass
#
#     main = join(o, "main" + ext)
#     with open(main, "wb") as writer:
#         create_image(writer, imag)
#     for p in wtp.tpat.ptld:
#         layer = join(o, f"layer-{_LAYER_NAMES.get(p.layer)}.tga")
#         with open(layer, "wb") as writer:
#             create_mask_image(writer, p, wtp.tpat.info)
#
#
# def get_wtp(f: str):
#     with open(f, "rb") as handle:
#         try:
#             chunky = RelicChunky.unpack(handle)
#             rsh = WtpChunky.create(chunky)
#             return rsh
#         except TypeError:
#             return None
#
#
# def dump_all_wtp_as_image(f: str, o: str):
#     for root, file in walk_ext(f, ["wtp"]):
#         src = join(root, file)
#         dest = src.replace(f, o, 1)
#         print(src)
#         print("\t", dest)
#         try:
#             dump_wtp_as_image(src, dest)
#         except NotImplementedError as e:
#             print("\t\t", e)
#
#
# if __name__ == "__main__":
#     # meta_dump()
#     # raw_dump()
#     dump_all_wtp_as_image(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\wtp")
#     # fix_texture_inverstion("D:\Dumps\DOW I\dds")
