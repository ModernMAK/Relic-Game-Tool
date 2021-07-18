import math
from io import BytesIO
from typing import BinaryIO

from relic.chunk_formats.fda.fda import FdaDataChunk
from relic.chunk_formats.fda.fda_chunky import FdaChunky
from relic.chunk_formats.fda.info_chunk import FdaInfoChunk
from relic.chunky import RelicChunkyHeader
from relic.file_formats import aiff


class Converter:
    COMP = "COMP"
    COMP_desc = "Relic Codec v1.6"

    @classmethod
    def Fda2Aiffr(cls, chunky: FdaChunky, stream: BinaryIO) -> int:
        with BytesIO() as temp:
            aiff.write_default_FVER(temp)
            info = chunky.info_block
            frames = len(chunky.data_block.data) / math.ceil(info.block_bitrate / 8)
            assert frames == int(frames)
            frames = int(frames)

            aiff.write_COMM(temp, info.channels, frames, info.sample_size, info.sample_rate, cls.COMP, cls.COMP_desc,
                            use_fixed=True)
            aiff.write_SSND(temp, chunky.data_block.data, info.block_bitrate)
            with BytesIO() as marker:
                aiff.write_default_markers(marker)
                marker.seek(0, 0)
                buffer = marker.read()
                aiff.write_MARK(temp, 3, buffer)

            temp.seek(0, 0)
            buffer = temp.read()
            return aiff.write_FORM(stream, buffer)

    @classmethod
    def Aiffr2Fda(cls, stream: BinaryIO) -> FdaChunky:
        buffer = aiff.read_FORM(stream)
        info = FdaInfoChunk(None, None, None, None, 0, 0xffffffff, 0)
        data = None
        with BytesIO(buffer) as form:
            while form.tell() != len(buffer):
                block_type = form.read(4).decode("ascii")
                form.seek(-4, 1)

                if block_type == aiff.FVER:
                    _ = aiff.read_FVER(form)
                elif block_type == aiff.COMM:
                    info.channels, _, info.sample_size, info.sample_rate, _, _ = aiff.read_COMM(form)
                elif block_type == aiff.SSND:
                    data, info.block_bitrate = aiff.read_SSND(form)

        return FdaChunky(RelicChunkyHeader.default(), info, FdaDataChunk(len(data), data))