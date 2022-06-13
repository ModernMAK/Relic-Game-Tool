from dataclasses import dataclass
from typing import ClassVar

from relic.chunky import _abc


@dataclass
class ChunkyMetadata:
    rsv_a_thirty_six: int
    rsv_b_twenty_eight: int
    rsv_c_one: int
    RESERVED: ClassVar = (36, 28, 1)  # what they mean; idk, but its technically meta data, so I define a class


RawChunky = _abc.RawChunky[ChunkyMetadata]
Chunky = _abc.Chunky[ChunkyMetadata]
