from __future__ import annotations

import enum
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import BinaryIO, Union, Tuple
from typing import List, Optional

from archive_tools.ioutil import has_data, iter_read
from archive_tools.structx import Struct
from archive_tools.vstruct import VStruct

from .skel import SkelChunk
from ..common_chunks.fbif import FbifChunk
from ..common_chunks.imag import TxtrChunk
from ..convertable import find_chunk, find_chunks, ConvertableChunky
from ...chunky.chunk.chunk import GenericDataChunk, FolderChunk, AbstractChunk
from ...chunky.chunk.header import ChunkType
from ...chunky.chunky.chunky import RelicChunky, GenericRelicChunky
from ...file_formats.mesh_io import Float2, Float3


def _count(*args) -> int:
    c = 0
    for a in args:
        if a is None:
            continue
        if isinstance(a, list):
            c += len(a)
        else:
            c += 1
    return c


@dataclass
class SshrChunk(AbstractChunk):
    LAYOUT = VStruct("v")
    name: str

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> SshrChunk:
        with BytesIO(chunk.data) as stream:
            name = cls.LAYOUT.unpack_stream(stream)[0]
            name = name.decode("ascii")
            return SshrChunk(chunk.header, name)


@dataclass
class MsclHeader:
    # reserved_zero_a: int

    flag: bytes
    val: int
    # reserved_zero_b: int
    name_count: int

    LAYOUT = Struct("< l b l 2l")

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
        return MslcName(name, unk)


#
#
class MslcBlockFormat(Enum):
    Vertex32 = enum.auto()  # = 37
    Vertex48 = enum.auto()  # = 39

    # Oh, boy; IDK how many 'texture' classes there are but there are enough
    Texture = enum.auto()

    @classmethod
    def from_code(cls, code: int):
        if code <= 6:
            return MslcBlockFormat.Texture

        lookup = {
            37: MslcBlockFormat.Vertex32,
            39: MslcBlockFormat.Vertex48,
        }
        value = lookup.get(code)
        if value:
            return value
        raise KeyError(code)

    def vertex_buffer_size(self) -> int:
        size = {
            MslcBlockFormat.Vertex48: 48,
            MslcBlockFormat.Vertex32: 32,
        }
        val = size.get(self)
        if val is None:
            raise KeyError(f"'{val}' is not a Vertex Buffer Type")
        return val

    def to_code(self) -> int:

        lookup = {
            MslcBlockFormat.Vertex32: 37,
            MslcBlockFormat.Vertex48: 39,
        }
        return lookup[self.value]


#
#
@dataclass
class VertexMsclBlock:
    format: MslcBlockFormat
    count: int
    vertex_buffer: bytes
    _code: int = 0


@dataclass
class Vertex32MsclBlock:
    LAYOUT = Struct("< 3f 3f 2f")  # Float3, Float3, Float2
    vertexes: List[Tuple[Float3, Float3, Float2]]

    @property
    def format(self) -> MslcBlockFormat:
        return MslcBlockFormat.Vertex32

    @property
    def format_code(self) -> int:
        return self.format.to_code()

    @classmethod
    def convert(cls, stream: BinaryIO, count):
        vertex_list: List[Tuple[Float3, Float3, Float2]] = []
        for i, buffer in enumerate(iter_read(stream, cls.LAYOUT.size)):
            if i == count:
                break
            args = cls.LAYOUT.unpack(buffer)
            pos: Float3 = args[0:3]
            norm: Float3 = args[3:6]
            uv: Float2 = args[6:8]
            vert = (pos, norm, uv)
            vertex_list.append(vert)
        return Vertex32MsclBlock(vertex_list)


#
@dataclass
class TextureMsclSubBlock:
    name: str
    count: int
    index_buffer: bytes
    zero: int


@dataclass
class TextureMsclBlock:
    format: MslcBlockFormat
    zero: int
    blocks: List[TextureMsclSubBlock]
    info: List[Tuple[int, int]]

    unk_a: int
    unk_b: int
    unk_c: int
    _code: int = 0


MslcBlock = Union[VertexMsclBlock, TextureMsclBlock]


