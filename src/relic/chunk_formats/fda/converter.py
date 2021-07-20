import math
import os
import subprocess
from io import BytesIO
from tempfile import TemporaryFile, NamedTemporaryFile
from typing import BinaryIO

from relic.chunk_formats.fda.data_chunk import FdaDataChunk
from relic.chunk_formats.fda.fda_chunky import FdaChunky
from relic.chunk_formats.fda.info_chunk import FdaInfoChunk
from relic.chunky import RelicChunkyHeader
from relic.file_formats import aiff


class FdaConverter:
    COMP = "COMP"
    COMP_desc = "Relic Codec v1.6"

    # FDA <---> AIFF-C (Relic)
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


    # WAV <---> AIFF-C (Relic)
    # Assuming I do figure out the Relic Compression Algorithm from the .EXE, I wont need the binaries anymore
    @classmethod
    def Aiffr2Wav(cls, aiffr:BinaryIO, wav:BinaryIO) -> int:
        # HARDCODED, assumes src is working directory
        # TODO use paths
        DECODER_PATH = "dll/dec.exe"
        try:
            with NamedTemporaryFile("wb", delete=False) as aiffr_file:
                aiffr_file.write(aiffr.read())
                aiffr_file.close()
                wav_file_name = aiffr_file.name +".wav"
            subprocess.call([DECODER_PATH, aiffr_file.name, wav_file_name])

            with open(wav_file_name,"rb") as wav_file:
                return wav.write(wav_file.read())
        finally:
            try:
                os.remove(aiffr_file.name)
            except:
                pass
            try:
                os.remove(wav_file_name)
            except:
                pass

    @classmethod
    def Wav2Aiffr(cls, wav:BinaryIO, aiffr:BinaryIO) -> int:
        # HARDCODED, assumes src is working directory
        # TODO use paths
        ENCODER_PATH = "dll/enc.exe"
        try:
            with NamedTemporaryFile("wb", delete=False) as wav_file:
                wav_file.write(wav.read())
                wav_file.close()
                aiffr_file_name = wav_file.name + ".aiffr"
            subprocess.call([ENCODER_PATH, wav_file.name, aiffr_file_name])

            with open(aiffr_file_name, "rb") as aiffr_file:
                return aiffr.write(aiffr_file.read())
        finally:
            try:
                os.remove(wav_file.name)
            except:
                pass
            try:
                os.remove(aiffr_file_name)
            except:
                pass

    # FDA <---> WAV
    @classmethod
    def Fda2Wav(cls, chunky:FdaChunky, stream:BinaryIO) -> int:
        with BytesIO() as aiffr:
            cls.Fda2Aiffr(chunky,aiffr)
            aiffr.seek(0)
            return cls.Aiffr2Wav(aiffr, stream)

    @classmethod
    def Wav2Fda(cls, stream:BinaryIO) -> FdaChunky:
        with BytesIO() as aiffr:
            cls.Wav2Aiffr(stream, aiffr)
            aiffr.seek(0)
            return cls.Aiffr2Fda(aiffr, stream)
