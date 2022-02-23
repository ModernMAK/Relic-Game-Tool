from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Tuple, Any
from typing import List, Optional

from archive_tools.ioutil import as_hex_adr
from archive_tools.structx import Struct
from archive_tools.vstruct import VStruct

from ..common_chunks.fbif import FbifChunk
from ..common_chunks.imag import TxtrChunk
from ..convertable import UnimplementedDataChunk, ChunkConverterFactory, ChunkCollectionX, UnimplementedFolderChunk, DEBUG_WRITE_TO_BIN
from ...chunky import ChunkyVersion
from ...chunky.chunk.chunk import GenericDataChunk, FolderChunk, AbstractChunk
from ...chunky.chunk.header import ChunkType
from ...chunky.chunky.chunky import RelicChunky, GenericRelicChunky
from ...file_formats.mesh_io import Float3, Float4


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

        with BytesIO(chunk.data) as stream:
            name = cls.LAYOUT.unpack_stream(stream)[0]
            name = name.decode("ascii")
            assert len(chunk.data) == len(name) + cls.LAYOUT.min_size
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


@dataclass
class MslcDataChunk(AbstractChunk):
    CHUNK_ID = "DATA"
    CHUNK_TYPE = ChunkType.Data
    VERSIONS = [2]
    # data: bytes

    COUNT_LAYOUT = Struct("i")
    NAME_LAYOUT = VStruct("v")
    HEADER_NAME_LAYOUT = VStruct("vi")
    INDEX_LAYOUT = Struct("H")
    INDEX_TRI_LAYOUT = Struct("3H")
    # VERTEX_LAYOUT = Struct("32s")
    EXCESS_SIZE = 8
    VERTEX_POS_LAYOUT = Struct("< 3f")
    VERTEX_NORM_LAYOUT = Struct("< 3f")
    VERTEX_UV_LAYOUT = Struct("< 2f")
    VERTEX_UNK_LAYOUT = Struct("< 3f 4s")

    unks: Tuple[Any, ...]
    header_names: List[Tuple[str, int]]
    vertex_buffers: Tuple[bytes, ...]
    triangle_buffers: List[Tuple[str, List[int]]]
    trailing_data: bytes  # LIKELY EMBEDDED TEXTURES, No magic so TGA? Or relic's wierd no-magic DDS

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> MslcDataChunk:
        try:
            assert chunk.header.version in cls.VERSIONS, chunk.header.version
            with BytesIO(chunk.data) as stream:
                a = stream.read(4)
                assert a == b'\x00\x00\x00\x00', a
                ac = stream.read(1)
                aa = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                c = stream.read(4)
                assert c == b'\x00\x00\x00\x00', c
                header_name_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                header_names = [cls.HEADER_NAME_LAYOUT.unpack_stream(stream) for _ in range(header_name_count)]
                # d = stream.read(4)
                # assert d == b'\x00\x00\x00\x00', d
                vertex_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                ab = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
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
                V_SIZE_KEY = ab
                V_SIZE = V_SIZE_TABLE[V_SIZE_KEY]

                if V_SIZE in [32, 48]:
                    position_buffer = [cls.VERTEX_POS_LAYOUT.unpack_stream(stream) for _ in range(vertex_count)]
                else:
                    position_buffer = None

                if V_SIZE in [48]:
                    unk_buffer = [cls.VERTEX_UNK_LAYOUT.unpack_stream(stream) for _ in range(vertex_count)]
                else:
                    unk_buffer = None

                if V_SIZE in [32, 48]:
                    normal_buffer = [cls.VERTEX_NORM_LAYOUT.unpack_stream(stream) for _ in range(vertex_count)]
                else:
                    normal_buffer = None

                if V_SIZE in [32, 48]:
                    uv_buffer = [cls.VERTEX_UV_LAYOUT.unpack_stream(stream) for _ in range(vertex_count)]
                else:
                    uv_buffer = None

                vertex_buffer = (position_buffer, unk_buffer, normal_buffer, uv_buffer)

                e = stream.read(4)
                assert e == b'\x00\x00\x00\x00', e
                index_buffer_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                index_buffers = []
                for _ in range(index_buffer_count):
                    name = cls.NAME_LAYOUT.unpack_stream(stream)[0]
                    index_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                    tri_count = index_count / cls.INDEX_TRI_LAYOUT.args
                    assert int(tri_count) == tri_count
                    indexes = [cls.INDEX_TRI_LAYOUT.unpack_stream(stream) for _ in range(int(tri_count))]
                    index_trailing_a = cls.COUNT_LAYOUT.unpack_stream(stream)
                    index_trailing_b = cls.COUNT_LAYOUT.unpack_stream(stream)
                    ibuffer = (name, indexes, (index_trailing_a, index_trailing_b))
                    index_buffers.append(ibuffer)

                # print(as_hex_adr(stream.tell()))
                ad_size = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                ad = stream.read(ad_size)
                assert len(ad) == ad_size, (ad_size, ad)

                baked_textures_maybe = stream.read()

                # assert excess == b'\x00\x00\x00\x00\x00\x00\x00\x00', excess
                # assert len(excess) == cls.EXCESS_SIZE, (cls.EXCESS_SIZE, excess)

                # assert stream.tell() == len(chunk.data), (stream.tell(), len(chunk.data))
            # assert len(chunk.data) == 61, len(chunk.data) # TODO
            return cls(chunk.header, (ac, aa, ab), header_names, vertex_buffer, index_buffers, baked_textures_maybe)
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
        assert len(chunk.data) == chunk.header.size
        assert len(chunk.data) == cls.LAYOUT.size, (len(chunk.data), cls.LAYOUT.size)
        flag, unks, m00, m01, m02, m03, m10, m11, m12, m13, m20, m21, m22, m23 = cls.LAYOUT.unpack(chunk.data)
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
    REP_LAYOUT = VStruct("2vi")
    VERSIONS = [1]

    items: List[Tuple[str, str, int]]

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> MsgrDataChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        with BytesIO(chunk.data) as stream:
            try:
                count = cls.LEN_LAYOUT.unpack_stream(stream)[0]
                items = []
                for _ in range(count):
                    name, path, unk = cls.REP_LAYOUT.unpack_stream(stream)
                    item = (name, path, unk)
                    items.append(item)
            except:
                print()
                print(chunk.data)
                print()
                raise

        tot = sum([len(n) for n, _, _ in items])
        assert cls.LEN_LAYOUT.size + cls.REP_LAYOUT.min_size * count + tot
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
        RsgmChunkV1.VERSION: RsgmChunkV1,
        RsgmChunkV3.VERSION: RsgmChunkV3,
    }
    VERSIONS = [k for k in __MAP.keys()]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> RsgmChunk:
        # VERSIONED
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        return cls.__MAP[chunk.header.version].convert(chunk)


@dataclass
class SkelBone:
    name: str
    parent_index: int

    # Original coordinate system
    pos: Float3
    quaternion: Float4

    LAYOUT = VStruct("v <l3f4f")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> SkelBone:
        name, parent, px, py, pz, rx, ry, rz, rw = cls.LAYOUT.unpack_stream(stream)
        name = name.decode("ascii")
        p = (px, py, pz)
        q = (rx, ry, rz, rw)
        return SkelBone(name, parent, p, q)


@dataclass
class SkelChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "SKEL"

    LAYOUT = Struct("<l")
    # This chunk is super easy
    bones: List[SkelBone]

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> SkelChunk:
        with BytesIO(chunk.data) as stream:
            bone_count = cls.LAYOUT.unpack_stream(stream)[0]
            bones = [SkelBone.unpack(stream) for _ in range(bone_count)]
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
