from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from struct import Struct
from typing import Tuple, Optional, List

from relic.chunky import DataChunk, FolderChunk
from relic.util.struct_util import unpack_from_stream


@dataclass
class MtrlInfoChunk:
    shader_name: str

    @classmethod
    def convert(cls, chunk: DataChunk):
        with BytesIO(chunk.data) as stream:
            name_len = unpack_from_stream(Struct("< L"), stream)[0]
            name = stream.read(name_len).decode("ascii")
            return cls(name)


class MaterialVarType(Enum):
    Texture = 9
    WorldMaybe = 8
    HighlightMaybe = 10
    MultiplierMaybe = 1
    OcclusionFlagMaybe = 0
    MatrixRow = 5


@dataclass
class VarChunk:
    property_name: str
    var_type: MaterialVarType

    args: Optional[Tuple] = None
    excess: Optional[Tuple[bytes, bytes]] = None

    @classmethod
    def convert(cls, chunk: DataChunk):
        with BytesIO(chunk.data) as stream:
            prop_len = unpack_from_stream(Struct("< L"), stream)[0]
            prop = stream.read(prop_len).decode("ascii")
            var_type_val = unpack_from_stream(Struct("< L"), stream)[0]
            var_type = MaterialVarType(var_type_val)
            buffer_len = unpack_from_stream(Struct("< L "), stream)[0]
            buffer = stream.read(buffer_len)
            # This acts as a soft assertion; if the buffer is too small, we'll get an unpack error
            # if either exceess has extra bytes, then somethings probably wrong, but I don't check for it
            # TODO check for it
            with BytesIO(buffer) as buffer_stream:
                if var_type == MaterialVarType.Texture:
                    args = buffer_stream.read(buffer_len).decode("ascii").strip("\0")
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.HighlightMaybe:
                    args = unpack_from_stream(Struct("< b"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.MatrixRow:
                    args = unpack_from_stream(Struct("< 4f"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.MultiplierMaybe:
                    args = unpack_from_stream(Struct("< f"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.OcclusionFlagMaybe:
                    args = unpack_from_stream(Struct("< L"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.WorldMaybe:
                    args = unpack_from_stream(Struct("< 16f"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)

                raise NotImplementedError


@dataclass
class MtrlChunk:
    name: str
    info: MtrlInfoChunk
    vars: List[VarChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'MtrlChunk':
        info = MtrlInfoChunk.convert(chunk.get_data_chunk("INFO"))
        vars = [VarChunk.convert(v) for v in chunk.get_data_chunks("VAR")]
        return MtrlChunk(chunk.header.name, info, vars)

