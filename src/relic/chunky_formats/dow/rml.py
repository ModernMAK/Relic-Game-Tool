from __future__ import annotations
from dataclasses import dataclass
from typing import List

from relic.chunky import RelicChunky, GenericRelicChunky, ChunkType, GenericDataChunk, AbstractChunk, FolderChunk
from relic.chunky_formats.util import find_chunks, find_chunk, UnimplementedDataChunk


@dataclass
class ModfChunk(AbstractChunk):
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> ModfChunk:
        return ModfChunk(chunk.header, chunk.raw_bytes)


@dataclass
class MdatChunk(AbstractChunk):
    raw: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> MdatChunk:
        return cls(chunk.header, chunk.raw_bytes)


@dataclass
class MotnChunk(AbstractChunk):
    mdat: MdatChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MotnChunk:
        mdat = find_chunk(chunk.chunks, "MDAT", ChunkType.Data)
        mdat = MdatChunk.convert(mdat)
        assert len(chunk.chunks) == 1
        return MotnChunk(chunk.header, mdat)


@dataclass
class MtonChunk(UnimplementedDataChunk):
    pass


@dataclass
class ModlChunk(AbstractChunk):
    modf: List[ModfChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ModlChunk:
        modf = find_chunks(chunk.chunks, "MODF", ChunkType.Data)
        modf = [ModfChunk.convert(_) for _ in modf]
        assert len(chunk.chunks) == len(modf)
        return ModlChunk(chunk.header, modf)


@dataclass
class MtreChunk(AbstractChunk):
    # Check version to see if one uses motn and another uses mton
    motn: List[MotnChunk]
    mton: List[MtonChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MtreChunk:
        motn = find_chunks(chunk.chunks, "MOTN", ChunkType.Folder)
        motn = [MotnChunk.convert(_) for _ in motn]

        mton = find_chunks(chunk.chunks, "MTON", ChunkType.Data)
        mton = [MtonChunk.convert(_) for _ in mton]

        assert len(chunk.chunks) == len(motn) + len(mton)
        return MtreChunk(chunk.header, motn, mton)


@dataclass
class ErmlChunk(AbstractChunk):
    modl: ModlChunk
    mtre: MtreChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ErmlChunk:
        modl = find_chunk(chunk.chunks, "MODL", ChunkType.Folder)
        modl = ModlChunk.convert(modl)
        mtre = find_chunk(chunk.chunks, "MTRE", ChunkType.Folder)
        mtre = MtreChunk.convert(mtre)
        assert len(chunk.chunks) == 2
        return ErmlChunk(chunk.header, modl, mtre)


@dataclass
class RmlChunky(RelicChunky):
    erml: ErmlChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> RmlChunky:
        # print([(c.header.type, c.header.id) for c in chunky.chunks])
        # raise NotImplementedError
        erml = find_chunk(chunky.chunks, "ERML", ChunkType.Folder)
        erml = ErmlChunk.convert(erml)
        assert len(chunky.chunks) == 1
        return RmlChunky(chunky.header, erml)
