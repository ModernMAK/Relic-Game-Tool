from __future__ import annotations

# Painted Team BD?
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct

from relic.chunky.chunk.chunk import GenericDataChunk, AbstractChunk, FolderChunk
from relic.chunky.chunk.header import ChunkType
from relic.chunky.chunky.chunky import GenericRelicChunky, RelicChunky
from relic.chunky_formats.dow.common_chunks.imag import ImagChunk
from relic.chunky_formats.util import find_chunks, find_chunk


# Painted Team Layer Data?
# Painted Team BN?
# Looks identical to PTBD


@dataclass
class PtbdChunk(AbstractChunk):
    LAYOUT = Struct("< 4f")  # 4 floats?
    # floats are typically positions, uv coordinates?
    # atlas size maybe? IDK
    unk_a: float
    unk_b: float
    unk_c: float
    unk_d: float

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> 'PtbdChunk':
        args = cls.LAYOUT.unpack(chunk.raw_bytes)
        return PtbdChunk(chunk.header, *args)


@dataclass
class WtpInfoChunk(AbstractChunk):
    LAYOUT = Struct("< 2l")
    width: int
    height: int

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> WtpInfoChunk:
        height, width = cls.LAYOUT.unpack(chunk.raw_bytes)
        return WtpInfoChunk(chunk.header, width=width, height=height)  # SWAPPED! Using Kwargs to make sure order doesn't matter


@dataclass
class PtbnChunk:
    LAYOUT = Struct("< 4f")  # 4 floats?
    unk_a: float
    unk_b: float
    unk_c: float
    unk_d: float

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> PtbnChunk:
        args = cls.LAYOUT.unpack(chunk.raw_bytes)
        assert len(chunk.raw_bytes) == cls.LAYOUT.size
        return PtbnChunk(*args)


class PtldLayer(Enum):
    Primary = 0
    Secondary = 1
    Trim = 2
    Weapon = 3
    Eyes = 4
    Dirt = 5


@dataclass
class PtldChunk(AbstractChunk):
    LAYOUT = VStruct("< l v")

    layer: PtldLayer
    image: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> PtldChunk:
        assert chunk.header.version == 1
        layer_code, image = cls.LAYOUT.unpack(chunk.raw_bytes)
        layer = PtldLayer(layer_code)
        return PtldChunk(chunk.header, layer, image)


@dataclass
class TpatChunk:
    info: WtpInfoChunk
    imag: ImagChunk

    ptld: List[PtldChunk]
    ptbd: Optional[PtbdChunk]
    ptbn: Optional[PtbnChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'TpatChunk':
        info = find_chunk(chunk.chunks, "INFO", ChunkType.Data)
        info = WtpInfoChunk.convert(info)

        imag = find_chunk(chunk.chunks, "IMAG", ChunkType.Folder)
        imag = ImagChunk.convert(imag)

        ptld = find_chunks(chunk.chunks, "PTLD", ChunkType.Data)
        ptld = [PtldChunk.convert(_) for _ in ptld]
        # ptld = PtldChunk.convert(ptld) if ptld else None

        ptbd = find_chunk(chunk.chunks, "PTBD", ChunkType.Data)
        # ptbd = [PtbdChunk.convert(_) for _ in ptbd]
        ptbd = PtbdChunk.convert(ptbd) if ptbd else None

        ptbn = find_chunk(chunk.chunks, "PTBN", ChunkType.Data)
        # ptbn = [PtbnChunk.convert(_) for _ in ptbn]
        ptbn = PtbnChunk.convert(ptbn) if ptbn else None

        assert len(chunk.chunks) == sum(1 if _ else 0 for _ in [ptbd, ptbn]) + 2 + len(ptld), [(_.header.type.value,_.header.id) for _ in chunk.chunks]
        return TpatChunk(info, imag, ptld, ptbd, ptbn)


@dataclass
class WtpChunky(RelicChunky):
    tpat: TpatChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> WtpChunky:
        tpat = find_chunk(chunky.chunks, "TPAT", ChunkType.Folder)
        tpat = TpatChunk.convert(tpat)
        return WtpChunky(chunky.header, tpat)
