import struct
from dataclasses import dataclass
from io import BytesIO

from relic.chunk_formats.Dow.shared.imag.image_format import ImageFormat
from relic.chunky import DataChunk

_MIP = struct.Struct("< l")
_HEADER = struct.Struct("< l l l")


@dataclass
class AttrChunk:
    img: ImageFormat
    width: int
    height: int
    mips: int

    @classmethod
    def create(cls, chunk: DataChunk) -> 'AttrChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(_HEADER.size)
            img, height, width = _HEADER.unpack(buffer)  # width and height are swapped?
            img_fmt = ImageFormat(img)
            if stream.tell() < len(chunk.data):
                buffer = stream.read(_MIP.size)
                mips = _MIP.unpack(buffer)[0]
            else:
                mips = 0

            return AttrChunk(img_fmt, width, height, mips)
