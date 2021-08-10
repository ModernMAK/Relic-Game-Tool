from dataclasses import dataclass
from typing import BinaryIO

from relic.chunk_formats.Dow.wtp.tpat_chunk import TpatChunk
from relic.chunky import RelicChunky, FolderChunk
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


@dataclass
class WtpChunky(AbstractRelicChunky):
    tpat: TpatChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'WtpChunky':
        tpat_folder: FolderChunk = chunky.get_chunk(id="TPAT")
        tpat = TpatChunk.convert(tpat_folder)
        return WtpChunky(chunky.chunks, chunky.header, tpat)

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'WtpChunky':
        chunky = RelicChunky.unpack(stream, read_magic)
        return cls.convert(chunky)
