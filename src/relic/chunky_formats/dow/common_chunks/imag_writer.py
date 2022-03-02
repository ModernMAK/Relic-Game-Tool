import os
import shutil
import subprocess
from io import BytesIO
from os.path import dirname, splitext, exists
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Optional

from .imag import ImagChunk
from ....file_formats.dxt import get_full_dxt_header, build_dow_tga_color_header, DDS_MAGIC, build_dow_tga_gray_header

TEX_CONV = "texconv.exe"
DEFAULT_LOCAL_TEX_CONV = os.path.abspath(fr".\{TEX_CONV}")
DEFAULT_PATH_TEX_CONV = TEX_CONV


def find_texconv() -> Optional[str]:
    if shutil.which(DEFAULT_PATH_TEX_CONV):
        return DEFAULT_PATH_TEX_CONV
    if exists(DEFAULT_LOCAL_TEX_CONV):
        return DEFAULT_LOCAL_TEX_CONV
    return None


class ImagConverter:
    TEXCONV_PATH: str = find_texconv()

    @classmethod
    def fix_dow_dds(cls, input_stream: BinaryIO, output_stream: BinaryIO, *, texconv_path: str = None):
        """
        Vertically flips the dds image contained in input_stream and writes the result

        :param input_stream: The dds file stream to read from
        :param output_stream: The dds file stream to write to
        :param texconv_path: If supplied, will use this path to call texconv instead of the class path.
        """
        texconv_path = texconv_path or cls.TEXCONV_PATH
        if not texconv_path:
            raise FileNotFoundError("No texconv.exe could be found; try specifying texconv_path.")
        elif not exists(texconv_path):
            raise FileNotFoundError(texconv_path)
        try:
            with NamedTemporaryFile("wb", delete=False) as in_file:
                in_file.write(input_stream.read())
                in_file.close()

            subprocess.run([texconv_path, "-vflip", "-y", "-o", dirname(in_file.name), in_file.name], stdout=subprocess.DEVNULL)
            # subprocess.call([, in_file.name, out_file_name])

            with open(in_file.name, "rb") as out_file:
                output_stream.write(out_file.read())
        finally:
            try:
                os.remove(in_file.name)
            except FileNotFoundError:
                pass

    @classmethod
    def ConvertStream(cls, input_stream: BinaryIO, output_stream: BinaryIO, out_format: str, input_ext: str = None, perform_dds_fix: bool = False, *, texconv_path: str = None):  # An option to fix the dds inversion to avoid redoing a temp file
        def get_texconv_fmt_ext() -> str:
            lookup = {
                'png': ".PNG",
            }
            return lookup[out_format.lower()]

        input_ext = input_ext or "." + out_format

        try:
            texconv_path = texconv_path or cls.TEXCONV_PATH

            with NamedTemporaryFile("wb", suffix=input_ext, delete=False) as in_file:
                in_file.write(input_stream.read())
                in_file.close()

            # perform_dds_fix = False #TODO temp
            args = [texconv_path, "-vflip" if perform_dds_fix else None, "-ft", out_format, "-y", "-o", dirname(in_file.name), in_file.name]
            # filter out vflip
            args = [arg for arg in args if arg is not None]
            subprocess.run(args, stdout=subprocess.DEVNULL)
            b, _ = splitext(in_file.name)
            out_name = b + get_texconv_fmt_ext()
            with open(out_name, "rb") as out_file:
                output_stream.write(out_file.read())
        finally:
            try:
                os.remove(in_file.name)
            except (FileNotFoundError, UnboundLocalError):
                pass
            try:
                os.remove(out_name)
            except (FileNotFoundError, UnboundLocalError):
                pass

    @classmethod
    def Imag2StreamRaw(cls, imag: ImagChunk, stream: BinaryIO, color_tga: bool = True):
        info = imag.attr
        data = imag.data.raw_bytes
        if info.image_format.is_dxt:
            header = get_full_dxt_header(info.image_format.fourCC, info.width, info.height, len(data), info.mips)
            stream.write(DDS_MAGIC)
            stream.write(header)
            stream.write(data)
        elif info.image_format.is_tga:
            if color_tga:
                header = build_dow_tga_color_header(info.width, info.height)
            else:
                header = build_dow_tga_gray_header(info.width, info.height)
            stream.write(header)
            stream.write(data)
        else:
            raise NotImplementedError(info.image_format, info.image_format.is_dxt)

    # Less of a conversion
    # writes the imag as an image to the stream, raw will not perform a DDS fix (or any other fixes)
    @classmethod
    def Imag2Stream(cls, imag: ImagChunk, stream: BinaryIO, out_format: str = None, raw: bool = False, *, texconv_path: str = None, color_tga: bool = True):
        if raw:  # Regardless of type, don't perform any fixes
            cls.Imag2StreamRaw(imag, stream, color_tga=color_tga)
        elif out_format:
            with BytesIO() as temp:
                cls.Imag2StreamRaw(imag, temp, color_tga=color_tga)
                # We have to check needs fixing otherwise non-dds images will be dds_fixed
                perform_dds_fix = not raw and imag.attr.image_format.is_dxt
                temp.seek(0, 0)
                cls.ConvertStream(temp, stream, out_format, imag.attr.image_format.extension, perform_dds_fix, texconv_path=texconv_path)
        else:
            if imag.attr.image_format.is_dxt:
                with BytesIO() as temp:
                    cls.Imag2StreamRaw(imag, temp, color_tga=color_tga)
                    temp.seek(0, 0)
                    cls.fix_dow_dds(temp, stream, texconv_path=texconv_path)
            else:  # TGA, no fixes
                cls.Imag2StreamRaw(imag, stream, color_tga=color_tga)
