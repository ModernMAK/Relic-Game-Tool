import enum
import struct
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import Tuple, List, BinaryIO, Union

from relic.chunk_formats.whm.errors import UnimplementedMslcBlockFormat
from relic.chunk_formats.whm.shared import num_layout
from relic.chunky import FolderChunk, DataChunk
from relic.shared import unpack_from_stream


@dataclass
class MsclHeader:
    reserved_zero_a: int
    # flag_b: bytes
    # unk_c: int
    unk_b: bytes
    reserved_zero_b: int
    name_count: int

    _HEADER = struct.Struct("< L 5s L L")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MsclHeader':
        args = unpack_from_stream(cls._HEADER, stream)
        return MsclHeader(*args)


@dataclass
class MslcName:
    name: str
    unk_a: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MslcName':
        buffer = stream.read(num_layout.size)
        size = num_layout.unpack(buffer)[0]
        name = stream.read(size).decode("ascii")

        buffer = stream.read(num_layout.size)
        unk_a = num_layout.unpack(buffer)[0]

        return MslcName(name, unk_a)


class MslcBlockFormat(Enum):
    Vertex32 = enum.auto()  # = 37
    Vertex48 = enum.auto()  # = 39

    # Oh boy; IDK how many 'texture' classes there are but there are enough
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
    _HEADER_LAYOUT = struct.Struct("< L L")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> MslcBlock:
        def read_index_block() -> TextureMsclSubBlock:
            name_size = num_layout.unpack(stream.read(num_layout.size))[0]
            name = stream.read(name_size).decode("ascii")
            index_size = num_layout.unpack(stream.read(num_layout.size))[0]
            i_buffer = stream.read(index_size * 2)
            return TextureMsclSubBlock(name, index_size, i_buffer, count)

        # Code currently has a lot of 'garbage values'
        #   But '5', '3', '2', '39', '37', '1', '6', look the least garbagey and the most common.
        #       All those numbers occur at least 9+ times; 39, 37 & 1 occur at least 3000 times

        count, code = unpack_from_stream(cls._HEADER_LAYOUT, stream)
        f = MslcBlockFormat.from_code(code)
        if f == MslcBlockFormat.Texture:
            texture_count = code
            subs = []
            infos = []
            INFO = struct.Struct("< l l")
            for _ in range(texture_count):
                sub = read_index_block()

                buffer = stream.read(INFO.size)
                info = INFO.unpack(buffer)

                subs.append(sub)
                infos.append(info)

            UNK = struct.Struct("< l l l")

            buffer = stream.read(UNK.size)
            unks = UNK.unpack(buffer)

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
