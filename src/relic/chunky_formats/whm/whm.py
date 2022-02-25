from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Tuple, Any
from typing import List, Optional

from archive_tools.structx import Struct
from archive_tools.vstruct import VStruct

from ..common_chunks.fbif import FbifChunk
from ..common_chunks.imag import TxtrChunk
from ..convertable import UnimplementedDataChunk, ChunkConverterFactory, ChunkCollectionX, UnimplementedFolderChunk
from ...chunky import ChunkyVersion
from ...chunky.chunk.chunk import GenericDataChunk, FolderChunk, AbstractChunk
from ...chunky.chunk.header import ChunkType
from ...chunky.chunky.chunky import RelicChunky, GenericRelicChunky
from ...file_formats.mesh_io import Float3, Float4, Float2, Short3


@dataclass
class SshrChunk(AbstractChunk):
    VERSIONS = [2]
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "SSHR"
    LAYOUT = VStruct("v")
    name: str

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> SshrChunk:
        # VERSIONED
        assert chunk.header.version in cls.VERSIONS, chunk.header.version

        with BytesIO(chunk.raw_bytes) as stream:
            name = cls.LAYOUT.unpack_stream(stream)[0]
            name = name.decode("ascii")
            assert len(chunk.raw_bytes) == len(name) + cls.LAYOUT.min_size
            return SshrChunk(chunk.header, name)


@dataclass
class MsclHeader:
    LAYOUT = Struct("< l b l 2l")
    flag: bytes
    val: int
    name_count: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> MsclHeader:
        rsv_0a, flag, val, rsv_0b, names = cls.LAYOUT.unpack_stream(stream)

        assert rsv_0a == 0
        assert rsv_0b == 0
        assert flag in [1, 0], (flag, val)

        return MsclHeader(flag, val, names)


@dataclass
class MslcName:
    LAYOUT = VStruct("vl")
    name: str
    unk_a: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> MslcName:
        name, unk = cls.LAYOUT.unpack_stream(stream)
        name = name.decode("ascii")
        assert len(name) + cls.LAYOUT.min_size
        return MslcName(name, unk)


# class MslcBlockFormat(Enum):
#     Vertex32 = enum.auto()  # = 37
#     Vertex48 = enum.auto()  # = 39
#
#     # Oh, boy; IDK how many 'texture' classes there are but there are enough
#     Texture = enum.auto()
#
#     @classmethod
#     def from_code(cls, code: int):
#         if code <= 6:
#             return MslcBlockFormat.Texture
#
#         lookup = {
#             37: MslcBlockFormat.Vertex32,
#             39: MslcBlockFormat.Vertex48,
#         }
#         value = lookup.get(code)
#         if value:
#             return value
#         raise KeyError(code)
#
#     def vertex_buffer_size(self) -> int:
#         size = {
#             MslcBlockFormat.Vertex48: 48,
#             MslcBlockFormat.Vertex32: 32,
#         }
#         val = size.get(self)
#         if val is None:
#             raise KeyError(f"'{val}' is not a Vertex Buffer Type")
#         return val
#
#     def to_code(self) -> int:
#
#         lookup = {
#             MslcBlockFormat.Vertex32: 37,
#             MslcBlockFormat.Vertex48: 39,
#         }
#         return lookup[self.value]


# @dataclass
# class VertexMsclBlock:
#     format: MslcBlockFormat
#     count: int
#     vertex_buffer: bytes
#     _code: int = 0


# @dataclass
# class Vertex32MsclBlock:
#     LAYOUT = Struct("< 3f 3f 2f")  # Float3, Float3, Float2
#     vertexes: List[Tuple[Float3, Float3, Float2]]
#
#     @property
#     def format(self) -> MslcBlockFormat:
#         return MslcBlockFormat.Vertex32
#
#     @property
#     def format_code(self) -> int:
#         return self.format.to_code()
#
#     @classmethod
#     def convert(cls, stream: BinaryIO, count):
#         vertex_list: List[Tuple[Float3, Float3, Float2]] = []
#         for i, buffer in enumerate(iter_read(stream, cls.LAYOUT.size)):
#             if i == count:
#                 break
#             args = cls.LAYOUT.unpack(buffer)
#             pos: Float3 = args[0:3]
#             norm: Float3 = args[3:6]
#             uv: Float2 = args[6:8]
#             vert = (pos, norm, uv)
#             vertex_list.append(vert)
#         return Vertex32MsclBlock(vertex_list)

# @dataclass
# class TextureMsclSubBlock:
#     name: str
#     count: int
#     index_buffer: bytes
#     zero: int


# @dataclass
# class TextureMsclBlock:
#     format: MslcBlockFormat
#     zero: int
#     blocks: List[TextureMsclSubBlock]
#     info: List[Tuple[int, int]]
#
#     unk_a: int
#     unk_b: int
#     unk_c: int
#     _code: int = 0


# MslcBlock = Union[VertexMsclBlock, TextureMsclBlock]

