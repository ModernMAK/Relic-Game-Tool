from dataclasses import dataclass

from relic.chunk_formats.Dow.fda.data_chunk import FdaDataChunk
from relic.chunk_formats.Dow.fda.info_chunk import FdaInfoChunk
from relic.chunk_formats.Dow.shared.fbif_chunk import FbifChunk
from relic.chunky import RelicChunky, FolderChunk
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


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
