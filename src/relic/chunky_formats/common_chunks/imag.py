from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from os.path import dirname, splitext
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Optional, List

from archive_tools.structx import Struct

from ..convertable import find_chunk, find_chunks
from ...chunky.chunk.chunk import GenericDataChunk, FolderChunk, AbstractChunk
from ...chunky.chunk.header import ChunkType
from ...config import texconv_path
from ...file_formats.dxt import get_full_dxt_header, build_dow_tga_color_header, DDS_MAGIC


class ImageFormat(Enum):
    TGA = 0

    DXT1 = 8
    DXT3 = 10
    DXT5 = 11

    @property
    def extension(self) -> str:
        _extensions = {
            ImageFormat.TGA: ".tga",
            ImageFormat.DXT1: ".dds",
            ImageFormat.DXT3: ".dds",
            ImageFormat.DXT5: ".dds"
        }
        return _extensions[self.value]

    @property
    def fourCC(self) -> str:
        _fourCC = {
            ImageFormat.DXT1: "DXT1",
            ImageFormat.DXT3: "DXT3",
            ImageFormat.DXT5: "DXT5"
        }
        return _fourCC[self.value]

    @property
    def is_dxt(self) -> bool:
        _dds = [ImageFormat.DXT1, ImageFormat.DXT3, ImageFormat.DXT5]
        return self.value in _dds

    @property
    def is_tga(self) -> bool:
        _tga = [ImageFormat.TGA]
        return self.value in _tga


@dataclass
class AttrChunk(AbstractChunk):
    LAYOUT = Struct("< 3l")
    LAYOUT_WITH_MIP = Struct("< 4l")

    img: ImageFormat
    width: int
    height: int
    mips: int

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> 'AttrChunk':
        buffer_size = len(chunk.data)
        if buffer_size == cls.LAYOUT_WITH_MIP.size:
            args = cls.LAYOUT_WITH_MIP.unpack(chunk.data)
        elif buffer_size == cls.LAYOUT.size:
            args = cls.LAYOUT.unpack(chunk.data)
            args = (*args, 0)
        else:
            raise NotImplementedError

        img = ImageFormat(args[0])
        args = args[1:]
        return AttrChunk(chunk.header, img, *args)


# TxtrChunk = ForwardRef("TxtrChunk")

@dataclass
class ImagChunk(AbstractChunk):
    attr: AttrChunk
    data: GenericDataChunk
    txtr: Optional[TxtrChunk]
    shdr: Optional[FolderChunk]  # TODO
    sshr: List[FolderChunk]  # TODO

    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'ImagChunk':
        attr = find_chunk(chunk.chunks, "ATTR", ChunkType.Data)
        attr = AttrChunk.convert(attr)
        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        txtr = find_chunk(chunk.chunks, "TXTR", ChunkType.Folder)
        if txtr:
            txtr = TxtrChunk.convert(txtr)
        shdr = find_chunk(chunk.chunks, "SHDR", ChunkType.Folder)

        sshr = find_chunks(chunk.chunks, "SSHR", ChunkType.Data)
        sshr = list(sshr)
        assert len(chunk.chunks) == 2 + (1 if shdr else 0) + (1 if txtr else 0) + len(sshr)
        return ImagChunk(chunk.header, attr, data, txtr, shdr, sshr)


# Dumps the raw image, DDS images will be inverted, TGA images will be normal


class ImagConverter:
    @classmethod
    def __fix_dds(cls, input_stream: BinaryIO, output_stream: BinaryIO):
        try:
            with NamedTemporaryFile("wb", delete=False) as in_file:
                in_file.write(input_stream.read())
                in_file.close()

            subprocess.run([texconv_path, "-vflip", "-y", "-o", dirname(in_file.name), in_file.name],
                           stdout=subprocess.DEVNULL)
            # subprocess.call([, in_file.name, out_file_name])

            with open(in_file.name, "rb") as out_file:
                output_stream.write(out_file.read())
        finally:
            try:
                os.remove(in_file.name)
            except FileNotFoundError:
                pass

    @classmethod
    def __convert(cls, input_stream: BinaryIO, output_stream: BinaryIO, fmt: str, input_ext: str, perform_dds_fix: bool = False):  # An option to fix the dds inversion to avoid redoing a temp file
        def get_texconv_fmt_ext() -> str:
            lookup = {
                'png': ".PNG",
            }
            return lookup[fmt.lower()]

        out_name = None
        try:
            with NamedTemporaryFile("wb", suffix=input_ext, delete=False) as in_file:
                in_file.write(input_stream.read())
                in_file.close()

            # perform_dds_fix = False #TODO temp
            args = [texconv_path, "-vflip" if perform_dds_fix else None, "-ft", fmt, "-y", "-o",
                    dirname(in_file.name), in_file.name]
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
            except FileNotFoundError:
                pass
            try:
                os.remove(out_name)
            except FileNotFoundError:
                pass

    @classmethod
    def Imag2StreamRaw(cls, imag: ImagChunk, stream: BinaryIO):
        info = imag.attr
        data = imag.data.data
        if info.img.is_dxt:
            header = get_full_dxt_header(info.img.fourCC, info.width, info.height, len(data), info.mips)
            stream.write(DDS_MAGIC)
            stream.write(header)
            stream.write(data)
        elif info.img.is_tga:
            header = build_dow_tga_color_header(info.width, info.height)
            stream.write(header)
            stream.write(data)
        else:
            raise NotImplementedError(info.img)

    # Less of a conversion
    # writes the imag as an image to the stream, raw will not perform a DDS fix (or any other fixes)
    @classmethod
    def Imag2Stream(cls, imag: ImagChunk, stream: BinaryIO, out_format: str = None, raw: bool = False):
        if raw:  # Regardless of type, don't perform any fixes
            cls.Imag2StreamRaw(imag, stream)
        elif out_format:
            with BytesIO() as temp:
                cls.Imag2StreamRaw(imag, temp)
                # We have to check needs fixing otherwise non-dds images will be dds_fixed
                perform_dds_fix = not raw and imag.attr.img.is_dxt
                temp.seek(0, 0)
                cls.__convert(temp, stream, out_format, imag.attr.img.extension, perform_dds_fix)
        else:
            if imag.attr.img.is_dxt:
                with BytesIO() as temp:
                    cls.Imag2StreamRaw(imag, temp)
                    temp.seek(0, 0)
                    cls.__fix_dds(temp, stream)
            else:  # TGA, no fixes
                cls.Imag2StreamRaw(imag, stream)


@dataclass
class HeadChunk:
    LAYOUT = Struct("< 2l")
    image_format: int
    unk_a: int

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> HeadChunk:
        args = cls.LAYOUT.unpack(chunk.data)
        return HeadChunk(*args)


@dataclass
class TxtrChunk:
    head: HeadChunk
    imag: ImagChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> TxtrChunk:
        assert chunk.header.version == 1
        head = find_chunk(chunk.chunks, "HEAD", ChunkType.Data)
        head = HeadChunk.convert(head)
        imag = find_chunk(chunk.chunks, "IMAG", ChunkType.Folder)
        imag = ImagChunk.convert(imag)
        return TxtrChunk(head, imag)
