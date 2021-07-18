from dataclasses import dataclass
from relic.chunky import RelicChunkyHeader

# Added to allow specialized chunkies to preserve the header without re-declaring it
@dataclass
class AbstractRelicChunky:
    header: RelicChunkyHeader
