from dataclasses import dataclass
from typing import BinaryIO

from relic.chunk_formats.wtp.tpat_chunk import TpatChunk
from relic.chunky import RelicChunky, FolderChunk


@dataclass
class WtpChunky:
    tpat: TpatChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'WtpChunky':
        tpat_folder: FolderChunk = chunky.get_chunk(id="TPAT")
        tpat = TpatChunk.create(tpat_folder)
        return WtpChunky(tpat)

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'WtpChunky':
        chunky = RelicChunky.unpack(stream, read_magic)
        return cls.create(chunky)