#
#
class MslcBlockUtil:
    LAYOUT = Struct("< 2L")
    INFO = Struct("< 2l")
    UNK = Struct("< 3l")
    INDEX_BLOCK_LAYOUT = VStruct("vl")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> MslcBlock:
        def read_index_block() -> TextureMsclSubBlock:
            name, index_count = cls.INDEX_BLOCK_LAYOUT.unpack_stream(stream)
            name = name.decode("ascii")
            i_buffer = stream.read(index_count * 2)  # index is a short
            return TextureMsclSubBlock(name, index_count, i_buffer, count)

        # Code currently has a lot of 'garbage values'
        #   But '5', '3', '2', '39', '37', '1', '6', look the least garbagey and the most common.
        #       All those numbers occur at least 9+ times; 39, 37 & 1 occur at least 3000 times

        count, code = cls.LAYOUT.unpack_stream(stream)
        f = MslcBlockFormat.from_code(code)
        if f == MslcBlockFormat.Texture:
            texture_count = code
            subs = []
            infos = []
            for _ in range(texture_count):
                sub = read_index_block()

                info = cls.INFO.unpack_stream(stream)

                subs.append(sub)
                infos.append(info)

            unks = cls.UNK.unpack_stream(stream)

            return TextureMsclBlock(f, count, subs, infos, *unks, code)

        try:
            # if f == MslcBlockFormat.Vertex32:
            #     return Vertex32MsclBlock.convert(stream, count)
            buffer_size = f.vertex_buffer_size()
            v_buffer = stream.read(buffer_size * count)
            return VertexMsclBlock(f, count, v_buffer, code)
        except KeyError:
            pass

        raise NotImplementedError(code)


# @dataclass
# class MslcChunk(AbstractChunk):
#     sub_header: MsclHeader
#     names: List[MslcName]
#     blocks: List[MslcBlock]
#
#     EXPECTED_VERSION = 2
#
#     @classmethod
#     def create(cls, chunk: FolderChunk) -> 'MslcChunk':
#         # noinspection PyTypeChecker
#         data: GenericDataChunk = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
#         # WHM's data.header.version always '2'
#         assert data.header.version == cls.EXPECTED_VERSION
#         with BytesIO(data.data) as stream:
#             sub_header = MsclHeader.unpack(stream)
#             names = [MslcName.unpack(stream) for _ in range(sub_header.name_count)]
#             blocks = []
#             start = stream.tell()
#             stream.seek(0, 2)
#             end = stream.tell()
#             stream.seek(start)
#
#             while stream.tell() != end:
#                 block = MslcBlockUtil.unpack(stream)
#                 blocks.append(block)
#             return MslcChunk(chunk.header, sub_header, names, blocks)
#

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
    sub_header: MsclHeader
    names: List[MslcName]
    blocks: List[MslcBlock]

    EXPECTED_VERSION = 2

    # Mesh data I believe
    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> MslcDataChunk:
        # WHM's data.header.version always '2'
        assert chunk.header.version == cls.EXPECTED_VERSION
        with BytesIO(chunk.data) as stream:
            sub_header = MsclHeader.unpack(stream)
            names = [MslcName.unpack(stream) for _ in range(sub_header.name_count)]
            blocks = []
            while has_data(stream):
                block = MslcBlockUtil.unpack(stream)
                blocks.append(block)
            return MslcDataChunk(chunk.header, sub_header, names, blocks)


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
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> BvolChunk:
        return BvolChunk(chunk.header, chunk.data)


@dataclass
class MslcChunk(AbstractChunk):
    data: MslcDataChunk
    bvol: BvolChunk

    # mark: List[MarkChunk]
    # sub_meshes: List[MslcChunk]
    # anim: List[AnimChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MslcChunk:
        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        data = MslcDataChunk.convert(data)
        # data = [MslcDataChunk.convert(d) for d in data]
        #
        bvol = find_chunk(chunk.chunks, "BVOL", ChunkType.Data)
        bvol = BvolChunk.convert(bvol)
        # bvol = [BvolChunk.convert(b) for b in bvol]
        #
        # mark = find_chunks(chunk.chunks, "MARK", ChunkType.Data)
        # mark = [MarkChunk.convert(m) for m in mark]
        #
        # mslc = find_chunks(chunk.chunks, "MSLC", ChunkType.Folder)
        # mslc = [MslcChunk.convert(sub_mesh) for sub_mesh in mslc]
        #
        # anim = find_chunks(chunk.chunks, "ANIM", ChunkType.Folder)
        # anim = [AnimChunk.convert(a) for a in anim]
        #
        # cams = list(find_chunks(chunk.chunks, "CAMS", ChunkType.Data))
        # cams = [CamsChunk.convert(c) for c in cams]

        args = (data, bvol)
        assert len(chunk.chunks) == _count(*args)
        return MslcChunk(chunk.header, *args)


