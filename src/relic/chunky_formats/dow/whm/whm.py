from __future__ import annotations

# A MODEL SPECIFICATION. ish...
#   "https://web.archive.org/web/20141003211026/http://forums.relicnews.com/showthread.php?89094-Specs-for-models-to-be-used-in-DoW"
#   HA, nice for some

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO
from typing import List, Optional

from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct

from .animation import AnimChunk
from .mesh import MslcChunk
from .shared import BvolChunk
from ..common_chunks.fbif import FbifChunk
from ..common_chunks.imag import TxtrChunk
from ...convertable import ChunkConverterFactory
from ...util import UnimplementedFolderChunk, UnimplementedDataChunk, ChunkCollectionX
from ....chunky import ChunkyVersion
from ....chunky.chunk.chunk import GenericDataChunk, FolderChunk, AbstractChunk
from ....chunky.chunk.header import ChunkType
from ....chunky.chunky.chunky import RelicChunky, GenericRelicChunky
from ....file_formats.mesh_io import Float3, Float4


@dataclass
class SshrChunk(AbstractChunk):
    VERSIONS = [2]
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "SSHR"
    LAYOUT = VStruct("v")
    name: str  # IBB's IChunky Viewer says this is shader path? Maybe in CoH, but DoW; this looks like a texture name

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
class CamsChunk(UnimplementedDataChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "CAMS"


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

        assert len(chunk.chunks) == sum([1 if _ else 0 for _ in [data, bvol]]) + len(mslc)
        return MsgrChunk(chunk.header, mslc, data, bvol)


@dataclass
class MarkChunk(UnimplementedDataChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "MARK"


@dataclass
class RsgmChunk(AbstractChunk):
    CHUNK_ID = "RSGM"
    CHUNK_TYPE = ChunkType.Folder
    VERSIONS = [1, 3]


@dataclass
class RsgmChunkV1(UnimplementedFolderChunk):
    _VERSION = 1

    # @classmethod
    # def convert(cls, chunk:FolderChunk) -> RsgmChunkV1:
    #     raise NotImplementedError


@dataclass
class RsgmChunkV3(RsgmChunk):
    _VERSION = 3

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
        assert chunk.header.version == cls._VERSION
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
        assert len(chunk.chunks) == count

        return RsgmChunkV3(chunk.header, anim, txtr, shdr, sshr, msgr, skel, mark, cams)


@dataclass
class ShdrInfoChunk(UnimplementedDataChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "INFO"


@dataclass
class ChanChunk(UnimplementedDataChunk):
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "CHAN"


@dataclass
class ShdrChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "SHDR"
    VERSIONS = [1]
    info: ShdrInfoChunk
    chan: List[ChanChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ShdrChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = WhmChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        info = x.find(ShdrInfoChunk)
        chan = x.find(ChanChunk, True)
        assert len(chunk.chunks) == 1 + len(chan)
        return cls(chunk.header, info, chan)


@dataclass
class RsgmChunkFactory:
    CHUNK_ID = "RSGM"
    CHUNK_TYPE = ChunkType.Folder
    __MAP = {
        # RsgmChunkV1.VERSION: RsgmChunkV1,
        RsgmChunkV3._VERSION: RsgmChunkV3,
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
    VERSIONS = [5]
    LAYOUT = Struct("< l")
    bones: List[SkelTransform]

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> SkelChunk:
        assert chunk.header.version in cls.VERSIONS, (chunk.header.version, cls.VERSIONS)
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


def add_msgr_chunk_converter(conv):
    conv.register(MslcChunk)
    conv.register(MsgrDataChunk)
    conv.register(BvolChunk)
    return conv


def generate_msgr_chunk_converter():
    conv = ChunkConverterFactory()
    add_msgr_chunk_converter(conv)
    return conv


def add_whm_chunk_converter(conv: ChunkConverterFactory):
    conv.register(FbifChunk)
    conv.register(RsgmChunkFactory)
    conv.register(TxtrChunk)
    conv.register(ShdrChunk)
    conv.register(ShdrInfoChunk)
    conv.register(ChanChunk)
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
MsgrChunkConverter = generate_msgr_chunk_converter()
WhmChunkConverter = generate_whm_chunk_converter()
