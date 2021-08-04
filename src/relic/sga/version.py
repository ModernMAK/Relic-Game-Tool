from dataclasses import dataclass
from struct import Struct
from typing import Optional

_Version32 = Struct("< L L")
_Version16 = Struct("< H H")


@dataclass
class Version:
    major: int
    minor: Optional[int] = 0

    def __str__(self) -> str:
        return f"Version {self.major}.{self.minor}"

    def __eq__(self, other):
        if not isinstance(other,Version):
            return NotImplementedError
        return self.major == other.major and self.minor == other.minor

    @classmethod
    def DowI_Version(cls):
        return cls(2)

    @classmethod
    def DowII_Version(cls):
        return cls(5)

    @classmethod
    def DowIII_Version(cls):
        return cls(9)