@dataclass
class MsgrChunk(AbstractChunk):
    # parts: List[MsgrName]
    mslc: List[MslcChunk]
    data: GenericDataChunk
    bvol: BvolChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MsgrChunk:
        mslc = find_chunks(chunk.chunks, "MSLC", ChunkType.Folder)
        mslc = [MslcChunk.convert(_) for _ in mslc]

        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        # data = MsgrDataChunk.convert(data)

        bvol = find_chunk(chunk.chunks, "BVOL", ChunkType.Data)
        bvol = BvolChunk.convert(bvol)

        assert len(chunk.chunks) == 2 + len(mslc)
        return MsgrChunk(chunk.header, mslc, data, bvol)
        # # noinspection PyTypeChecker
        # data: GenericDataChunk = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        # # noinspection PyTypeChecker
        # submeshes = [MslcChunk.create(mscl) for mscl in find_chunks(chunk.chunks, "MSLC", ChunkType.Folder)]
        #
        # return MsgrChunk(chunk.header, parts, submeshes)


@dataclass
class MarkChunk(AbstractChunk):
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> MarkChunk:
        return MarkChunk(chunk.header, chunk.data)


@dataclass
class AnbvChunk(AbstractChunk):
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> AnbvChunk:
        return AnbvChunk(chunk.header, chunk.data)


@dataclass
class AnimChunkData(AbstractChunk):
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> AnimChunkData:
        return AnimChunkData(chunk.header, chunk.data)


@dataclass
class AnimChunk(GenericDataChunk):
    data: AnimChunkData
    anbv: AnbvChunk
    anim: Optional[AnimChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> AnimChunk:
        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        data = AnimChunkData.convert(data)
        anbv = find_chunk(chunk.chunks, "ANBV", ChunkType.Data)
        anbv = AnbvChunk.convert(anbv)
        anim = find_chunk(chunk.chunks, "ANIM", ChunkType.Folder)
        if anim:
            anim = AnimChunk.convert(anim)

        assert len(chunk.chunks) == 2 + (1 if anim else 0)
        return AnimChunk(chunk.header, data, anbv, anim)


@dataclass
class RsgmChunk(AbstractChunk):
    sshr: List[SshrChunk]
    skel: Optional[SkelChunk]
    msgr: Optional[MsgrChunk]
    mark: Optional[MarkChunk]
    anim: List[AnimChunk]
    txtr: List[TxtrChunk]
    shdr: List[FolderChunk]
    cams: Optional[GenericDataChunk]  # TODO

    @classmethod
    def convert(cls, chunk: FolderChunk) -> RsgmChunk:
        sshr = find_chunks(chunk.chunks, "SSHR", ChunkType.Data)
        sshr = [SshrChunk.convert(_) for _ in sshr]

        skel = find_chunk(chunk.chunks, "SKEL", ChunkType.Data)
        if skel:
            skel = SkelChunk.convert(skel)

        mark = find_chunk(chunk.chunks, "MARK", ChunkType.Data)
        if mark:
            mark = MarkChunk.convert(mark)

        msgr = find_chunk(chunk.chunks, "MSGR", ChunkType.Folder)
        if msgr:
            msgr = MsgrChunk.convert(msgr)

        anim = find_chunks(chunk.chunks, "ANIM", ChunkType.Folder)
        anim = [AnimChunk.convert(_) for _ in anim]

        txtr = find_chunks(chunk.chunks, "TXTR", ChunkType.Folder)
        txtr = [TxtrChunk.convert(_) for _ in txtr]

        shdr = find_chunks(chunk.chunks, "SHDR", ChunkType.Folder)
        shdr = list(shdr)

        cams = find_chunk(chunk.chunks, "CAMS", ChunkType.Data)

        args = (sshr, skel, msgr, mark, anim, txtr, shdr, cams)
        assert len(chunk.chunks) == _count(*args)
        return RsgmChunk(chunk.header, *args)


@dataclass
class WhmChunky(ConvertableChunky, RelicChunky):
    fbif: FbifChunk
    rsgm: RsgmChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> WhmChunky:
        fbif = find_chunk(chunky.chunks, "FBIF", ChunkType.Data)
        fbif = FbifChunk.convert(fbif)

        rsgm = find_chunk(chunky.chunks, "RSGM", ChunkType.Folder)
        rsgm = RsgmChunk.convert(rsgm)
        assert len(chunky.chunks) == 2

        return WhmChunky(chunky.header, fbif, rsgm)
