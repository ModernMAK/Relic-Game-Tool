from dataclasses import dataclass

from relic.chunk_formats.shared.txtr.head_chunk import HeadChunk
from relic.chunk_formats.shared.imag.imag_chunk import ImagChunk
from relic.chunky import FolderChunk


@dataclass
class TxtrChunk:
    head: HeadChunk
    imag: ImagChunk

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'TxtrChunk':
        head_chunk = chunk.get_chunk(id="HEAD")
        imag_chunk = chunk.get_chunk(id="IMAG")

        head = HeadChunk.create(head_chunk)
        imag = ImagChunk.create(imag_chunk)

        return TxtrChunk(head, imag)
