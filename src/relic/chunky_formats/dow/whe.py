from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from relic.chunky import AbstractChunk, FolderChunk
from relic.chunky.chunk import ChunkType
from relic.chunky.chunky import RelicChunky, GenericRelicChunky
from relic.chunky_formats.dow.common_chunks.fbif import FbifChunk
from relic.chunky_formats.util import find_chunks, find_chunk, UnimplementedDataChunk
from relic.chunky_formats.dow.events import EvctChunk
from relic.chunky_formats.dow.rml import MtreChunk, ModlChunk
from relic.chunky_formats.dow.whm.animation import AnbvChunk, AnimChunk


@dataclass
class SeuiChunk(UnimplementedDataChunk):
    pass


@dataclass
class ClasChunk(UnimplementedDataChunk):
    pass


@dataclass
class ClstChunk(AbstractChunk):
    clas: List[ClasChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ClstChunk:
        clas = find_chunks(chunk.chunks, "CLAS", ChunkType.Data)
        clas = [ClasChunk.convert(_) for _ in clas]

        assert len(chunk.chunks) == len(clas)
        return cls(chunk.header, clas)


@dataclass
class ActsChunk(UnimplementedDataChunk):
    pass


@dataclass
class CondChunk(UnimplementedDataChunk):
    pass


@dataclass
class ConlChunk(AbstractChunk):
    cond: List[CondChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> ConlChunk:
        cond = find_chunks(chunk.chunks, "COND", ChunkType.Data)
        cond = [CondChunk.convert(_) for _ in cond]

        assert len(chunk.chunks) == len(cond)
        return cls(chunk.header, cond)


@dataclass
class XrefChunk(UnimplementedDataChunk):
    pass


@dataclass
class AnimChunk(AbstractChunk):
    xref: XrefChunk
    anbv: AnbvChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> AnimChunk:
        xref = find_chunk(chunk.chunks, "XREF", ChunkType.Data)
        xref = XrefChunk.convert(xref)

        anbv = find_chunk(chunk.chunks, "ANBV", ChunkType.Data)
        anbv = AnbvChunk.convert(anbv)

        assert len(chunk.chunks) == 2
        return AnimChunk(chunk.header, xref, anbv)


@dataclass
class RebpChunk(AbstractChunk):
    clst: Optional[ClstChunk]
    conl: Optional[ConlChunk]
    mtre: MtreChunk
    acts: Optional[ActsChunk]
    seui: SeuiChunk
    evct: Optional[EvctChunk]
    modl: Optional[ModlChunk]
    anim: List[AnimChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> RebpChunk:
        # Seems to vary; but version is always 4?
        assert chunk.header.version == 4, chunk.header.version

        clst = find_chunk(chunk.chunks, "CLST", ChunkType.Folder)
        clst = ClstChunk.convert(clst) if clst else None

        conl = find_chunk(chunk.chunks, "CONL", ChunkType.Folder)
        conl = ConlChunk.convert(conl) if conl else None

        mtre = find_chunk(chunk.chunks, "MTRE", ChunkType.Folder)
        mtre = MtreChunk.convert(mtre)

        acts = find_chunk(chunk.chunks, "ACTS", ChunkType.Data)
        acts = ActsChunk.convert(acts) if acts else None

        seui = find_chunk(chunk.chunks, "SEUI", ChunkType.Data)
        seui = SeuiChunk.convert(seui)

        evct = find_chunk(chunk.chunks, "EVCT", ChunkType.Folder)
        evct = EvctChunk.convert(evct) if evct else None

        modl = find_chunk(chunk.chunks, "MODL", ChunkType.Folder)
        modl = ModlChunk.convert(modl) if modl else None

        anim = find_chunks(chunk.chunks, "ANIM", ChunkType.Folder)
        anim = [AnimChunk.convert(_) for _ in anim]

        _loaded = 2 + (1 if clst else 0) + (1 if conl else 0) + (1 if evct else 0) + (1 if acts else 0) + (1 if modl else 0) + len(anim)
        assert len(chunk.chunks) == _loaded, (len(chunk.chunks), _loaded, [(_.header.type.value, _.header.id) for _ in chunk.chunks], [clst, conl, mtre, acts, seui, evct, modl, anim])
        return RebpChunk(chunk.header, clst, conl, mtre, acts, seui, evct, modl, anim)


@dataclass
class WheChunky(RelicChunky):
    fbif: FbifChunk
    rebp: RebpChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> WheChunky:
        fbif = find_chunk(chunky.chunks, "FBIF", ChunkType.Data)
        fbif = FbifChunk.convert(fbif)
        rebp = find_chunk(chunky.chunks, "REBP", ChunkType.Folder)
        rebp = RebpChunk.convert(rebp)
        assert len(chunky.chunks) == 2
        return WheChunky(chunky.header, fbif, rebp)
