# A personal script using what I have so far to dump WTP files as 3 PNGs (1 Albedo, 2 Splat Masks)
#   Splat 1 - Primary, Secondary, Trim & Splat 2 - Weapon, Detail, Dirt
#       Dirt is inclluded in Splat2 so that both pngs can be RGB instead of RGBA's (although having dirt be in both Alphas would also be a decent solution)
import os
from io import BytesIO
from os.path import join, splitext, basename
from typing import List, Dict

from PIL import Image
from PIL.Image import Image as PilImage
from relic.rsh import create_image
from relic.shared import walk_ext
from relic.wtp import get_wtp, create_mask_image, _LAYER_NAMES


def dump_wtp_as_compact(f: str, o: str):
    MAIN_EXT = "_Albedo.png"
    SPLAT_1_EXT = "_TeamMajorSplat.png"  # IDK what to call them
    SPLAT_2_EXT = "_TeamMinorSplat.png"

    n = basename(o)

    wtp_chunky = get_wtp(f)

    if wtp_chunky is None:
        raise NotImplementedError(f"'{f} couldn't be processed.")

    try:
        os.makedirs(o)
    except FileExistsError:
        pass

    # Create a 'file' that we can write our TGAs to
    # Shared buffer seems to not work? I assume its because Pillow is lazy
    with BytesIO() as main_buffer:
        # Start by dumping main
        create_image(main_buffer, wtp_chunky.tpat.imag)
        # Fix file pointer to allow for reading
        main_buffer.seek(0)
        # Read
        main: PilImage = Image.open(main_buffer)
        # Save
        with open(join(o, n + MAIN_EXT), "wb") as handle:
            main.save(handle, format="png")

    # Setup vars for team layers
    info = wtp_chunky.tpat.info
    size = (info.width, info.height)

    # Read in layer images, to merge them they need to be all loaded in
    # Technically only each batch of 3,
    # but this allows me to easily replace it with the black/white default layers
    imgs: Dict[int, PilImage] = {}
    buffers: List[BytesIO] = []
    for ptld in wtp_chunky.tpat.ptld:
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
                # channels_1[0].show()
                # channels_1[1].show()
                # channels_1[2].show()
                # splat_1.show()
                with open(join(o, n + SPLAT_1_EXT), "wb") as handle:
                    splat_1.save(handle, format="png")
            # Write second splat
            with Image.merge("RGB", channels_2) as splat_2:
                splat_2: PilImage
                with open(join(o, n + SPLAT_2_EXT), "wb") as handle:
                    splat_2.save(handle, format="png")

        for img in imgs.values():
            img.close()
        for buffer in buffers:
            buffer.close()


def dump_all_wtp_as_image(f: str, o: str):

    for root, file in walk_ext(f, ["wtp"]):
        src = join(root, file)
        partial = src.replace(f, "", 1).lstrip("\\").lstrip("/")
        dest = join(o, partial)
        dest, _ = splitext(dest)
        print(f"...\\{partial}")
        try:
            dump_wtp_as_compact(src, dest)
        except NotImplementedError as e:
            print("\t", e)


if __name__ == "__main__":
    dump_all_wtp_as_image(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\teamable textures")
    # dump_all_wtp_as_image(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard", r"D:\Dumps\DOW I\teamable textures\art\ebps\races\imperial_guard")
    # dump_all_wtp_as_image(r"D:\Dumps\DOW I\sga\art\ebps\races\imperial_guard\texture_share\ig_guardsmen_sergeant_default.wtp", r"D:\Dumps\DOW I\teamable textures\art\ebps\races\imperial_guard\texture_share\ig_guardsmen_sergeant_default")
