from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from math import sqrt
from typing import List, Tuple, Optional, BinaryIO, Union, Any

from serialization_tools.ioutil import has_data
from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct

from relic.chunky import FolderChunk, GenericDataChunk, RelicChunky, ChunkyVersion, GenericRelicChunky, ChunkType, AbstractChunk, ChunkHeaderV0301
from relic.chunky.serializer import read_chunky
from relic.chunky_formats.convertable import ChunkConverterFactory
from relic.chunky_formats.util import ChunkCollectionX
from relic.file_formats.mesh_io import Float3, Float2


@dataclass
class BVolChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "BVOL"
    VERSIONS = [2]

    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class MrfmChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "MRFM"
    VERSIONS = [1]

    raw_bytes: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> MrfmChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class TrimVertex:
    position: Float3
    unk1: Optional[Tuple[int, int, int, int]]
    unk2: Optional[Tuple[int, int, int, int]]
    normal: Optional[Float3]
    tangent: Optional[Float3]
    bi_tangent: Optional[Float3]
    unk6: Optional[Tuple[int, int, int, int]]
    uv: Float2
    uv_detail: Optional[Float2]
    # unks: Optional[bytes] = None

    # A bit of reading for Float16s in Vertex Buffers:
    # 'https://www.yosoygames.com.ar/wp/2018/03/vertex-formats-part-1-compression/'
    #   I couldn't find the Normal using Float32 but the wierd placement of byte (0,0,255,0) got me thinking about the Half format
    #       Unfortunately; it wasn't that simple; but my experience with Voxels taught me about other ways to express normals ALA SNorm and UNorm
    #       I do think this is an SNorm Float16, which kinda works out for us, The article has some fancy talk for how to handle SNorm (due to the dreaded -32758

    INT_16_MAX = 32767
    INT_32_MAX = 2147483647

    @classmethod
    def __int2float(cls, n: List, s: int = INT_16_MAX) -> List[float]:
        return [v / s for v in n]

    @classmethod
    def from_unorm(cls, n: List, int_bits: int = 16):
        s = (2 ** int_bits) - 1  # Max size of int
        return cls.__int2float(n, s)

    @classmethod
    def from_snorm(cls, n: List, int_bits: int = 16):
        s = (2 ** (int_bits - 1)) - 1  # Max size of int

        def __fix_neg(v: int) -> int:  # Snorm maps '-s-1' to -1.0, AND '-s' to -1.0
            return v if v >= -s else -s

        n2 = [__fix_neg(_) for _ in n]
        return cls.__int2float(n2, s)

    @classmethod
    def DEBUG_MAG(cls, v: List):
        sqm = sum(_ ** 2 for _ in v)
        return sqrt(sqm)

    LAYOUT_FLOAT3 = Struct("3f")
    LAYOUT_FLOAT2 = Struct("2f")
    LAYOUT_BYTE4 = Struct("4b")

    @classmethod
    def read_layout(cls, stream: BinaryIO, layout: VertexPropertyLayout) -> Tuple[Any, ...]:
        if layout == VertexPropertyLayout.Float3:
            return cls.LAYOUT_FLOAT3.unpack_stream(stream)
        elif layout == VertexPropertyLayout.Float2:
            return cls.LAYOUT_FLOAT2.unpack_stream(stream)
        elif layout == VertexPropertyLayout.Byte4:
            return cls.LAYOUT_BYTE4.unpack_stream(stream)
        elif layout == VertexPropertyLayout.Unk14:
            return tuple(b for b in stream.read(4))
        else:
            raise NotImplementedError(layout)

    def __read_property(self, stream: BinaryIO, property: VertexProperty, vpl: Tuple[VertexPropertyLayout, int]):
        layout, version = vpl
        data = self.read_layout(stream, layout)
        if property == VertexProperty.Position:
            assert len(data) == 3, len(data)
            self.position = data
        elif property == VertexProperty.Normal:
            if len(data) == 4:
                assert data[3] == 0, data[3]
                data = data[:3]
            assert len(data) == 3, len(data)
            data = tuple(self.from_snorm(data, 8))
            self.normal = data
        elif property == VertexProperty.Tangent:
            if len(data) == 4:
                assert data[3] == 0, data[3]
                data = data[:3]
            assert len(data) == 3, len(data)
            data = tuple(self.from_snorm(data, 8))
            self.tangent = data
        elif property == VertexProperty.BiTangent:
            if len(data) == 4:
                assert data[3] == 0
                data = data[:3]
            assert len(data) == 3, len(data)
            data = tuple(self.from_snorm(data, 8))
            self.bi_tangent = data
        elif property == VertexProperty.Uv:
            assert len(data) == 2, len(data)
            self.uv = data
        elif property == VertexProperty.DetailUvMaybe:
            assert len(data) == 2, len(data)
            self.uv_detail = data
        elif property == VertexProperty.Unk1:
            assert len(data) == 4, len(data)
            self.unk1 = data  # num 0 0 0
        elif property == VertexProperty.Unk2:
            assert len(data) == 4, len(data)
            self.unk2 = data  # 0.0 0.0 val 0.0
        elif property == VertexProperty.Unk6:
            assert len(data) == 4, len(data)
            assert data == (1, 1, 1, 1), data  # Always 1,1,1,1 => SNormed?
            self.unk6 = data  # all same
        else:
            raise NotImplementedError(property)

    @classmethod
    def unpack(cls, stream: BinaryIO, v_size: int, layout: VertexLayout):
        result = cls(None, None, None, None, None, None, None, None, None)
        start = stream.tell()
        try:
            for prop in VertexProperty.property_order():
                if prop in layout:
                    result.__read_property(stream, prop, layout[prop])
            end = stream.tell()
            assert end - start == v_size, ("READ:", end - start, "EXPECTED:", v_size)
        except Exception as e:
            raise
        return result


