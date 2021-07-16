# A personal script using what I have so far to dump WTP files as 3 PNGs (1 Albedo, 2 Splat Masks) Splat 1 - Primary,
# Secondary, Trim & Splat 2 - Weapon, Detail, Dirt Dirt is inclluded in Splat2 so that both pngs can be RGB instead
# of RGBA's (although having dirt be in both Alphas would also be a decent solution)
import os
from contextlib import contextmanager
from io import BytesIO
from os.path import join, split
from typing import List, Dict, BinaryIO, Tuple, Union

from PIL import Image
from PIL.Image import Image as PilImage

from relic.chunk_formats.rsh import create_image
from relic.chunk_formats.wtp import get_wtp, create_mask_image, WtpFile
from relic.sga import FlatArchive, FullArchive
from relic.shared import walk_ext


def dump_file_as_compact(f: str, o: str):
    wtp = get_wtp(f)
    dump_wtp_as_compact(wtp, o)


def dump_wtp_as_compact(wtp: WtpFile, o: str):
    compacts = open_streams(o)
    write_compact(wtp, compacts)


@contextmanager
def open_streams(o: str) -> Tuple[BinaryIO, BinaryIO, BinaryIO]:
    dirname, filename = split(o)
    MAIN_EXT = "_Albedo.png"
    SPLAT_1_EXT = "_TeamMajorSplat.png"  # IDK what to call them
    SPLAT_2_EXT = "_TeamMinorSplat.png"
    try:
        os.makedirs(o)
    except FileExistsError:
        pass

    with open(join(dirname, filename, filename + MAIN_EXT), "wb") as albedo:
        with open(join(dirname, filename, filename + SPLAT_1_EXT), "wb") as splat1:
            with open(join(dirname, filename, filename + SPLAT_2_EXT), "wb") as splat2:
                yield albedo, splat1, splat2


def write_compact(wtp: WtpFile, compacts: Tuple[BinaryIO, BinaryIO, BinaryIO]):
    albedo, splat_major, splat_minor = compacts
    with BytesIO() as main_buffer:
        # Start by dumping main
        create_image(main_buffer, wtp.tpat.imag)
        # Fix file pointer to allow for reading
        main_buffer.seek(0)
        # Read
        main: PilImage = Image.open(main_buffer)
        # Save
        main.save(albedo)

    # Setup vars for team layers
    info = wtp.tpat.info
    size = (info.width, info.height)

    # Read in layer images, to merge them they need to be all loaded in
    # Technically only each batch of 3,
    # but this allows me to easily replace it with the black/white default layers
    imgs: Dict[int, PilImage] = {}
    buffers: List[BytesIO] = []
    for ptld in wtp.tpat.ptld:
        buffer = BytesIO()
        create_mask_image(buffer, ptld, info)
        buffer.seek(0)
        imgs[ptld.layer] = Image.open(buffer)
        buffers.append(buffer)

    # Create default black/white layers
    with Image.new("L", size, 1) as white:
        with Image.new("L", size, 0) as black:
            # group channels as tuple
            channels_1 = imgs.get(0, black), imgs.get(1, black), imgs.get(2, black)
            channels_2 = imgs.get(3, black), imgs.get(4, black), imgs.get(5, white)
            # Write First Splat
            with Image.merge("RGB", channels_1) as splat_1:
                splat_1: PilImage
                splat_1.save(splat_major, format="png")
            # Write second splat
            with Image.merge("RGB", channels_2) as splat_2:
                splat_2: PilImage
                splat_2.save(splat_minor, format="png")

        for img in imgs.values():
            img.close()
        for buffer in buffers:
            buffer.close()


def dump_all_wtp_in_archive(sga: Union[FlatArchive, FullArchive], o: str):
    for path, file in sga.walk_files(exts="wtp"):
        wtp = WtpFile.create(file)
        dump_wtp_as_compact(wtp, join(o, path))


def dump_all_wtp_in_folder(f: str, o: str):
    for root, file in walk_ext(f, ["wtp"]):
        full = join(root, file)
        dump = full.replace(f, o, 1)
        dump_file_as_compact(full, dump)



if __name__ == "__main__":
    dump(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\teamable textures")
