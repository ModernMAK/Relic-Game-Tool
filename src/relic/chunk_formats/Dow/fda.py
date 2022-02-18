import math
import os
import subprocess
from dataclasses import dataclass
from io import BytesIO
from tempfile import NamedTemporaryFile
from typing import BinaryIO

from archive_tools.structx import Struct

from relic.chunk_formats.Dow.shared.fbif_chunk import FbifChunk
from relic.chunky import DataChunk
from relic.chunky import RelicChunky, FolderChunk
from relic.chunky import RelicChunkyHeader
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky
from relic.config import aifc_decoder_path, aifc_encoder_path
from relic.file_formats import aiff


@dataclass
class FdaInfoChunk:
    LAYOUT = Struct("< 7L")

    channels: int
    sample_size: int
    block_bitrate: int
    sample_rate: int
    begin_loop: int
    end_loop: int
    start_offset: int

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'FdaInfoChunk':
        args = cls.LAYOUT.unpack(chunk.data)
        return FdaInfoChunk(*args)


@dataclass
class FdaDataChunk:
    LAYOUT = Struct("< L")
    size: int
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'FdaDataChunk':
        size = cls.LAYOUT.unpack(chunk.data[:4])[0]
        data = chunk.data[4:]
        # TODO see if this is a len-encoded situtation
        # assert len(data) == size
        return FdaDataChunk(size, data)


@dataclass
class FdaChunk:
    info: FdaInfoChunk
    data: FdaDataChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'FdaChunk':
        # We fetch 'FDA ' and get the Info/Data block from FDA
        info = chunk.get_chunk(id="INFO", recursive=False)
        data = chunk.get_chunk(id="DATA", recursive=False)

        # parse the blocks
        fda_info = FdaInfoChunk.convert(info)
        fda_data = FdaDataChunk.convert(data)

        return FdaChunk(fda_info, fda_data)  # chunky.chunks, header, fda_info, fda_data)


@dataclass
class FdaChunky(AbstractRelicChunky):
    fbif: FbifChunk
    fda: FdaChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'FdaChunky':
        # We ignore burn info ~ FBIF
        fda_folder: FolderChunk = chunky.get_chunk(id="FDA ", recursive=False)
        fda = FdaChunk.convert(fda_folder)

        fbif_data: FolderChunk = chunky.get_chunk(id="FBIF", recursive=False)
        fbif = FbifChunk.convert(fbif_data)

        return FdaChunky(chunky.chunks, chunky.header, fbif, fda)


class FdaConverter:
    COMP = "COMP"
    COMP_desc = "Relic Codec v1.6"

    # FDA <---> AIFF-C (Relic)
    @classmethod
    def Fda2Aiffr(cls, chunky: FdaChunky, stream: BinaryIO) -> int:
        with BytesIO() as temp:
            aiff.write_default_FVER(temp)
            info = chunky.fda.info
            frames = len(chunky.fda.data.data) / math.ceil(info.block_bitrate / 8)
            assert frames == int(frames)
            frames = int(frames)

            aiff.write_COMM(temp, info.channels, frames, info.sample_size, info.sample_rate, cls.COMP, cls.COMP_desc,
                            use_fixed=True)
            aiff.write_SSND(temp, chunky.fda.data.data, info.block_bitrate)
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
        # noinspection PyTypeChecker
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

        return FdaChunky([], RelicChunkyHeader.default(), None, FdaChunk(info, FdaDataChunk(len(data), data)))

    # WAV <---> AIFF-C (Relic)
    # Assuming I do figure out the Relic Compression Algorithm from the .EXE, I won't need the binaries anymore
    @classmethod
    def Aiffr2Wav(cls, aiffr: BinaryIO, wav: BinaryIO) -> int:
        try:
            with NamedTemporaryFile("wb", delete=False) as aiffr_file:
                aiffr_file.write(aiffr.read())
                aiffr_file.close()
                wav_file_name = aiffr_file.name + ".wav"
            subprocess.call([aifc_decoder_path, aiffr_file.name, wav_file_name], stdout=subprocess.DEVNULL)

            with open(wav_file_name, "rb") as wav_file:
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
    def Wav2Aiffr(cls, wav: BinaryIO, aiffr: BinaryIO) -> int:
        try:
            with NamedTemporaryFile("wb", delete=False) as wav_file:
                wav_file.write(wav.read())
                wav_file.close()
                aiffr_file_name = wav_file.name + ".aiffr"
            subprocess.call([aifc_encoder_path, wav_file.name, aiffr_file_name])

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
    def Fda2Wav(cls, chunky: FdaChunky, stream: BinaryIO) -> int:
        with BytesIO() as aiffr:
            cls.Fda2Aiffr(chunky, aiffr)
            aiffr.seek(0)
            return cls.Aiffr2Wav(aiffr, stream)

    @classmethod
    def Wav2Fda(cls, stream: BinaryIO) -> FdaChunky:
        with BytesIO() as aiffr:
            cls.Wav2Aiffr(stream, aiffr)
            aiffr.seek(0)
            return cls.Aiffr2Fda(aiffr)


__all__ = [
    FdaConverter.__name__,
    FdaDataChunk.__name__,
    FdaChunky.__name__,
    FdaChunk.__name__,
    FdaInfoChunk.__name__,
]