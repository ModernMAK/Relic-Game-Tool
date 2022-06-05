from structlib.byteorder import LittleEndian
from structlib.typedefs.structure import Struct
from structlib.typedefs.strings import PascalString
from structlib.typedefs.integer import IntegerDefinition

Int32 = IntegerDefinition(4, True, alignment=1, byteorder=LittleEndian)
VarString = PascalString(Int32, encoding="ascii", alignment=1, block_size=1)
__all__ = [
    "Struct",
    Int32,
    VarString
]