class VertexPropertyLayout(Enum):
    Byte4 = 2  # I got confused, everwhere I say UNORM is closer; I meant snorm; i swapped the var names by acident, so; to clarify 'SNORM BYTE 4' is correct
    Float2 = 3
    Float3 = 4
    Unk14 = 14  # IDK


class VertexProperty(Enum):
    Position = 0
    Unk1 = 1
    Unk2 = 2
    Normal = 3
    Tangent = 4
    BiTangent = 5
    Unk6 = 6
    Uv = 8
    DetailUvMaybe = 9

    @classmethod
    def property_order(cls) -> List[VertexProperty]:
        return [cls.Position, cls.Unk1, cls.Unk2, cls.Normal, cls.Tangent, cls.BiTangent, cls.Unk6, cls.Uv, cls.DetailUvMaybe]


class VertexLayout(UserDict):
    @classmethod
    def __fix(cls, key, value):
        layout, version = value
        if not isinstance(key, VertexProperty):
            key = VertexProperty(key)
        if not isinstance(layout, VertexPropertyLayout):
            layout = VertexPropertyLayout(layout)
        return key, (layout, version)

    @classmethod
    def __fix_key(cls, key):
        if not isinstance(key, VertexProperty):
            key = VertexProperty(key)
        return key

    def __setitem__(self, key: Union[VertexProperty, int], value: Union[Tuple[VertexPropertyLayout, int], Tuple[int, int]]):
        key, value = self.__fix(key, value)
        super(VertexLayout, self).__setitem__(key, value)

    def __getitem__(self, key: Union[VertexProperty, int]):
        key = self.__fix_key(key)
        return super(VertexLayout, self).__getitem__(key)


