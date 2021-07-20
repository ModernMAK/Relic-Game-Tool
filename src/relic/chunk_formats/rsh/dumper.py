import json
import os
import subprocess
from os.path import join, dirname, splitext

from relic.chunk_formats.rsh.rsh_chunky import RshChunky
from relic.chunk_formats.shared.imag.writer import create_image, get_imag_chunk_extension
from relic.chunky import RelicChunky
from relic.shared import EnhancedJSONEncoder, walk_ext


def get_rsh(f: str):
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        rsh = RshChunky.create(chunky)
        return rsh


def print_meta(f: str):
    with open(f, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        rsh = RshChunky.create(chunky)
        meta = json.dumps(rsh, indent=4, cls=EnhancedJSONEncoder)
        print(meta)


def dump_rsh_as_image(f: str, o: str):
    rsh = get_rsh(f)

    ext = get_imag_chunk_extension(rsh.shrf.texture.imag.attr.img)
    o, _ = splitext(o)
    o += ext

    try:
        os.makedirs(dirname(o))
    except FileExistsError:
        pass
    try:
        with open(o, "wb") as writer:
            create_image(writer, rsh.shrf.texture.imag)
    except NotImplementedError as e:
        try:
            os.remove(o)
        except FileNotFoundError:
            pass
        raise


def dump_all_rsh_as_image(f: str, o: str):
    for root, file in walk_ext(f, ["rsh"]):
        src = join(root, file)
        dest = src.replace(f, o, 1)
        print(src)
        print("\t", dest)
        try:
            dump_rsh_as_image(src, dest)
        except NotImplementedError as e:
            print("\t\t", e)


def directex_fix_texture(f: str, path: str = r"dll\texconv.exe"):
    path = os.path.abspath(path)
    outdir = dirname(f)
    subprocess.run([path, "-vflip", f, "-y", "-o", outdir])


def fix_texture_inversion(folder: str):
    for root, file in walk_ext(folder, ["dds"]):
        f = join(root, file)
        directex_fix_texture(f)


def convert_all(f: str, o: str, fmt: str = "png", path: str = r"dll\texconv.exe"):
    path = os.path.abspath(path)
    for root, _, files in os.walk(f):
        for file in files:
            file_path = join(root, file)
            output_dir = root.replace(f, o, 1)
            try:
                os.makedirs(output_dir)
            except FileExistsError:
                pass
            subprocess.run([path, "-vflip", file_path, "-y", "-ft", fmt, "-o", output_dir])


if __name__ == "__main__":
    dump_all_rsh_as_image(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\rsh")
    # fix_texture_inversion(r"D:\Dumps\DOW I\rsh")
    convert_all(r"D:\Dumps\DOW I\rsh", r"D:\Dumps\DOW I\textures",fmt="tga")
    # dump_all_rsh_as_image(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\textures\png")
    # fix_texture_inversion("D:\Dumps\DOW I\dds")