# class MslcBlockUtil:
#     LAYOUT = Struct("< 2L")
#     INFO = Struct("< 2l")
#     UNK = Struct("< 3l")
#     INDEX_BLOCK_LAYOUT = VStruct("vl")
#
#     @classmethod
#     def unpack(cls, stream: BinaryIO) -> MslcBlock:
#         def read_index_block() -> TextureMsclSubBlock:
#             name, index_count = cls.INDEX_BLOCK_LAYOUT.unpack_stream(stream)
#             name = name.decode("ascii")
#             i_buffer = stream.read(index_count * 2)  # index is a short
#             return TextureMsclSubBlock(name, index_count, i_buffer, count)
#
#         # Code currently has a lot of 'garbage values'
#         #   But '5', '3', '2', '39', '37', '1', '6', look the least garbagey and the most common.
#         #       All those numbers occur at least 9+ times; 39, 37 & 1 occur at least 3000 times
#
#         count, code = cls.LAYOUT.unpack_stream(stream)
#         f = MslcBlockFormat.from_code(code)
#         if f == MslcBlockFormat.Texture:
#             texture_count = code
#             subs = []
#             infos = []
#             for _ in range(texture_count):
#                 sub = read_index_block()
#
#                 info = cls.INFO.unpack_stream(stream)
#
#                 subs.append(sub)
#                 infos.append(info)
#
#             unks = cls.UNK.unpack_stream(stream)
#
#             return TextureMsclBlock(f, count, subs, infos, *unks, code)
#
#         try:
#             # if f == MslcBlockFormat.Vertex32:
#             #     return Vertex32MsclBlock.convert(stream, count)
#             buffer_size = f.vertex_buffer_size()
#             v_buffer = stream.read(buffer_size * count)
#             return VertexMsclBlock(f, count, v_buffer, code)
#         except KeyError:
#             pass
#
#         raise NotImplementedError(code)


@dataclass
class MsgrName:
    LAYOUT = VStruct("v <l")
    name: str
    # unk_a: int
    flag: int
    sub_names: Optional[List[MsgrName]]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> MsgrName:
        name, sub_count = cls.LAYOUT.unpack_stream(stream)
        name = name.decode("ascii")
        assert sub_count == 0
        sub_names = [] if sub_count != -1 else None
        if sub_names:
            for _ in range(sub_count):
                p = MsgrName.unpack(stream)
                sub_names.append(p)
        return MsgrName(name, sub_count, sub_names)


Byte4 = Tuple[int, int, int, int]
Byte3 = Tuple[int, int, int]
Byte = int


@dataclass
class MslcVertexData:
    VERTEX_POS_LAYOUT = Struct("< 3f")
    VERTEX_NORM_LAYOUT = Struct("< 3f")
    VERTEX_UV_LAYOUT = Struct("< 2f")
    VERTEX_BONE_WEIGHT_LAYOUT = Struct("< 3f 3c c")

    positions: List[Float3]
    normals: List[Float3]
    bone_weights: Optional[List[Tuple[Float3, Byte4]]]
    uvs: List[Float2]

    @property
    def count(self) -> int:
        return len(self.positions)

    @classmethod
    def unpack(cls, stream: BinaryIO, vertex_count: int, V_SIZE: int) -> MslcVertexData:
        if V_SIZE in [32, 48]:
            position_buffer = [cls.VERTEX_POS_LAYOUT.unpack_stream(stream) for _ in range(vertex_count)]
        else:
            position_buffer = None

        if V_SIZE in [48]:
            bone_buffer = [cls.VERTEX_BONE_WEIGHT_LAYOUT.unpack_stream(stream) for _ in range(vertex_count)]
            bone_buffer = [((w1, w2, w3), (b1, b2, b3), f) for w1, w2, w3, b1, b2, b3, f in bone_buffer]
        else:
            bone_buffer = None

        if V_SIZE in [32, 48]:
            normal_buffer = [cls.VERTEX_NORM_LAYOUT.unpack_stream(stream) for _ in range(vertex_count)]
        else:
            normal_buffer = None

        if V_SIZE in [32, 48]:
            uv_buffer = [cls.VERTEX_UV_LAYOUT.unpack_stream(stream) for _ in range(vertex_count)]
        else:
            uv_buffer = None

        return cls(position_buffer, normal_buffer, bone_buffer, uv_buffer)


Short4 = Tuple[int, int, int, int]


@dataclass
class MslcSubmeshData:
    COUNT_LAYOUT = Struct("i")
    NAME_LAYOUT = VStruct("v")
    INDEX_LAYOUT = Struct("H")
    INDEX_TRI_LAYOUT = Struct("3H")
    INDEX_TRAILING_LAYOUT = Struct("4h")

    texture_path: str
    triangles: List[Short3]
    trailing: Short4

    @classmethod
    def unpack(cls, stream: BinaryIO) -> MslcSubmeshData:
        name = cls.NAME_LAYOUT.unpack_stream(stream)[0].decode("ascii")
        index_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
        tri_count = index_count / cls.INDEX_TRI_LAYOUT.args
        assert int(tri_count) == tri_count
        indexes = [cls.INDEX_TRI_LAYOUT.unpack_stream(stream) for _ in range(int(tri_count))]
        trailing = cls.INDEX_TRAILING_LAYOUT.unpack_stream(stream)
        return cls(name, indexes, trailing)


