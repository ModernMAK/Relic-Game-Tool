import json
from dataclasses import asdict
from enum import Enum, auto
from os import makedirs
from os.path import splitext, dirname, join
from typing import BinaryIO, Optional

from relic.chunk_formats.fda.converter import FdaConverter
from relic.chunk_formats.fda.fda_chunky import FdaChunky
from relic.chunk_formats.rsh.rsh_chunky import RshChunky
from relic.chunk_formats.shared.imag.writer import ImagConverter, get_imag_chunk_extension, create_image
from relic.chunk_formats.whm.whm_chunky import WhmChunky
from relic.chunk_formats.whm.errors import UnimplementedMslcBlockFormat
from relic.chunk_formats.whm.writer import write_mtllib_to_obj, write_msgr_to_obj, write_msgr_to_mtl
from relic.chunk_formats.wtp.dumper import WTP_LAYER_NAMES
from relic.chunk_formats.wtp.writer import create_mask_image
from relic.chunk_formats.wtp.wtp_chunky import WtpChunky
from relic.chunky import RelicChunky, DataChunk
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky
from relic.chunky.magic import RELIC_CHUNKY_MAGIC
from relic.sga.file import File


class ChunkyFormat(Enum):
    Unsupported = auto()
    FDA = auto()
    RSH = auto()
    WHM = auto()
    WTP = auto()

    # Audio = FDA

    @classmethod
    def from_class(cls, instance: AbstractRelicChunky) -> 'ChunkyFormat':
        if isinstance(instance, FdaChunky):
            return ChunkyFormat.FDA
        if isinstance(instance, WtpChunky):
            return ChunkyFormat.WTP
        if isinstance(instance, RshChunky):
            return ChunkyFormat.RSH
        if isinstance(instance, WhmChunky):
            return ChunkyFormat.WHM
        return ChunkyFormat.Unsupported

    @classmethod
    def from_extension(cls, extension: str) -> 'ChunkyFormat':
        extension = extension.lstrip(".").lower()

        lookup = {
            'fda': ChunkyFormat.FDA,
            'rsh': ChunkyFormat.RSH,
            'whm': ChunkyFormat.WHM,
            'wtp': ChunkyFormat.WTP,
        }
        return lookup.get(extension, ChunkyFormat.Unsupported)

    @classmethod
    def from_path(cls, path: str) -> 'ChunkyFormat':
        _, x = splitext(path)
        return cls.from_extension(x)


def unpack_file(path: str) -> AbstractRelicChunky:
    format = ChunkyFormat.from_path(path)
    with open(path, "rb") as handle:
        unpack_stream(handle, format)


def unpack_archive_file(file: File, check_magic: bool = True) -> Optional[AbstractRelicChunky]:
    """Returns the unpacked relic chunky; if check_magic is True; none is returned for Non-Chunkies"""
    format = ChunkyFormat.from_path(file.name)
    with file.open_readonly_stream() as handle:
        if check_magic and not RELIC_CHUNKY_MAGIC.check_magic_word(handle):
            return None
        return unpack_stream(handle, format)


def unpack_stream(stream: BinaryIO, chunk_format: ChunkyFormat) -> AbstractRelicChunky:
    chunky = RelicChunky.unpack(stream)
    return create(chunky, chunk_format)


def create(chunky: RelicChunky, chunk_format: ChunkyFormat) -> AbstractRelicChunky:
    if chunk_format == ChunkyFormat.FDA:
        return FdaChunky.create(chunky)
    elif chunk_format == ChunkyFormat.RSH:
        return RshChunky.create(chunky)
    elif chunk_format == ChunkyFormat.WHM:
        try:
            return WhmChunky.create(chunky)
        except UnimplementedMslcBlockFormat as e:
            return chunky
    elif chunk_format == ChunkyFormat.WTP:
        return WtpChunky.create(chunky)
    elif chunk_format == ChunkyFormat.Unsupported:
        return chunky


def __create_dirs(output_path: str, use_dirname: bool = True):
    output_path = dirname(output_path) if use_dirname else output_path
    try:
        makedirs(output_path)
    except FileExistsError:
        pass


