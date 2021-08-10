from dataclasses import dataclass
from relic.chunk_formats.Dow.shared.imag.attr_chunk import AttrChunk
from relic.chunky import FolderChunk, DataChunk


@dataclass
class ImagChunk:
    attr: AttrChunk
    data: DataChunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'ImagChunk':
        attr_chunk = chunk.get_chunk(id="ATTR")
        data_chunk = chunk.get_chunk(id="DATA")

        attr = AttrChunk.create(attr_chunk)
        data = data_chunk

        return ImagChunk(attr, data)
