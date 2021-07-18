from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO

from relic.shared import unpack_from_stream, pack_into_stream


@dataclass
class Description:
    __DESC_LAYOUT = Struct("< 64s 64s H L L")

    category: str
    name: str
    unk_a1: int
    unk_a2: int
    unk_a3: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Description':
        args = unpack_from_stream(cls.__DESC_LAYOUT, stream)
        category = args[0].decode("ascii").rstrip("\x00")
        name = args[1].decode("ascii").rstrip("\x00")
        unks = args[2:]
        return Description(category, name, *unks)

    def pack(self, stream: BinaryIO) -> int:
        args = (self.category, self.name, self.unk_a1, self.unk_a2, self.unk_a3)
        return pack_into_stream(self.__DESC_LAYOUT, stream, *args)