@dataclass
class MslcDataChunk(AbstractChunk):
    CHUNK_ID = "DATA"
    CHUNK_TYPE = ChunkType.Data
    VERSIONS = [2]
    # data: bytes

    HEADER_NAME_LAYOUT = VStruct("vi")
    COUNT_LAYOUT = Struct("i")
    NAME_LAYOUT = VStruct("v")
    # VERTEX_LAYOUT = Struct("32s")
    # EXCESS_SIZE = 8

    HEADER_LAYOUT = Struct("< i b i i")

    sub_header: Tuple[Any, ...]
    unks: Tuple[Any, ...]
    header_names: List[Tuple[str, int]]
    vertex_buffers: MslcVertexData
    triangle_buffers: List[Tuple[str, List[Tuple[Short3]], List]]
    trailing_data: bytes  # LIKELY EMBEDDED TEXTURES, No magic so TGA? Or relic's wierd no-magic DDS

    UNK2TEX = {}
    _EX = []
    TEX_SIZES = {
        441096, 578440, 824112, 264924, 339144, 84288, 11112, 7620, 5820, 3996, 125616, 112236, 179028, 216024, 256308, 107340, 142692, 148284, 54600, 38496, 29304, 32256, 13236, 29712, 2016, 10500, 58680, 5868, 199452, 58656, 41712, 141456, 138396, 445596, 111672, 12684, 195636, 183672, 116100,
        356496, 197976, 176424, 66276, 90804,
        126144, 64308, 69996, 204432, 10164, 31716, 43872, 72204, 11808, 9828, 9288, 77268, 29040, 2556, 24204, 63240, 24276, 90980, 53004, 8748, 20700, 14988, 11556, 31356, 17436, 46380, 102300, 389148, 315840, 177696, 156144, 167676, 165888, 167772, 25152, 44820, 9396, 36948,
        35664, 56844, 70392, 103752, 54360, 64524, 61272, 197364, 29340, 26316, 15276, 15996, 11868, 95352, 180084, 258120, 184836, 188280, 230604, 10176, 9252, 8328, 6516, 7596, 6876, 7956, 6876, 7956, 8496, 8496, 8496, 8496, 239004, 1836, 9780, 1116, 1116, 1116, 21888, 8052, 2220, 1836,
        9780, 53148, 1116, 1116, 1116, 1116, 1116, 5124, 5124, 1116, 1116, 1116, 53148, 1116, 1116, 1116, 53148, 1116, 5124, 5124, 1116, 21888, 8052, 2220, 5124, 1116, 21888, 8052, 2220, 1836, 9780, 21888, 8052, 2220, 1836, 9780, 72180, 5328, 32088, 47664, 37500, 97092, 38292, 5328, 192168,
        1116, 21888, 8052, 2220, 1836, 9780, 21888, 8052, 2220, 1836, 9780, 72180, 1116, 1116, 1116, 1116, 1116, 5124, 5124, 1116, 34116, 9780, 1836, 2220, 8052, 21888, 1116, 1116, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 5124, 1116, 131508, 35820, 14268, 9516, 2736, 9516, 1656, 5328, 868,
        34116, 9780, 1836, 2220, 8052, 21888, 1116, 1116, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 1116, 34116, 9780, 1836, 2220, 8052, 21888, 1116, 1116, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 5124, 1116, 119616, 59184, 3636, 39708, 34116, 9780, 1836, 2220, 8052, 21888, 1116, 1116,
        9780, 1836, 2220, 8052, 21888, 1116, 5124, 5124, 8052, 2220, 1836, 9780, 21888, 8052, 2220, 1836, 9780, 288684, 1116, 5124, 5124, 1116, 2220, 2220, 2220, 25488, 25488, 7692, 7692, 7692, 7692, 71196, 17052, 1116, 5124, 5124, 1116, 4428, 4428, 4428, 4428, 21888, 4428, 4428, 21888,
        8052, 2220, 1836, 9780, 21888, 8052, 2220, 1836, 9780, 288684, 6924, 9036, 6924, 9036, 1116, 6156, 6156, 238944, 4428, 21888, 8052, 2220, 1836, 9780, 21888, 8052, 2220, 1836, 9780, 182412, 1116, 5124, 5124, 1116, 4428, 4428, 144348, 2220, 2220, 2220, 2220, 1116, 5124, 5124, 1116,
        21888, 8052, 2220, 1836, 9780, 21888, 8052, 2220, 2220, 2220, 2220, 2220, 1116, 5124, 5124, 1116, 21888, 8052, 2220, 1836, 9780, 21888, 8052, 2220, 1836, 9780, 2220, 1836, 9780, 144348, 25488, 25488, 7692, 7692, 7692, 7692, 71196, 17052, 11196, 11196, 33852, 162468, 1836, 9780,
        144348, 2220, 2220, 2220, 2220, 1116, 5124, 5124, 1116, 21888, 8052, 2220, 1836, 9780, 21888, 8052, 88356, 1116, 5124, 5124, 1116, 21888, 8052, 2220, 1836, 9780, 1116, 1116, 21888, 8052, 2220, 1836, 9780, 34116, 39864, 209988, 53148, 9780, 1836, 1116, 5124, 2220, 8052, 21888, 1116,
        1116, 1116, 9780, 1836, 1116, 5124, 2220, 8052, 21888, 19404, 9780, 1836, 2220, 8052, 21888, 1116, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 1116, 5124, 5124, 1116, 21888, 8052, 2220, 1836, 9780, 1116, 1116, 21888, 8052, 2220, 1836, 9780, 34116, 1116, 5124, 5124, 1116, 21888, 8052,
        2220, 1836, 9780, 1116, 1116, 1116, 21888, 8052, 2220, 1836, 9780, 53148, 1116, 1116, 1116, 1116, 1116, 5124, 5124, 1116, 21888, 8052, 2220, 1836, 9780, 21888, 8052, 2220, 1836, 9780, 72180, 5124, 1116, 34116, 9780, 1836, 2220, 8052, 21888, 1116, 1116, 9780, 1836, 2220, 8052, 21888,
        1116, 5124, 5124, 1116, 116292, 5484, 5484, 5484, 7596, 4896, 75708, 31548, 34116, 9780, 1836, 2220, 8052, 21888, 1116, 1116, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 2220, 8052, 21888, 2220, 2220, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 5124, 1116, 165600, 1116, 1116, 6588,
        22716, 68220, 9780, 1836, 2220, 8052, 21888, 2220, 2220, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 5124, 1116, 68220, 9780, 1836, 5124, 1116, 34116, 9780, 1836, 2220, 8052, 21888, 1116, 1116, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 5124, 1116, 44508, 9756, 9756, 8028, 16044,
        34116, 9780, 1836, 2220, 8052, 21888, 1116, 1116, 9780, 1836, 2220, 8052, 21888, 1116, 5124, 27084, 2736, 4896, 2736, 4896, 2736, 4896, 2736, 4896, 10116, 10116, 10116, 10116, 36588, 1932, 13560, 13560, 13560, 13560, 4356, 3636, 4716, 4536, 3456, 4716, 4716, 4716, 4716, 3456, 6156,
        22356, 4716, 10188, 5796, 5796, 5796, 5796, 176184, 25788, 2916, 25788, 2916, 25788, 2916, 9960, 1116, 1116, 1116, 1116, 6516, 6516, 6516, 6516, 6516, 6516, 37884, 37884, 25788, 2916, 23844, 23124, 23844, 23124, 25572, 25572, 25572, 25572, 23124, 22944, 22944, 23124, 3276, 3276,
        3276, 3276, 3276, 3276, 23100, 144648, 5124, 10236, 11472, 11472, 186084, 24660, 12372, 2196, 2196, 2196, 2196, 14040, 1836, 34836, 5076, 16788, 20556, 20556, 20556, 20556, 5076, 20556, 20556, 20556, 20556, 20556, 20556, 20556, 20556, 16788, 5076, 34836, 1836, 14040, 2196, 2196,
        2196, 2196, 12372, 24660, 27036, 27036, 27036, 27036, 22404, 30264, 137724, 89508, 44916, 20556, 20556, 20556, 20556, 16788, 5076, 34836, 1836, 14040, 2196, 2196, 2196, 2196, 12372, 24660, 20556, 20556, 20556, 20556, 5076, 9492, 4920, 9492, 4920, 18972, 23292, 13632, 60420, 34236,
        20556, 20556, 20556, 20556, 5076, 9492, 4920, 9492, 4920, 18972, 23292, 13632, 60420, 34236, 16788, 5076, 34836, 1836, 14040, 2196, 2196, 2196, 2196, 12372, 24660, 9240, 9240, 9240, 9240, 9240, 9240, 9240, 9240, 99432, 20556, 20556, 20556, 20556, 16788, 5076, 34836, 1836, 14040,
        2196, 2196, 2196, 2196, 12372, 24660, 7356, 12636, 12636, 184476, 20556, 20556, 20556, 20556, 16788, 5076, 34836, 1836, 14040, 2196, 2196, 2196, 2196, 12372, 24660, 12636, 49944, 49944, 29580, 29580, 20556, 20556, 20556, 20556, 16788, 5076, 34836, 1836, 14040, 2196, 2196, 2196, 2196,
        12372, 24660, 34848, 137364, 8052, 1656, 1656, 8052, 20556, 20556, 20556, 20556, 16788, 5076, 34836, 1836, 14040, 2196, 2196, 2196, 2196, 12372, 24660, 5796, 33972, 11916, 4044, 58008, 12456, 4044, 91308, 24660, 12372, 2196, 2196, 2196, 2196, 14040, 1836, 34836, 5076, 16788, 14040,
        1836, 34836, 5076, 16788, 20556, 20556, 20556, 20556, 10140, 10140, 10140, 10140, 3276, 3276, 143196, 5664, 5664, 5664, 5664, 5664, 5664, 5664, 5664, 2916, 8004, 39708, 116880, 24660, 12372, 2196, 2196, 2196, 2196, 123732, 123732, 22092, 22092, 22092, 179700, 128244, 306612, 127740,
        123348, 68004, 271224, 274872, 274872, 270756, 250020, 250380, 106440, 106440, 339900, 170556, 170556, 183804, 92472, 5796, 26976, 33132, 46044, 34092, 25644, 45036, 45036, 17136, 315756, 159888, 154788, 65316, 23508, 25512, 152976, 152976, 347724, 19992, 27576, 126120, 23340, 30204,
        30204, 9084, 9084, 9084, 9084, 9084, 25656, 78336, 18276, 6156, 12300, 7236, 8136, 5796, 5616, 5976, 5976, 7236, 8136, 15768, 22092, 23184, 23184, 35700, 8532, 23184, 5100, 5100, 25452, 26748, 80112, 14364, 18468, 36252, 36252, 3456, 7668, 51816, 168300, 43860, 33948, 108468, 108468,
        87300, 6360, 6360, 135156, 168300, 96432, 47328, 16920, 39984, 88140, 81252, 67260, 58344, 6636, 72108, 79668, 10140, 24540, 24540, 24540, 35340, 31428, 15084, 137628, 84952, 80616, 109836, 115692, 105084, 56532, 8004, 156432, 1296, 1296, 1476, 19044, 3300, 74712, 38736, 31848,
        36252, 29952, 156552, 1476, 15948, 6156, 6156, 25260, 19044, 77604, 34044, 290664, 6660, 5124, 5124, 1116, 19044, 198768, 2376, 2376, 2376, 2376, 756, 2916, 14796, 8652, 14796, 1656, 1656, 1656, 1656, 33588, 19920, 23568, 17292, 22272, 20388, 7260, 7260, 5436, 5436, 7284, 1116, 2196,
        2196, 2916, 2916, 2916, 2916, 7284, 1116, 2196, 2196, 2916, 2916, 2916, 2916, 1476, 5772, 15456, 15456, 15456, 15456, 17148, 15456, 15456, 15456, 19044, 109560, 117516, 29724, 197496, 12732, 2376, 7464, 2376, 1116, 1116, 1116, 1116, 8652, 8652, 197520, 74460, 218364, 17352, 18492,
        10296, 10296, 10296, 54324, 65244, 88092, 6924, 72372, 45516, 246660, 10176, 8328, 10296, 14952, 286056, 8496, 8496, 8496, 174420, 17352, 325404, 10116, 12096, 12096, 149640, 6876, 8316, 10176, 9252, 39528, 28752, 109668, 13776, 1836, 165780, 13800, 13800, 44508, 28752, 39588, 28884,
        38892, 13596, 8436, 6972, 9204, 16188, 31632, 5148, 88416, 5280, 25212, 28200, 28752, 189924, 33396, 1548, 3660, 31140, 42588, 27648, 29904, 175572, 14340, 4620, 190008, 110088, 25524, 5172, 37248, 5172, 25524, 5172, 37788, 5172, 31752, 18696, 45888, 53988, 31488, 32400, 7020, 2196,
        11820, 2196, 2196, 8436, 6972, 28752, 20424, 105036, 19212, 28236, 30540, 19500, 3636, 1836, 3636, 1836, 43068, 6876, 243684, 15372, 15372, 15372, 15372, 15372, 13836, 53976, 38412, 10188, 1116, 9216, 12456, 9756, 24000, 6876, 43068, 133980, 5124, 39084, 41676, 5124, 34092, 40788,
        7104, 1116, 2916, 2916, 2916, 2916, 7104, 1116, 2916, 2916, 2916, 2916, 5436, 6660, 43068, 69948, 24900, 3300, 3300, 9948, 5052, 5052, 3300, 36252, 3300, 4920, 23808, 14844, 17292, 14100, 19188, 15324, 7260, 7260, 7284, 1116, 2196, 2196, 2916, 2916, 2916, 2916, 7284, 1116, 2196,
        2196, 2916, 2916, 2916, 2916, 26772, 6900, 8004, 6900, 12708, 75156, 43068, 12660, 6900, 94368, 7284, 1116, 2196, 2196, 2916, 2916, 2916, 2916, 7284, 1116, 2196, 2196, 2916, 2916, 2916, 2916, 38988, 10752, 1836, 1116, 1116, 6876, 115392, 44508, 107508, 5124, 5436, 5124, 170292, 74460,
    }

    def positions(self) -> List[Float3]:
        raise Exception("Use vertex_data accessors")
        return self.vertex_buffers[0]

    def normals(self) -> List[Float3]:
        raise Exception("Use vertex_data accessors")
        return self.vertex_buffers[2]

    def uvs(self) -> List[Float2]:
        raise Exception("Use vertex_data accessors")
        return self.vertex_buffers[3]

    def triangles(self, group: int) -> List[Tuple[int, int, int]]:
        return self.triangle_buffers[group][1]

    def vertex_count(self) -> int:
        raise Exception("Use vertex_data accessors")
        return len(self.positions())

    def index_count(self, group: int = 0) -> int:
        return self.triangle_count(group) * 3

    def triangle_count(self, group: int = 0) -> int:
        return len(self.triangles(group))

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> MslcDataChunk:
        try:
            assert chunk.header.version in cls.VERSIONS, chunk.header.version
            assert len(chunk.raw_bytes) == chunk.header.size
            with BytesIO(chunk.raw_bytes) as stream:
                rsv0_a, flag, val, rsv0_b = cls.HEADER_LAYOUT.unpack_stream(stream)
                assert rsv0_a == 0
                assert rsv0_b == 0
                header = (flag, val)

                header_name_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                header_names = [cls.HEADER_NAME_LAYOUT.unpack_stream(stream) for _ in range(header_name_count)]
                # d = stream.read(4)
                # assert d == b'\x00\x00\x00\x00', d
                vertex_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                vertex_size_id = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                # try:
                # except:
                #     DEBUG_WRITE_TO_BIN(chunk.data)
                #     raise

                # TOO MANY
                #   Probably not aa
                V_SIZE_TABLE__aa = {
                    12: 32,
                    24: 32,
                    36: 32,
                    148: 32,
                    # 26: 32, # FAILS ON 'DXP2Data\data\art\fx\guard_bit_1.whm'
                    26: 48,
                    33: 48,
                    18: 48,
                    204: 32,
                    158: 32,
                    115: 32,
                    187: 32,
                    132: 32,
                    30: 32,
                    176: 32,
                    22: 32,
                    1818: 32,
                    180: 48
                }
                V_SIZE_TABLE__ab = {
                    37: 32,
                    39: 48,
                }
                V_SIZE_TABLE = V_SIZE_TABLE__ab
                V_SIZE_KEY = vertex_size_id
                V_SIZE = V_SIZE_TABLE[V_SIZE_KEY]

                _debug_V_BUFFER_START = stream.tell()

                _debug_vbuffer_fullsize = vertex_count * V_SIZE
                vertex_data = MslcVertexData.unpack(stream, vertex_count, V_SIZE)
                e = stream.read(4)
                assert e == b'\x00\x00\x00\x00', e
                index_buffer_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                index_buffers = []
                _debug_ibuffer_fullsize = 0
                for _ in range(index_buffer_count):
                    # index_trailing_a = stream.read(4)
                    # index_trailing_b = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                    # assert index_trailing_a == 0, index_trailing_a
                    # assert trailing[0] == 0 and trailing[2] == 0 and trailing[3] == 0, (trailing, (0, vertex_count, 0, 0))
                    # assert trailing[0] != 0 and sum(trailing) == vertex_count, (trailing, vertex_count)
                    ibuffer = (name, indexes, trailing)
                    index_buffers.append(ibuffer)
                    _debug_ibuffer_fullsize += len(name) + cls.NAME_LAYOUT.min_size + cls.COUNT_LAYOUT.size + cls.INDEX_TRI_LAYOUT.size * int(tri_count)

                # print(as_hex_adr(stream.tell()))
                # ad_size = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                # ad = []
                # # ad = stream.read(ad_size)
                # # assert len(ad) == ad_size, (ad_size, ad)
                # for _ in range(ad_size):
                #     ae_size = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                #     ae = stream.read(ae_size)
                #     assert len(ae) == ae_size, (ae_size, ae)
                #     # af_size = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                #     # af = stream.read(af_size)
                #     # assert len(af) == af_size, (af_size, af)
                # af = None
                # if ad_size == 0: #
                #     ae, af = stream.read(4),stream.read(4)

                baked_textures_maybe = stream.read()
                # assert len(baked_textures_maybe) == 0

                # assert excess == b'\x00\x00\x00\x00\x00\x00\x00\x00', excess
                # assert len(excess) == cls.EXCESS_SIZE, (cls.EXCESS_SIZE, excess)

            # _ = _debug_V_BUFFER_START
            # _ = _debug_vbuffer_fullsize
            # _ = _debug_ibuffer_fullsize
            # assert stream.tell() == len(chunk.data), (stream.tell(), len(chunk.data))
            # assert len(chunk.data) == 61, len(chunk.data) # TODO
            # GATHERING SIZES TO GET A BETTER UNDERSTANDING
            #   By extraching common factors (ignoring 12, since it doesn't fit the pattern), we might be able to see the 'size' of the fixed portion of whatever this is
            #       Or atleast get closer to finding out where/what size is  #TODO make sure the assertion is only for debugging

            # bake_textures_maybe is roughly 90*header[1]
            #   This isnt concrete evidence, but since most factors of the tex sizes resolve to a large prime, I'm thinking it's either variable data, or a variable size is defined elsewhere
            # try:
            #     # assert len(baked_textures_maybe) == 12 or \
            #     assert len(baked_textures_maybe) // header[1] == 90, (len(baked_textures_maybe), len(baked_textures_maybe) // header[1])
            # except:
            #     raise
            # try:
            # UNK2TEX = cls.UNK2TEX
            # pair = ((header[0],header[1],vertex_size_id),len(baked_textures_maybe))
            # try:
            #     assert pair[0] in UNK2TEX and UNK2TEX[pair[0]] == pair[1]
            # # assert len(baked_textures_maybe) == 12 or len(baked_textures_maybe) in cls.TEX_SIZES, len(baked_textures_maybe)
            # except:
            #     cls._EX.append(pair)
            #     print("\n"+", ".join('( '+str(_[0][0])+", "+str(_[0][1])+", "+str(_[0][2])+"):"+str(_[1]) for _ in cls._EX)+"\n")
            #     pass
            return cls(chunk.header, header, (vertex_size_id,), header_names, vertex_data, index_buffers, baked_textures_maybe)
        except Exception as e:
            # print(as_hex_adr(stream.tell()))
            # _ = None
            # DEBUG_WRITE_TO_BIN(chunk.data) #
            raise
    # sub_header: MsclHeader
    # names: List[MslcName]
    # blocks: List[MslcBlock]
    #
    # # Mesh data I believe
    # @classmethod
    # def convert(cls, chunk: GenericDataChunk) -> MslcDataChunk:
    #
    #     # VERSIONED
    #     assert chunk.header.version in [2], chunk.header.version
    #
    #     with BytesIO(chunk.data) as stream:
    #         sub_header = MsclHeader.unpack(stream)
    #         names = [MslcName.unpack(stream) for _ in range(sub_header.name_count)]
    #         blocks = []
    #         while has_data(stream):
    #             block = MslcBlockUtil.unpack(stream)
    #             blocks.append(block)
    #         return MslcDataChunk(chunk.header, sub_header, names, blocks)