def __file_replace_name(output_path: str, ext: str, replace_ext: bool = False) -> str:
    no_ext, _ = splitext(output_path)
    return no_ext + ext if replace_ext else output_path


def __dir_replace_name(output_path: str, replace_ext: bool = False) -> str:
    no_ext, _ = splitext(output_path)
    return no_ext if replace_ext else output_path


def dump_fda(fda: FdaChunky, output_path: str, replace_ext: bool = True, use_wave: bool = True, **kwargs):
    # KWARGS is neccessary to catch unexpected keyword args
    output_path = __file_replace_name(output_path, ".wav" if use_wave else ".aiffc", replace_ext)
    with open(output_path, "wb") as handle:
        if use_wave:
            FdaConverter.Fda2Wav(fda, handle)
        else:
            FdaConverter.Fda2Aiffr(fda, handle)


def dump_rsh(rsh: RshChunky, output_path: str, replace_ext: bool = True, format: str = "png", **kwargs):
    output_path = __file_replace_name(output_path, f".{format}", replace_ext)
    # Theres more to dump here, but for now, we only dump the Image
    with open(output_path, "wb") as handle:
        ImagConverter.Imag2Stream(rsh.shrf.texture.imag, handle, format)


def dump_whm(whm: WhmChunky, output_path: str, replace_ext: bool = True, texture_root: str = None,
             texture_ext: str = None, **kwargs):
    output_path = __dir_replace_name(output_path, replace_ext)
    obj_path = output_path + f".obj"
    mtl_path = output_path + f".mtl"
    with open(obj_path, "w") as obj_handle:
        write_mtllib_to_obj(obj_handle, mtl_path)
        write_msgr_to_obj(obj_handle, whm.msgr)
    with open(mtl_path, "w") as mtl_handle:
        write_msgr_to_mtl(mtl_handle, whm.msgr, texture_root, texture_ext)


def dump_chunky(chunky: RelicChunky, output_path: str, replace_ext: bool = True, include_meta: bool = False, **kwargs):
    output_path = __file_replace_name(output_path, "", replace_ext)
    for sub_root, _, files in chunky.walk_chunks():
        full_root = join(output_path, sub_root)
        __create_dirs(full_root)

        for file in files:
            file: DataChunk
            full_path = join(full_root, file.header.name)
            with open(full_path + ".bin", "wb") as handle:
                handle.write(file.data)
            if include_meta:
                with open(full_path + ".meta", "w") as handle:
                    d = asdict(file.header)
                    json_text = json.dumps(d, indent=4)
                    handle.write(json_text)


def dump_wtp(chunky: WtpChunky, output_path: str, replace_ext: bool = True, **kwargs):
    imag = chunky.tpat.imag
    ext = get_imag_chunk_extension(imag.attr.img)
    output_path = __dir_replace_name(output_path, replace_ext)
    __create_dirs(output_path, use_dirname=False)

    with open(join(output_path, "Diffuse" + ext), "wb") as writer:
        create_image(writer, imag)
    for p in chunky.tpat.ptld:
        with open(join(output_path, f"Layer-{WTP_LAYER_NAMES.get(p.layer)}.tga"), "wb") as writer:
            create_mask_image(writer, p, chunky.tpat.info)


def dump(chunky: AbstractRelicChunky, output_path: str, replace_ext: bool = True, **kwargs):
    """Output path may be used as a directory if multiple files are dumped from a single Chunky.
    If a single file is dumped, replace_ext will set the ext to the expected dump extension.
    If multiple files are dumped, replace_ext will trim the extension from output_path.

    It is expected that output_path already exists, subdirectories will be created as needed
    """

    if isinstance(chunky, FdaChunky):
        dump_fda(chunky, output_path, replace_ext, **kwargs)
    elif isinstance(chunky, RshChunky):
        dump_rsh(chunky, output_path, replace_ext, **kwargs)
    elif isinstance(chunky, WhmChunky):
        dump_whm(chunky, output_path, replace_ext, **kwargs)
    elif isinstance(chunky, WtpChunky):
        dump_wtp(chunky,output_path,replace_ext)
    elif isinstance(chunky, RelicChunky):
        dump_chunky(chunky, output_path, replace_ext, **kwargs)
    else:
        raise NotImplementedError(chunky)
