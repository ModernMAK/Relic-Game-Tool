from dataclasses import dataclass

from relic.chunk_formats.fda.data_chunk import FdaDataChunk
from relic.chunk_formats.fda.info_chunk import FdaInfoChunk
from relic.chunky import RelicChunky, FolderChunk
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


@dataclass
class FdaChunky(AbstractRelicChunky):
    info_block: FdaInfoChunk
    data_block: FdaDataChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'FdaChunky':
        header = chunky.header
        # We ignore burn info ~ FBIF
        fda: FolderChunk = chunky.get_chunk(id="FDA ")

        # We fetch 'FDA ' and get the Info/Data block from FDA
        info = fda.get_chunk(id="INFO", recursive=False)
        data = fda.get_chunk(id="DATA", recursive=False)

        # parse the blocks
        fda_info = FdaInfoChunk.convert(info)
        fda_data = FdaDataChunk.convert(data)

        return FdaChunky(chunky.chunks, header, fda_info, fda_data)
