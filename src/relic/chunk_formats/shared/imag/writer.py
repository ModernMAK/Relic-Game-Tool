import os
import subprocess
from io import BytesIO
from os.path import dirname
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Dict

from relic.chunk_formats.shared.imag.imag_chunk import ImagChunk
from relic.file_formats.dxt import get_full_dxt_header, build_dow_tga_color_header, DDS_MAGIC

_DDS_FORMAT_LOOKUP: Dict[int, str] = {
    8: "DXT1",
    10: "DXT3",
    11: "DXT5",
}
_DDS_FORMATS = [id for id, _ in _DDS_FORMAT_LOOKUP.items()]
_TGA_FORMATS = [0]


def get_imag_chunk_extension(format: int) -> str:
    if format in _TGA_FORMATS:
        return ".tga"
    elif format in _DDS_FORMATS:
        return ".dds"
    else:
        raise NotImplementedError(format)


# Dumps the raw image, DDS images will be inverted, TGA images will be normal
def create_image(stream: BinaryIO, chunk: ImagChunk):
    info = chunk.attr
    data = chunk.data.data
    if info.img in _DDS_FORMATS:
        # DDS
        dds_format = _DDS_FORMAT_LOOKUP[info.img]
        header = get_full_dxt_header(dds_format, info.width, info.height, len(data), info.mips)
        stream.write(DDS_MAGIC)
        stream.write(header)
        stream.write(data)
        return

    if info.img in _TGA_FORMATS:
        header = build_dow_tga_color_header(info.width, info.height)
        stream.write(header)
        stream.write(data)
        return

    if format is None:
        raise NotImplementedError(info.img)


class ImagConverter:
    @classmethod
    def __fix_dds(cls, input_stream: BinaryIO, output_stream: BinaryIO):
        # HARDCODED, assumes src is working directory
        # TODO use paths
        DIREXTEXCONV_PATH = "dll/texconv.exe"
        try:
            with NamedTemporaryFile("wb", delete=False) as in_file:
                in_file.write(input_stream.read())
                in_file.close()
            subprocess.run([DIREXTEXCONV_PATH, "-vflip", "-y", "-o", dirname(in_file.name), in_file.name])
            # subprocess.call([, in_file.name, out_file_name])

            with open(in_file.name, "rb") as out_file:
                output_stream.write(out_file.read())
        finally:
            try:
                os.remove(in_file.name)
            except:
                pass

    @classmethod
    def __needs_fix(cls, imag: ImagChunk) -> bool:
        return imag.attr.img in _DDS_FORMATS

    @classmethod
    def __convert(cls, input_stream: BinaryIO, output_stream: BinaryIO, fmt: str,
                  perform_dds_fix: bool = False):  # An option to fix the dds inversion to avoid redoing a temp file
        # HARDCODED, assumes src is working directory
        # TODO use paths
        DIREXTEXCONV_PATH = "dll/texconv.exe"
        try:
            with NamedTemporaryFile("wb", delete=False) as in_file:
                in_file.write(input_stream.read())
                in_file.close()

            args = [DIREXTEXCONV_PATH, "-vflip" if perform_dds_fix else None, in_file.name, "-ft", fmt, "-y", "-o",
                    dirname(in_file.name), in_file.name]
            # filter out vflip
            args = [arg for arg in args if arg is not None]
            subprocess.run(args)
            with open(in_file.name, "rb") as out_file:
                output_stream.write(out_file.read())
        finally:
            try:
                os.remove(in_file.name)
            except:
                pass

    # Less of a conversion
    # writes the imag as an image to the stream, raw will not perform a DDS fix (or any other fixes)
    @classmethod
    def Imag2Stream(cls, imag: ImagChunk, stream: BinaryIO, format: str = None, raw: bool = False):
        if raw:  # Regardless of type, don't perform any fixes
            create_image(stream, imag)
        elif format:
            with BytesIO() as temp:
                create_image(temp, imag)
                # We have to check needs fixing otherwise non-dds images will be dds_fixed
                perform_dds_fix = not raw and cls.__needs_fix(imag)
                cls.__convert(temp, stream, format, perform_dds_fix)
        else:
            if cls.__needs_fix(imag):
                with BytesIO() as temp:
                    create_image(temp, imag)
                    cls.__fix_dds(temp, stream)
            else:  # TGA, no fixes
                create_image(stream, imag)
