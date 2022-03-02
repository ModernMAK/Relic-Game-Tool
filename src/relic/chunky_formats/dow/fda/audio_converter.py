import math
import os
import subprocess
from io import BytesIO
from os.path import exists, dirname
from tempfile import NamedTemporaryFile
from typing import BinaryIO

from .chunky import FdaChunky, FdaChunk, FdaDataChunk, FdaInfoChunk
from ..common_chunks.fbif import FbifChunk
from ....file_formats.aiff import Aiff, Marker, Comm, Ssnd

__ROOT_PATH = dirname(__file__)
DECODER_PATH = __ROOT_PATH + "/conv/dec.exe"
ENCODER_PATH = __ROOT_PATH + "/conv/enc.exe"


class FdaAudioConverter:

    # FDA <---> AIFF-C (Relic)
    @classmethod
    def Fda2Aiffr(cls, chunky: FdaChunky, stream: BinaryIO) -> int:
        info = chunky.fda.info
        frames = len(chunky.fda.data.data) / math.ceil(info.block_bitrate / 8)
        assert frames == int(frames)
        frames = int(frames)
        assert info.sample_rate == 22050, info.sample_rate  # TODO
        comm = Comm.relic_default(info.channels, frames, info.sample_size)
        ssnd = Ssnd(chunky.fda.data.data, info.block_bitrate)
        aiff = Aiff.default(comm, ssnd)
        return aiff.write(stream)

    @classmethod
    def Aiffr2Fda(cls, stream: BinaryIO) -> FdaChunky:
        aiff = Aiff.read(stream)
        ssnd = aiff.ssnd
        comm = aiff.comm
        mark = aiff.mark

        begin_loop, end_loop, start_offset = None, None, None
        for m in mark.markers:
            if m.name == Marker.DEFAULT_BEGIN_LOOP[2]:
                begin_loop = m.position
            elif m.name == Marker.DEFAULT_END_LOOP[2]:
                end_loop = m.position
            elif m.name == Marker.DEFAULT_START_OFFSET[2]:
                start_offset = m.position

        fda_info_chunk = FdaInfoChunk(None, comm.channels, comm.sample_size, ssnd.block_bitrate, comm.sample_rate, begin_loop, end_loop, start_offset)
        fda_data_chunk = FdaDataChunk(None, ssnd.data)
        fda_chunk = FdaChunk(None, fda_info_chunk, fda_data_chunk)
        fbif = FbifChunk.default()
        return FdaChunky(None, fbif, fda_chunk)

    # WAV <---> AIFF-C (Relic)
    # Assuming I do figure out the Relic Compression Algorithm from the .EXE, I won't need the binaries anymore
    @classmethod
    def Aiffr2Wav(cls, aiffr: BinaryIO, wav: BinaryIO) -> int:
        if not exists(DECODER_PATH):
            raise FileNotFoundError(DECODER_PATH)
        try:
            with NamedTemporaryFile("wb", delete=False) as aiffr_file:
                aiffr_file.write(aiffr.read())
                aiffr_file.close()
                wav_file_name = aiffr_file.name + ".wav"
            subprocess.call([DECODER_PATH, aiffr_file.name, wav_file_name], stdout=subprocess.DEVNULL)  # TODO see if i can wrap stdout into a seperate stream, then raise an error if it prints ERROR
            with open(wav_file_name, "rb") as wav_file:
                buffer = wav_file.read()
                return wav.write(buffer)
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
    def Wav2Aiffr(cls, wav: BinaryIO, aiffr: BinaryIO) -> int:
        if not exists(DECODER_PATH):
            raise FileNotFoundError(ENCODER_PATH)
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
    def Fda2Wav(cls, chunky: FdaChunky, wav: BinaryIO) -> int:
        with BytesIO() as aiffr:
            cls.Fda2Aiffr(chunky, aiffr)
            aiffr.seek(0)
            return cls.Aiffr2Wav(aiffr, wav)

    @classmethod
    def Wav2Fda(cls, wav: BinaryIO) -> FdaChunky:
        with BytesIO() as aiffr:
            cls.Wav2Aiffr(wav, aiffr)
            aiffr.seek(0)
            return cls.Aiffr2Fda(aiffr)
