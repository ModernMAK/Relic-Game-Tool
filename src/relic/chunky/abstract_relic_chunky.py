from dataclasses import dataclass

from relic.chunky.chunk_collection import ChunkCollection
from relic.chunky.relic_chunky_header import RelicChunkyHeader


# Added to allow specialized chunkies to preserve the header without re-declaring it
@dataclass
class AbstractRelicChunky(ChunkCollection):
    header: RelicChunkyHeader
