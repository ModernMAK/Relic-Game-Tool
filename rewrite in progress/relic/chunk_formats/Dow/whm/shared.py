import struct

# Uhhhhh why is this here?! This Is garbage!
num_layout = struct.Struct("< L")
_UNK_STRUCT = struct.Struct("< L L")
raise NotImplementedError("Please use these structs in context!")