@dataclass
class VertexDefinition:
    LAYOUT = Struct("<3L")

    # a: TrimDataChunk.VertexDefType  # UNIQUE! ID?
    # b: int
    # Size? Not Size, 32/13! Unless padded (3->4)? but 32/14! Unless padded to 4 (2->4 & 3->4)? 32/20... Not Size
    # c: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> Tuple[VertexProperty, int, VertexPropertyLayout]:
        a, b, c = cls.LAYOUT.unpack_stream(stream)
        try:
            assert a in [0, 1, 2, 3, 4, 5, 6, 8, 9], a
            assert b in [3, 4], b  # UH OH, 3 or 4...
            assert c in [2, 3, 4, 14], c
            return VertexProperty(a), b, VertexPropertyLayout(c)
        except Exception as e:
            raise

        # return cls(a, c)


@dataclass
class TrimDataChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "DATA"
    VERSIONS = [7]

    unk_a_blocks: List[Tuple[int, int, int]]
    vertexes: List[TrimVertex]
    unk_b: int
    unk_c: int
    indexes: List[int]
    material_name: str
    skel: List[Tuple[str, List[float]]]
    unk_d: int
    unk_e: int

    __short_layout = Struct("< H")
    __int_layout = Struct("< L")
    __int2_layout = Struct("< 2L")
    __int3_Layout = Struct("< 3L")
    __int4_Layout = Struct("< 4L ")
    __unk_skel_layout = Struct("< 24f") # DOH, I was thinking bytes; 24 floats is 6 x 4, so 2x3x4? Local and World Matrix (3x4 or 4x3, which evers the right one)

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        with BytesIO(chunk.raw_bytes) as stream:
            # THIS IS THE VERTEX LAYOUT MAYBE?
            vert_def_count = cls.__int_layout.unpack_stream(stream)[0]
            vert_defs = [VertexDefinition.unpack(stream) for _ in range(vert_def_count)]
            vert_layout = VertexLayout()
            for p, punk, pl in vert_defs:
                vert_layout[p] = (pl, punk)

            v_count = cls.__int_layout.unpack_stream(stream)[0]
            v_size = cls.__int_layout.unpack_stream(stream)[0]
            ...
            # Vertexes in this format are 'packed' instead of 'flattened'
            # This is probably why this format specifies the vertex size explicitly.
            vertexes = [TrimVertex.unpack(stream, v_size, vert_layout) for _ in range(v_count)]
            unk_b, index_count, unk_c, index_count_2 = cls.__int4_Layout.unpack_stream(stream)
            assert index_count == index_count_2
            assert unk_b == 1
            assert unk_c == 3
            # assert unk_b == unk_c, (unk_b, unk_c)
            indexes = [cls.__short_layout.unpack_stream(stream)[0] for _ in range(index_count)]
            name_size = cls.__int_layout.unpack_stream(stream)[0]
            name = stream.read(name_size).decode("ascii")
            skel_count = cls.__int_layout.unpack_stream(stream)[0]
            skels = []
            for _ in range(skel_count):
                skel_unks = cls.__unk_skel_layout.unpack_stream(stream)
                skel_name_len = cls.__int_layout.unpack_stream(stream)[0]
                skel_name = stream.read(skel_name_len).decode("ascii")
                skels.append((skel_name, skel_unks))
            unk_d, unk_e = cls.__int2_layout.unpack_stream(stream)
            assert not has_data(stream)
            return cls(chunk.header, vert_defs, vertexes, unk_b, unk_c, indexes, name, skels, unk_d, unk_e)

            # # PSUEDOCODE
        # unk_count_a = read_int32
        # unk_a_block = [read_int32x3 for _ in range(unk_count_a)]
        # v_count = read_int32
        # v_size = read_int32
        # v_buffer = read_bytes(v_size*v_count)
        # unk_ba, index_count, unk_bb, index_count_again = read_int32 * 4
        # i_buffer = read_bytes(index_count * 2)
        # name = read_length_string # AKA len = read_int32, read_bytes(len)
        # skel_count = read_int32
        # skels = []
        # for _ in range(skel_count):
        #     skel_unks = read_float32 * 6 * 4
        #     skel_name = read_length_string
        #     skel = (skel_unks, skel_name)
        #     skels.add(skel)
        # unk_ca, unk_cb = read_int32 * 2


