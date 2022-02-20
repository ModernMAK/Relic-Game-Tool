# import os
# from os.path import join, splitext, dirname
# from typing import Tuple, List
# from PIL import Image
#
# from relic.shared import walk_ext
#
#
# def walk_images(folder: str, exts: List[str] = None) -> Tuple[str, str]:
#     exts = exts or [".tga", ".dds", ".jpg", ".jpeg"]
#     return walk_ext(folder, exts)
#
#
# def dump_image(osrc: str, dest: str):
#     try:
#         os.makedirs(dirname(dest))
#     except FileExistsError:
#         pass
#
#     with Image.open(osrc) as handle:
#         handle: Image.Image
#         handle.save(dest)
#
#
# def dump_all_images(folder: str, format: str = ".png", out_dir: str = None, exts: List[str] = None):
#     out_dir = out_dir or "gen/image/shared_dump"
#     for root, file in walk_images(folder, exts):
#         osrc = join(root, file)
#         print(osrc)
#         full = osrc.lstrip(folder).lstrip("\\").lstrip("/")
#         full = join(out_dir, full)
#         n, e = splitext(full)
#         e = e.replace(".", "")
#         full = f"{n} ({e}){format}"
#         print("\t=>\t", full)
#         dump_image(osrc, full)
#
#
# if __name__ == "__main__":
#     dump_all_images(r"D:/Dumps/DOW I/sga",
#                     out_dir=r"D:/Dumps/DOW I/img")
