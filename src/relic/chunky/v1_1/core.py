from typing import Type

from relic.chunky import _abc

_ChunkyMetadata = Type[None]  # v1_1 has no meta, this should hopefully remind me

RawChunky = _abc.RawChunky[None]
Chunky = _abc.Chunky[None]
