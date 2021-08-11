from dataclasses import dataclass
from typing import List

from relic.chunky import DataChunk


@dataclass
class NodeChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)

@dataclass
class SharedMgrpChunk:
    nodes: List[NodeChunk]