# IDK, its names but the layout seems to vary BUT NOT BY VERSION
# @dataclass
# class MsgrDataChunk(AbstractChunk):
# COUNT = Struct("<L")
# EXPECTED_VERSION = 1
#
# names: List[MsgrName]
#
# @classmethod
# def convert(cls, chunk: GenericDataChunk) -> MsgrDataChunk:
#     assert chunk.header.version == cls.EXPECTED_VERSION
#     with BytesIO(chunk.data) as stream:
#         count = cls.COUNT.unpack_stream(stream)[0]
#         parts = []
#         for _ in range(count):
#             p = MsgrName.unpack(stream)  # [0].decode("ascii")
#             parts.append(p)
#         # parts = [MsgrName.unpack(stream) for _ in range(count)]
#     return cls(chunk.header, parts)


@dataclass
class BvolChunk(AbstractChunk):
    CHUNK_ID = "BVOL"
    CHUNK_TYPE = ChunkType.Data
    LAYOUT = Struct("<b 12s 12f")

    unk: bytes

    matrix: Tuple[Float4, Float4, Float4]

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> BvolChunk:
        # TODO, this chunk is wierd; it makes sense to have a TRS matrix and then maybe some ints for size, BUT
        #       Not a 4x4 matrix (physically not enough data; 64 bytes min)
        #       Not an even nummer of bytes; (61?) meaning theres a flag byte of some kind
        #       Size could be 3 ints (XYZ) but why not store in TRS?
        assert len(chunk.raw_bytes) == chunk.header.size
        assert len(chunk.raw_bytes) == cls.LAYOUT.size, (len(chunk.raw_bytes), cls.LAYOUT.size)
        flag, unks, m00, m01, m02, m03, m10, m11, m12, m13, m20, m21, m22, m23 = cls.LAYOUT.unpack(chunk.raw_bytes)
        assert flag == 1, flag
        m = ((m00, m01, m02, m03), (m10, m11, m12, m13), (m20, m21, m22, m23))
        return BvolChunk(chunk.header, unks, m)


