
import enum
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import List, Optional
from typing import Tuple, BinaryIO, Union

from archive_tools.structx import Struct
from archive_tools.vstruct import VStruct
from relic.chunk_formats.Dow.shared.fbif_chunk import FbifChunk
from relic.chunk_formats.Dow.whm.errors import UnimplementedMslcBlockFormat
from relic.chunk_formats.Dow.whm.skel_chunk import SkelChunk
from relic.chunky import ChunkCollection, ChunkHeader, DataChunk, FolderChunk, RelicChunky
from relic.chunky.abstract_relic_chunky import AbstractRelicChunky


@dataclass
class SshrChunk:
    LAYOUT = VStruct("v")
    name: str

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'SshrChunk':
        with BytesIO(chunk.data) as stream:
            name = cls.LAYOUT.unpack_stream(stream)[0]
            name = name.decode("ascii")
            return SshrChunk(name)


@dataclass
class MsclHeader:
    reserved_zero_a: int
    # flag_b: bytes
    # unk_c: int
    unk_b: bytes
    reserved_zero_b: int
    name_count: int

    LAYOUT = Struct("< L 5s 2L")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MsclHeader':
        args = cls.LAYOUT.unpack_stream(stream)
        return MsclHeader(*args)


@dataclass
class MslcName:
    LAYOUT = VStruct("vl")
    name: str
    unk_a: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MslcName':
        name, unk = cls.LAYOUT.unpack_stream(stream)
        name = name.decode("ascii")
        return MslcName(name, unk)


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
        raise UnimplementedMslcBlockFormat(code)

    def vertex_buffer_size(self) -> int:
        size = {
            MslcBlockFormat.Vertex48: 48,
            MslcBlockFormat.Vertex32: 32,
        }
        val = size.get(self)
        if val is None:
            raise KeyError(f"'{val}' is not a Vertex Buffer Type")
        return val


@dataclass
class VertexMsclBlock:
    format: MslcBlockFormat
    count: int
    vertex_buffer: bytes
    _code: int = 0


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
            i_buffer = stream.read(index_count * 2) # index is a short
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
            buffer_size = f.vertex_buffer_size()
            v_buffer = stream.read(buffer_size * count)
            return VertexMsclBlock(f, count, v_buffer, code)
        except KeyError:
            pass

        raise NotImplementedError(code)


@dataclass
class MslcChunk:
    header: MsclHeader
    names: List[MslcName]
    blocks: List[MslcBlock]

    @classmethod
    def create(cls, chunk: FolderChunk) -> 'MslcChunk':
        data: DataChunk = chunk.get_chunk(id="DATA", recursive=False)
        # WHM's data.header.version always '2'
        with BytesIO(data.data) as stream:
            header = MsclHeader.unpack(stream)
            global DB_LAST
            DB_LAST = []
            names = [MslcName.unpack(stream) for _ in range(header.name_count)]

            blocks = []

            start = stream.tell()
            stream.seek(0, 2)
            end = stream.tell()
            stream.seek(start)

            while stream.tell() != end:
                block = MslcBlockUtil.unpack(stream)
                blocks.append(block)
            return MslcChunk(header, names, blocks)



@dataclass
class MsgrName:
    LAYOUT = VStruct("v2L")
    name: str
    unk_a: int
    unk_b: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MsgrName':
        name, unk_a,unk_b = cls.LAYOUT.unpack_stream(stream)
        name = name.decode("ascii")
        return MsgrName(name, unk_a, unk_b)


@dataclass
class MsgrChunk:
    LAYOUT = Struct("<L")
    parts: List[MsgrName]
    sub_meshes: List['MslcChunk']


    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'MsgrChunk':
        # the id is DATA not the type (alhough it is coincidentally, a ChunkType.Data)
        data: DataChunk = chunk.get_chunk(id="DATA", recursive=False)
        with BytesIO(data.data) as stream:
            count = cls.LAYOUT.unpack_stream(stream)[0]
            parts = [MsgrName.unpack(stream) for _ in range(count)]
        submeshes = [MslcChunk.create(mscl) for mscl in chunk.get_chunks(id="MSLC")]

        return MsgrChunk(parts, submeshes)

@dataclass
class MarkChunk:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'MarkChunk':
        return MarkChunk(chunk.header, chunk.data)


@dataclass
class AnbvChunk:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'AnbvChunk':
        return AnbvChunk(chunk.header, chunk.data)

@dataclass
class AnimChunkData:
    header: ChunkHeader
    raw: bytes

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'AnimChunkData':
        return AnimChunkData(chunk.header, chunk.data)


@dataclass
class AnimChunk:
    data: AnimChunkData
    anbv: AnbvChunk

    @classmethod
    def convert(cls, chunk: ChunkCollection) -> 'AnimChunk':
        data = AnimChunkData.convert(chunk.get_chunk(recursive=False, id="DATA"))
        anbv = AnbvChunk.convert(chunk.get_chunk(recursive=False, id="ANBV"))
        return AnimChunk(data, anbv)


@dataclass
class RsgmChunk:
    sshr: List[SshrChunk]
    skel: Optional[SkelChunk]
    msgr: MsgrChunk
    mark: MarkChunk
    anim: List[AnimChunk]

    @classmethod
    def convert(cls, chunk: ChunkCollection) -> 'RsgmChunk':
        sshr = [SshrChunk.convert(c) for c in chunk.get_chunks(id='SSHR', recursive=False)]

        skel_chunk = chunk.get_chunk(id='SKEL', recursive=False, optional=True)
        skel = SkelChunk.convert(skel_chunk) if skel_chunk else None

        mark_chunk = chunk.get_chunk(id="MARK", recursive=False, optional=True)
        mark = MarkChunk.convert(mark_chunk) if mark_chunk else None

        msgr = MsgrChunk.convert(chunk.get_chunk(id="MSGR", recursive=False))

        anim = [AnimChunk.convert(c) for c in chunk.get_chunks(id='ANIM', recursive=False)]

        return RsgmChunk(sshr, skel, msgr, mark, anim)


@dataclass
class WhmChunky(AbstractRelicChunky):
    rsgm: RsgmChunk
    fbif: Optional[FbifChunk] = None

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'WhmChunky':
        rsgm = RsgmChunk.convert(chunky.get_chunk(id="RSGM", recursive=False))
        fbif = FbifChunk.convert(chunky.get_chunk(id="FBIF", recursive=False))
        # sshr = [SshrChunk.convert(c) for c in chunky.get_chunks(id='SSHR')]
        # msgr = MsgrChunk.convert(chunky.get_chunk(id="MSGR"))
        return WhmChunky(chunky.chunks, chunky.header, rsgm, fbif)  # sshr, msgr)


