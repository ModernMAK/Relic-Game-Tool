from dataclasses import dataclass

from relic.chunk_formats.Dow.rsh.shrf_chunk import ShrfChunk
from relic.chunky import RelicChunky
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


@dataclass
class RshChunky(AbstractRelicChunky):
    shrf: ShrfChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'RshChunky':
        shrf_folder = chunky.get_chunk(id="SHRF", recursive=True)
        shrf = ShrfChunk.create(shrf_folder)
        return RshChunky(chunky.chunks, chunky.header, shrf)
