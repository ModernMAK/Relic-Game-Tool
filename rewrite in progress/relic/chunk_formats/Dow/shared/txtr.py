from dataclasses import dataclass

from archive_tools.structx import Struct

from relic.chunk_formats.Dow.shared.imag import ImagChunk
from relic.chunky import DataChunk, FolderChunk


@dataclass
class HeadChunk:
    LAYOUT = Struct("< 2l")
    image_format: int
    unk_a: int

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'HeadChunk':
            args = cls.LAYOUT.unpack(chunk.data)
            return HeadChunk(*args)


@dataclass
class TxtrChunk:
    head: HeadChunk
    imag: ImagChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'TxtrChunk':
        head_chunk = chunk.get_chunk(chunk_id="HEAD")
        imag_chunk = chunk.get_chunk(chunk_id="IMAG")

        head = HeadChunk.convert(head_chunk)
        imag = ImagChunk.convert(imag_chunk)

        return TxtrChunk(head, imag)


__all__ = [TxtrChunk.__name__, HeadChunk.__name__]
