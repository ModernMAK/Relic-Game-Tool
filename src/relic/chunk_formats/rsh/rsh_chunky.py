from dataclasses import dataclass

from relic.chunk_formats.rsh.shrf_chunk import ShrfChunk
from relic.chunky import RelicChunky


@dataclass
class RshChunky:
    shrf: ShrfChunk

    @classmethod
    def create(cls, chunky: RelicChunky) -> 'RshChunky':
        shrf_folder = chunky.get_chunk(id="SHRF", recursive=True)
        shrf = ShrfChunk.create(shrf_folder)
        return RshChunky(shrf)