@dataclass
class CamsChunk(UnimplementedDataChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "CAMS"


@dataclass
class MslcChunk(AbstractChunk):
    CHUNK_ID = "MSLC"
    CHUNK_TYPE = ChunkType.Folder
    VERSIONS = [1]

    data: MslcDataChunk
    bvol: BvolChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MslcChunk:
        # VERSIONED
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = MslcChunkConverter.convert_many(chunk.chunks)
        coll = ChunkCollectionX.list2col(converted)
        data = coll.find(MslcDataChunk)
        bvol = coll.find(BvolChunk)
        assert len(chunk.chunks) == 2
        return MslcChunk(chunk.header, data, bvol)


@dataclass
class MsgrDataChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "DATA"
    LEN_LAYOUT = Struct("i")
    VERSIONS = [1]

    @dataclass
    class Item:
        LAYOUT = VStruct("2vi")
        name: str
        path: str
        unk: int

        @classmethod
        def unpack_stream(cls, stream: BinaryIO) -> MsgrDataChunk.Item:
            name, path, unk = cls.LAYOUT.unpack_stream(stream)
            name = name.decode("ascii")
            path = path.decode("ascii")
            return cls(name, path, unk)

    items: List[Item]

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> MsgrDataChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        with BytesIO(chunk.raw_bytes) as stream:
            try:
                count = cls.LEN_LAYOUT.unpack_stream(stream)[0]
                items = [MsgrDataChunk.Item.unpack_stream(stream) for _ in range(count)]
            except:
                print()
                print(chunk.raw_bytes)
                print()
                raise

        tot = sum([len(i.name) for i in items])
        assert cls.LEN_LAYOUT.size + cls.Item.LAYOUT.min_size * count + tot
        return cls(chunk.header, items)
        # unka, name, unkb, unkc = cls.LEN_LAYOUT.unpack(chunk.data)
        # assert len(chunk.data) == cls.LENLAYOUT.min_size + len(name), chunk.data
        # return cls(chunk.header, name, (unka, unkb, unkc))


@dataclass
class MsgrChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MSGR"

    mslc: List[MslcChunk]
    data: MsgrDataChunk
    bvol: BvolChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MsgrChunk:
        # VERSIONED
        assert chunk.header.version in [1], chunk.header.version
        converted = MsgrChunkConverter.convert_many(chunk.chunks)
        coll = ChunkCollectionX.list2col(converted)
        mslc = coll.find(MslcChunk, True)
        data = coll.find(MsgrDataChunk)
        bvol = coll.find(BvolChunk)
        #
        # mslc = find_chunks(chunk.chunks, "MSLC", ChunkType.Folder)
        # mslc = [MslcChunk.convert(_) for _ in mslc]
        #
        # data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        #
        # bvol = find_chunk(chunk.chunks, "BVOL", ChunkType.Data)
        # bvol = BvolChunk.convert(bvol)

        assert len(chunk.chunks) == sum([1 if _ else 0 for _ in [data, bvol]]) + len(mslc)
        return MsgrChunk(chunk.header, mslc, data, bvol)


@dataclass
class MarkChunk(UnimplementedDataChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "MARK"


@dataclass
class AnbvChunk(UnimplementedDataChunk):
    CHUNK_ID = "ANBV"
    CHUNK_TYPE = ChunkType.Data


@dataclass
class AnimDataChunk(UnimplementedDataChunk):
    CHUNK_ID = "DATA"
    CHUNK_TYPE = ChunkType.Data


@dataclass
class AnimChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "ANIM"
    VERSIONS = [3]

    data: AnimDataChunk
    anbv: AnbvChunk

    # anim: Optional[AnimChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> AnimChunk:
        # VERSIONED
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = AnimChunkConverter.convert_many(chunk.chunks)
        coll = ChunkCollectionX.list2col(converted)
        data = coll.find(AnimDataChunk)
        anbv = coll.find(AnbvChunk)

        assert len(chunk.chunks) == 2
        return AnimChunk(chunk.header, data, anbv)  # , anim)


@dataclass
class RsgmChunk(AbstractChunk):
    CHUNK_ID = "RSGM"
    CHUNK_TYPE = ChunkType.Folder


@dataclass
class RsgmChunkV1(UnimplementedFolderChunk):
    VERSION = 1

    # @classmethod
    # def convert(cls, chunk:FolderChunk) -> RsgmChunkV1:
    #     raise NotImplementedError


@dataclass
class RsgmChunkV3(RsgmChunk):
    VERSION = 3

    anim: List[AnimChunk]
    txtr: List[TxtrChunk]
    shdr: List[FolderChunk]
    sshr: List[SshrChunk]
    msgr: MsgrChunk
    skel: Optional[SkelChunk]
    mark: MarkChunk
    cams: CamsChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> RsgmChunkV3:
        converted = WhmChunkConverter.convert_many(chunk.chunks)
        col = ChunkCollectionX.list2col(converted)

        anim = col.find(AnimChunk, True)
        txtr = col.find(TxtrChunk, True)
        shdr = col.find(ShdrChunk, True)
        sshr = col.find(SshrChunk, True)

        msgr = col.find(MsgrChunk)
        skel = col.find(SkelChunk)
        mark = col.find(MarkChunk)
        cams = col.find(CamsChunk)

        count = sum([1 if _ else 0 for _ in [msgr, skel, mark, cams]]) + len(txtr) + len(shdr) + len(anim) + len(sshr)
        assert len(
            chunk.chunks) == count  # , (chunk.header, count, ", ".join([_.header.type.value[0] + ":" + _.header.id for _ in [sshr, msgr, skel, mark, cams] if _ is not None]), ", ".join([(_.header.type.value[0] + ":" + _.header.id) for _ in chunk.chunks if _.header.id not in ["TXTR", "SHDR", "ANIM"]]))
        # assert len(chunk.chunks) == _count(*args), (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks])
        return RsgmChunkV3(chunk.header, anim, txtr, shdr, sshr, msgr, skel, mark, cams)


@dataclass
class ShdrInfoChunk(UnimplementedDataChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "INFO"


@dataclass
class ShdrChanChunk(UnimplementedDataChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "CHAN"


@dataclass
class ShdrChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "SHDR"
    VERSIONS = [1]
    info: ShdrInfoChunk
    chan: List[ShdrChanChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ShdrChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = WhmChunkConverter.convert_many(chunk.chunks)
        coll = ChunkCollectionX.list2col(converted)
        info = coll.find(ShdrInfoChunk)
        chan = coll.find(ShdrChanChunk, True)
        assert len(chunk.chunks) == 1 + len(chan)
        return cls(chunk.header, info, chan)


@dataclass
class RsgmChunkFactory:
    CHUNK_ID = "RSGM"
    CHUNK_TYPE = ChunkType.Folder
    __MAP = {
        # RsgmChunkV1.VERSION: RsgmChunkV1,
        RsgmChunkV3.VERSION: RsgmChunkV3,
    }
    VERSIONS = [k for k in __MAP.keys()]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> RsgmChunk:
        # VERSIONED
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls.__MAP[chunk.header.version].convert(chunk)


@dataclass
class SkelTransform:  # THE BIGGEST MISTAKE! Assuming that these had to be bones. They are transforms that match
    name: str
    parent_index: int

    # Original coordinate system
    pos: Float3
    quaternion: Float4

    LAYOUT = VStruct("v <l 3f 4f")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> SkelTransform:
        name, parent, px, py, pz, rx, ry, rz, rw = cls.LAYOUT.unpack_stream(stream)
        name = name.decode("ascii")
        p = (px, py, pz)
        q = (rx, ry, rz, rw)
        return SkelTransform(name, parent, p, q)


@dataclass
class SkelChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "SKEL"

    LAYOUT = Struct("< l")
    transforms: List[SkelTransform]

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> SkelChunk:
        with BytesIO(chunk.raw_bytes) as stream:
            bone_count = cls.LAYOUT.unpack_stream(stream)[0]
            bones = [SkelTransform.unpack(stream) for _ in range(bone_count)]
            assert stream.tell() == len(chunk.raw_bytes), (len(chunk.raw_bytes), stream.tell())
            return SkelChunk(chunk.header, bones)


@dataclass
class WhmChunky(RelicChunky):
    VERSIONS = [ChunkyVersion.v0101]
    fbif: FbifChunk
    rsgm: RsgmChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> WhmChunky:
        # VERSIONED
        assert chunky.header.version in cls.VERSIONS, chunky.header.version
        converted = WhmChunkConverter.convert_many(chunky.chunks)
        x = ChunkCollectionX.list2col(converted)
        fbif = x.find(FbifChunk)
        rsgm = x.find(RsgmChunk)
        assert len(chunky.chunks) == 2
        return cls(chunky.header, fbif, rsgm)


def add_mslc_chunk_converter(conv):
    conv.register(MslcDataChunk)
    conv.register(BvolChunk)
    return conv


def generate_mslc_chunk_converter():
    conv = ChunkConverterFactory()
    add_mslc_chunk_converter(conv)
    return conv


def add_msgr_chunk_converter(conv):
    conv.register(MslcChunk)
    conv.register(MsgrDataChunk)
    conv.register(BvolChunk)
    return conv


def generate_msgr_chunk_converter():
    conv = ChunkConverterFactory()
    add_msgr_chunk_converter(conv)
    return conv


def add_anim_chunk_converter(conv):
    conv.register(AnimDataChunk)
    conv.register(AnbvChunk)
    return conv


def generate_anim_chunk_converter():
    conv = ChunkConverterFactory()
    add_anim_chunk_converter(conv)
    return conv


def add_whm_chunk_converter(conv: ChunkConverterFactory):
    conv.register(FbifChunk)
    conv.register(RsgmChunkFactory)
    conv.register(TxtrChunk)
    conv.register(ShdrChunk)
    conv.register(ShdrInfoChunk)
    conv.register(ShdrChanChunk)
    conv.register(MsgrChunk)
    conv.register(SkelChunk)
    conv.register(SshrChunk)
    conv.register(MarkChunk)
    conv.register(CamsChunk)
    conv.register(MslcChunk)
    conv.register(AnimChunk)


def generate_whm_chunk_converter():
    conv = ChunkConverterFactory()
    add_whm_chunk_converter(conv)
    return conv


# Individual converters are used to allow differing Chunkies to substitute their own Chunks
AnimChunkConverter = generate_anim_chunk_converter()
MslcChunkConverter = generate_mslc_chunk_converter()
MsgrChunkConverter = generate_msgr_chunk_converter()
WhmChunkConverter = generate_whm_chunk_converter()
