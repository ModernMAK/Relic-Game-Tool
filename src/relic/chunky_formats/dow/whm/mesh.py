from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, List, Optional, Tuple, Any

from serialization_tools.ioutil import has_data
from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct

from relic.chunky import AbstractChunk, ChunkType, GenericDataChunk, FolderChunk
from relic.chunky_formats.convertable import ChunkConverterFactory
from relic.chunky_formats.dow.whm.shared import Short4, BvolChunk, Byte4
from relic.chunky_formats.util import ChunkCollectionX
from relic.file_formats.mesh_io import Float3, Float2, Short3


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


@dataclass
class MslcVertexData:
    VERTEX_POS_LAYOUT = Struct("< 3f")
    VERTEX_NORM_LAYOUT = Struct("< 3f")
    VERTEX_UV_LAYOUT = Struct("< 2f")
    VERTEX_BONE_WEIGHT_LAYOUT = Struct("< 3f 4B")

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
            bone_buffer = [((w1, w2, w3), (b1, b2, b3, b4)) for w1, w2, w3, b1, b2, b3, b4 in bone_buffer]
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

    @property
    def index_count(self) -> int:
        return self.triangle_count * 3

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)


@dataclass
class MslcBoneInfo:
    LAYOUT = VStruct("vi")
    name: str
    index: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> MslcBoneInfo:
        name, index = cls.LAYOUT.unpack_stream(stream)
        name = name.decode("ascii")
        return cls(name, index)


@dataclass
class MslcDataChunk(AbstractChunk):
    CHUNK_ID = "DATA"
    CHUNK_TYPE = ChunkType.Data
    VERSIONS = [2]
    # data: bytes

    COUNT_LAYOUT = Struct("i")
    NAME_LAYOUT = VStruct("v")
    # VERTEX_LAYOUT = Struct("32s")
    # EXCESS_SIZE = 8

    HEADER_LAYOUT = Struct("< i b 4s i")

    sub_header: Tuple[Any, ...]
    unks: Tuple[Any, ...]
    bones: List[MslcBoneInfo]
    vertex_data: MslcVertexData
    sub_meshes: List[MslcSubmeshData]
    unk_a: List[bytes]
    unk_b: List[bytes]
    unk_c: List[bytes]

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
                bone_info_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                bones = [MslcBoneInfo.unpack(stream) for _ in range(bone_info_count)]

                vertex_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                vertex_size_id = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                V_SIZE_TABLE = {
                    37: 32,
                    39: 48,
                }
                V_SIZE = V_SIZE_TABLE[vertex_size_id]

                _debug_V_BUFFER_START = stream.tell()

                _debug_vbuffer_fullsize = vertex_count * V_SIZE
                vertex_data = MslcVertexData.unpack(stream, vertex_count, V_SIZE)
                e = stream.read(4)
                assert e == b'\x00\x00\x00\x00', e
                index_buffer_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                index_buffers = []
                _debug_ibuffer_fullsize = 0
                for _ in range(index_buffer_count):
                    sub_mesh = MslcSubmeshData.unpack(stream)
                    index_buffers.append(sub_mesh)

                aaa = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                aaa_data = [stream.read(12) for _ in range(aaa)]
                aab = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                aab_data = [stream.read(24) for _ in range(aab)]
                aac = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                aac_data = [stream.read(40) for _ in range(aac)]
                assert not has_data(stream), stream.read()

            return cls(chunk.header, header, (vertex_size_id,), bones, vertex_data, index_buffers, aaa_data, aab_data, aac_data)
        except Exception as e:
            raise


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


def add_mslc_chunk_converter(conv):
    conv.register(MslcDataChunk)
    conv.register(BvolChunk)
    return conv


def generate_mslc_chunk_converter():
    conv = ChunkConverterFactory()
    add_mslc_chunk_converter(conv)
    return conv


MslcChunkConverter = generate_mslc_chunk_converter()
