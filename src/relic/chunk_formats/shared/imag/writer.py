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


def get_ext(format: int) -> str:
    if format in _TGA_FORMATS:
        return ".tga"
    elif format in _DDS_FORMATS:
        return ".dds"
    else:
        raise NotImplementedError(format)


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
