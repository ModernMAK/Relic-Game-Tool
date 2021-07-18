from typing import BinaryIO

from relic.chunk_formats.wtp.info_chunk import InfoChunk
from relic.chunk_formats.wtp.ptld_chunk import PtldChunk


def create_mask_image(stream: BinaryIO, chunk: PtldChunk, info: InfoChunk):
    data = chunk.image
    header = build_dow_tga_gray_header(info.width, info.height)
    stream.write(header)
    stream.write(data)