# @ 0x58 ~ Vertex Count
# 40 is Vertex Size
# @ 0x4958 ~ Index Block


@dataclass
class TrimChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "TRIM"
    VERSIONS = [7]

    bvol: List[BVolChunk]
    data: TrimDataChunk
    mrfm: Optional[MrfmChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> TrimChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = TrimChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        bvol = x.find(BVolChunk, True)
        data = x.find(TrimDataChunk)
        mrfm = x.find(MrfmChunk)
        assert len(chunk.chunks) == 1 + len(bvol) + (1 if mrfm else 0)
        return cls(chunk.header, bvol, data, mrfm)


@dataclass
class ImodMeshChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MESH"
    VERSIONS = [3]
    trim: TrimChunk

    @classmethod
    def convert(cls, chunk: FolderChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        assert len(chunk.chunks) == 1, len(chunk.chunks)
        converted = ImodChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        trim = x.find(TrimChunk)
        return ImodMeshChunk(chunk.header, trim)


@dataclass
class NodeChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "NODE"
    VERSIONS = [2, 3]  # 3 is common

    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class SharedMgrpChunk:
    nodes: List[NodeChunk]


@dataclass
class MtrlInfoChunk(AbstractChunk):
    LAYOUT = VStruct("v")
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "INFO"
    VERSIONS = [1]
    shader_name: str

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        # with BytesIO(chunk.raw_bytes) as stream:
        name = cls.LAYOUT.unpack(chunk.raw_bytes)[0]
        # name_len = Struct("< L").unpack_stream(stream)[0]
        name = name.decode("ascii")
        return cls(chunk.header, name)


class MaterialVarType(Enum):
    Texture = 9
    WorldMaybe = 8
    HighlightMaybe = 10
    MultiplierMaybe = 1
    OcclusionFlagMaybe = 0
    MatrixRow = 5
    Color = 4  # Prop is 'Colour'
    Water = 3  # Idk about this one 3:'WaterReflection_WindDirection' # PROBABLY WATER VARS?!


@dataclass
class GenericVar:
    @property
    def var_type(self) -> MaterialVarType:
        raise NotImplementedError


@dataclass
class UnimplementedVar(GenericVar):
    __var_type: MaterialVarType
    data: bytes

    @property
    def var_type(self) -> MaterialVarType:
        return self.__var_type

    @classmethod
    def unpack(cls, stream: BinaryIO, var_type: MaterialVarType) -> UnimplementedVar:
        return cls(var_type, stream.read())


@dataclass
class TextureVar(GenericVar):
    @property
    def var_type(self) -> MaterialVarType:
        return MaterialVarType.Texture

    texture: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> TextureVar:
        texture = stream.read().decode("ascii").strip("\0")
        return cls(texture)


@dataclass
class VarChunk(AbstractChunk):
    LAYOUT = VStruct("< v l v")
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "VAR"
    VERSIONS = [1]

    property_name: str
    property_data: GenericVar

    @property
    def var_type(self) -> MaterialVarType:
        return self.property_data.var_type

    # args: Optional[Tuple] = None
    # excess: Optional[Tuple[bytes, bytes]] = None

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        with BytesIO(chunk.raw_bytes) as stream:
            prop, var_type, buffer = cls.LAYOUT.unpack_stream(stream)
            prop = prop.decode("ascii")
            try:
                var_type = MaterialVarType(var_type)  # 4 has prop as colour
            except ValueError:
                print(prop)
                raise
            # This acts as a soft assertion; if the buffer is too small, we'll get an unpack error
            # if either exceess has extra bytes, then somethings probably wrong, but I don't check for it
            # T-o-d-o check for it ~ archive_tools VStruct will make sure the buffer does not have any missing bytes (still does not check for excess tho)
            assert not has_data(stream), stream.read()
            # return cls(chunk.header, prop, var_type, buffer)
            var_data = UnimplementedVar(var_type, buffer)
            with BytesIO(buffer) as buffer_stream:
                if var_type == MaterialVarType.Texture:
                    var_data = TextureVar.unpack(buffer_stream)
            return cls(chunk.header, prop, var_data)

            #         args = buffer_stream.read().decode("ascii").strip("\0")
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(chunk.header, prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.HighlightMaybe:
            #         args = Struct("< b").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.MatrixRow:
            #         args = Struct("< 4f").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.MultiplierMaybe:
            #         args = Struct("< f").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.OcclusionFlagMaybe:
            #         args = Struct("< L").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.WorldMaybe:
            #         args = Struct("< 16f").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)

            # raise NotImplementedError


@dataclass
class SkelInfoChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "INFO"
    VERSIONS = [1]
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class BoneChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "BONE"
    VERSIONS = [7]
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class SkelChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "SKEL"
    VERSIONS = [3]
    info: SkelInfoChunk
    bone: List[BoneChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> SkelChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = SkelChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        info = x.find(SkelInfoChunk)
        bone = x.find(BoneChunk, True)
        assert len(chunk.chunks) == 1 + len(bone)
        return SkelChunk(chunk.header, info, bone)


@dataclass
class MtrlChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MTRL"
    VERSIONS = [1]
    # name: str
    info: MtrlInfoChunk
    var: List[VarChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'MtrlChunk':
        assert chunk.header.version in cls.VERSIONS
        converted = ModelChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        info = x.find(MtrlInfoChunk)
        var = x.find(VarChunk, True)
        assert len(chunk.chunks) == 1 + len(var), [c.header.id for c in chunk.chunks]
        return MtrlChunk(chunk.header, info, var)


@dataclass
class MrksChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "MRKS"
    VERSIONS = [1]

    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class ImodDataChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "DATA"
    VERSIONS = [9]

    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class ImodChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "IMOD"
    VERSIONS = [1, 4]

    data: Optional[ImodDataChunk]
    mesh: List[ImodMeshChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = ImodChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        data = x.find(ImodDataChunk)  # TODO check if data does not exist if version is 1
        mesh = x.find(ImodMeshChunk, True)  # TODO check if only 1 mesh is allowed for version 1
        assert len(chunk.chunks) == (1 if data else 0) + len(mesh), [c.header.id for c in chunk.chunks]
        return cls(chunk.header, data, mesh)


@dataclass
class ImdgMeshChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MESH"
    VERSIONS = [3]
    imod: ImodChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ImdgMeshChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        assert len(chunk.chunks) == 1
        converted = ImdgChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        imod = x.find(ImodChunk)
        return cls(chunk.header, imod)


@dataclass
class ImdgChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "IMDG"
    VERSIONS = [1]

    mesh: List[ImdgMeshChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ImdgChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = ImdgChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        mesh = x.find(ImdgMeshChunk, True)
        assert len(chunk.chunks) == len(mesh), [c.header.id for c in chunk.chunks]
        return cls(chunk.header, mesh)


@dataclass
class MgrpMeshChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MESH"
    VERSIONS = [3]

    imdg: ImdgChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MgrpMeshChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        assert len(chunk.chunks) == 1
        converted = MgrpChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        imdg = x.find(ImdgChunk)
        return MgrpMeshChunk(chunk.header, imdg)


@dataclass
class FlgsChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "FLGS"
    VERSIONS = [2]

    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class MgrpChunk(AbstractChunk):  # MGRP is probably Mesh GROUP
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MGRP"
    VERSIONS = [2, 3]  # 3 is common, 2 also occurs

    node: List[NodeChunk]
    mesh: List[MgrpMeshChunk]
    flgs: Optional[FlgsChunk]  # ONLY in v2

    @classmethod
    def convert(cls, chunk: FolderChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = MgrpChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        node = x.find(NodeChunk, True)
        mesh = x.find(MgrpMeshChunk, True)
        flgs = x.find(FlgsChunk)
        assert len(chunk.chunks) == len(node) + len(mesh) + (1 if flgs else 0), [c.header.id for c in chunk.chunks]
        assert len(node) == len(mesh), (len(node), len(mesh))  # Just an assumption
        return cls(chunk.header, node, mesh, flgs)


@dataclass
class ModlMeshChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MESH"
    VERSIONS = [3]
    mgrp: MgrpChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ModlMeshChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        assert len(chunk.chunks) == 1
        converted = ModelChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        mgrp = x.find(MgrpChunk)
        return cls(chunk.header, mgrp)


@dataclass
class MsdChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "MSD "  # SPACE IS IMPORTANT
    VERSIONS = [1, 2]

    name_a: Optional[str]
    one: int
    sub_names: List[str]

    __INT = Struct("< l")
    __INVALID = __INT.unpack(bytes([0xff, 0xff, 0xff, 0xff]))[0]

    # data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        # TODO, this looks like a special case thing
        #   BUT, it's probably actually caused by improperly reading chunks (which happened before I fixed the layout for name for V3.1 headers)
        if not isinstance(chunk.header, ChunkHeaderV0301):
            raise ValueError(chunk.header)
        with BytesIO(chunk.raw_bytes) as stream:
            if chunk.header.unk_a == cls.__INVALID:
                assert chunk.header.version == 1
                one = cls.__INT.unpack_stream(stream)[0]
                # assert one == 1, one
                assert not has_data(stream)
                return cls(chunk.header, None, one, [])
            else:
                assert chunk.header.version == 2
                name_a = stream.read(cls.__INT.unpack_stream(stream)[0]).decode("ascii")
                one = cls.__INT.unpack_stream(stream)[0]
                # assert one == 1, one

                sub_names = [stream.read(cls.__INT.unpack_stream(stream)[0]).decode("ascii") for _ in range(one)]
                assert not has_data(stream)
                return cls(chunk.header, name_a, one, sub_names)


@dataclass
class CnbpChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "CNBP"
    VERSIONS = [3]

    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class MsbpChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MSBP"
    VERSIONS = [1]

    msd: List[MsdChunk]
    cnbp: List[CnbpChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MsbpChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = ModelChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        msd = x.find(MsdChunk, True)
        cnbp = x.find(CnbpChunk, True)
        assert len(chunk.chunks) == len(cnbp) + len(msd), [c.header.id for c in chunk.chunks]
        return cls(chunk.header, msd, cnbp)


@dataclass
class DtbpChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "DTBP"
    VERSIONS = [3]

    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class TsetDataChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "DATA"
    VERSIONS = [3]

    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class TsetChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "TSET"
    VERSIONS = [1]

    data: TsetDataChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> TsetChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        assert len(chunk.chunks) == 1, [(c.header.type, c.header.id) for c in chunk.chunks]
        converted = TsetChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        data = x.find(TsetDataChunk)
        return cls(chunk.header, data)


@dataclass
class LsdChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "LSD "
    VERSIONS = [2]
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> LsdChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class LsbpChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "LSBP"
    VERSIONS = [1]

    lsd: LsdChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> LsbpChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        assert len(chunk.chunks) == 1, [(c.header.type, c.header.id) for c in chunk.chunks]
        converted = ModelChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        lsd = x.find(LsdChunk)
        return cls(chunk.header, lsd)


@dataclass
class ModlChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MODL"
    VERSIONS = [1]

    mtrls: List[MtrlChunk]
    mesh: ModlMeshChunk
    skel: Optional[SkelChunk]
    msbp: MsbpChunk
    dtbp: DtbpChunk
    mrks: MrksChunk
    tset: List[TsetChunk]
    lsbp: Optional[LsbpChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = ModelChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        mtrl = x.find(MtrlChunk, True)
        mesh = x.find(ModlMeshChunk)
        skel = x.find(SkelChunk)
        msbp = x.find(MsbpChunk)
        dtbp = x.find(DtbpChunk)
        mrks = x.find(MrksChunk)
        lsbp = x.find(LsbpChunk)
        tset = x.find(TsetChunk, True)
        assert len(chunk.chunks) == len(mtrl) + len(tset) + 4 + (1 if skel else 0) + (1 if lsbp else 0), (len(chunk.chunks), [c.header.id for c in chunk.chunks])
        return ModlChunk(chunk.header, mtrl, mesh, skel, msbp, dtbp, mrks, tset, lsbp)


@dataclass
class ModelChunky(RelicChunky):
    VERSIONS = [ChunkyVersion.Dow2]
    modl: ModlChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> ModelChunky:
        assert chunky.header.version in cls.VERSIONS, chunky.header.version
        assert len(chunky.chunks) == 1, len(chunky.chunks)
        converted = ModelChunkConverter.convert_many(chunky.chunks)
        x = ChunkCollectionX.list2col(converted)
        modl = x.find(ModlChunk)
        return ModelChunky(chunky.header, modl)


if __name__ == "__main__":
    # path = r"D:\Dumps\DOW_II\full_dump\art\race_ig\troops_wargear\heads\general\general_head.model"
    path = r"D:\Dumps\DOW_II\full_dump\art\race_ig\troops_wargear\armour\cadian_armour\cadian_armour.model"
    with open(path, "rb") as handle:
        chunky = read_chunky(handle)
        model = ModelChunky.convert(chunky)
        print(model)

ModelChunkConverter = ChunkConverterFactory()
ModelChunkConverter.register(ModlChunk)
ModelChunkConverter.register(ModlMeshChunk)
ModelChunkConverter.register(MtrlChunk)
ModelChunkConverter.register(MtrlInfoChunk)
ModelChunkConverter.register(VarChunk)
ModelChunkConverter.register(MgrpChunk)
ModelChunkConverter.register(MrksChunk)
ModelChunkConverter.register(SkelChunk)
ModelChunkConverter.register(MsbpChunk)
ModelChunkConverter.register(MsdChunk)
ModelChunkConverter.register(CnbpChunk)
ModelChunkConverter.register(DtbpChunk)
ModelChunkConverter.register(TsetChunk)
ModelChunkConverter.register(LsbpChunk)
ModelChunkConverter.register(LsdChunk)

MgrpChunkConverter = ChunkConverterFactory()
MgrpChunkConverter.register(NodeChunk)
MgrpChunkConverter.register(MgrpMeshChunk)
MgrpChunkConverter.register(ImdgChunk)
MgrpChunkConverter.register(FlgsChunk)

ImdgChunkConverter = ChunkConverterFactory()
ImdgChunkConverter.register(ImdgMeshChunk)
ImdgChunkConverter.register(ImodChunk)

ImodChunkConverter = ChunkConverterFactory()
ImodChunkConverter.register(ImodMeshChunk)
ImodChunkConverter.register(TrimChunk)
ImodChunkConverter.register(ImodDataChunk)

TrimChunkConverter = ChunkConverterFactory()
TrimChunkConverter.register(TrimDataChunk)
TrimChunkConverter.register(BVolChunk)
TrimChunkConverter.register(MrfmChunk)

SkelChunkConverter = ChunkConverterFactory()
SkelChunkConverter.register(SkelInfoChunk)
SkelChunkConverter.register(BoneChunk)

TsetChunkConverter = ChunkConverterFactory()
TsetChunkConverter.register(TsetDataChunk)
