# Painted Team Layer Data?
import struct
from dataclasses import dataclass
from enum import Enum
from io import BytesIO

from relic.chunky import DataChunk


class PtldLayer(Enum):
    Primary = 0
    Secondary = 1
    Trim = 2
    Weapon = 3
    Eyes = 4
    Dirt = 5

    _ignore = ["_pretty_names"]
    _pretty_names = {Primary: "Primary", Secondary: "Secondary", Trim: "Trim", Weapon: "Weapon", Eyes: "Eyes",
                     Dirt: "Dirt"}  # Decouples Names from Enum Name.

    @property
    def pretty_name(self):
        return self._pretty_names[self.value]


@dataclass
class PtldChunk:
    _HEADER = struct.Struct("< l l")
    layer: PtldLayer
    image: bytes

    @classmethod
    def create(cls, chunk: DataChunk) -> 'PtldChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(cls._HEADER.size)
            layer_code, size = cls._HEADER.unpack(buffer)
            layer = PtldLayer(layer_code)
            image = stream.read(size)
            return PtldChunk(layer, image)
