from dataclasses import dataclass
from struct import Struct
from typing import BinaryIO

from relic.shared import unpack_from_stream, pack_into_stream


@dataclass
class Description:
    __DESC_LAYOUT = Struct("< 64s 64s 5H")

    category: str
    name: str
    unk_a1: int  # 0
    unk_a2: int  # folder count
    unk_a3: int  # 0
    unk_a4: int  # File Count
    unk_a5: int  # 0

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Description':
        args = unpack_from_stream(cls.__DESC_LAYOUT, stream)
        category = args[0].decode("ascii").rstrip("\x00")
        name = args[1].decode("ascii").rstrip("\x00")
        unks = args[2:]
        assert (unks[0] == 0)
        assert (unks[2] == 0)
        assert (unks[4] == 0)
        return Description(category, name, *unks)

    def pack(self, stream: BinaryIO) -> int:
        args = (self.category, self.name, self.unk_a1, self.unk_a2, self.unk_a3)
        return pack_into_stream(self.__DESC_LAYOUT, stream, *args)
