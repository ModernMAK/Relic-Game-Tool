from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from relic.chunky import RelicChunky, AbstractChunk, FolderChunk, GenericDataChunk
from relic.chunky.chunk import ChunkType
from relic.chunky.chunky import GenericRelicChunky
from relic.chunky_formats.common_chunks.imag import ImagChunk
from relic.chunky_formats.convertable import find_chunk, find_chunks, UnimplementedFolderChunk, UnimplementedDataChunk
from relic.chunky_formats.whm.skel import SkelChunk
from relic.chunky_formats.whm.whm import SshrChunk, MsgrChunk, MarkChunk, AnimChunk, _count


@dataclass
class TxtrInfoChunk(UnimplementedDataChunk):
    pass


@dataclass
class TxtrChunk(UnimplementedFolderChunk):
    info: TxtrInfoChunk
    imag: ImagChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> TxtrChunk:
        info = find_chunk(chunk.chunks, "INFO", ChunkType.Data)
        info = TxtrInfoChunk.convert(info)

        imag = find_chunk(chunk.chunks, "IMAG", ChunkType.Folder)
        imag = ImagChunk.convert(imag)

        return cls(chunk.header, info, imag)
@dataclass
class GeomDataChunk(UnimplementedDataChunk):
    pass
@dataclass
class GeomShdwChunk(UnimplementedDataChunk):
    pass

@dataclass
class GeomBvolChunk(UnimplementedDataChunk):
    pass

@dataclass
class GeomChunk(AbstractChunk):
    data: GeomDataChunk
    shdw: GeomShdwChunk
    bvol: GeomBvolChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> GeomChunk:
        data = find_chunk(chunk.chunks, "DATA", ChunkType.Data)
        data = GeomDataChunk.convert(data)

        shdw = find_chunk(chunk.chunks, "SHDW", ChunkType.Data)
        shdw = GeomShdwChunk.convert(shdw)

        bvol = find_chunk(chunk.chunks, "BVOL", ChunkType.Data)
        bvol = GeomBvolChunk.convert(bvol)

        return cls(chunk.header, data, shdw, bvol)

@dataclass
class MeshChunk(AbstractChunk):
    geom: GeomChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> MeshChunk:
        geom = find_chunk(chunk.chunks, "GEOM", ChunkType.Folder)
        geom = GeomChunk.convert(geom)
        return cls(chunk.header, geom)


@dataclass
class ShdrChunk(UnimplementedFolderChunk):
    pass


@dataclass
class RsgmChunk(AbstractChunk):
    txtr: TxtrChunk
    shdr: FolderChunk  # TODO
    mesh: MeshChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> RsgmChunk:
        assert chunk.header.version == 1
        txtr = find_chunk(chunk.chunks, "TXTR", ChunkType.Folder)
        txtr = TxtrChunk.convert(txtr)

        shdr = find_chunk(chunk.chunks, "SHDR", ChunkType.Folder)

        mesh = find_chunk(chunk.chunks, "MESH", ChunkType.Folder)
        mesh = MeshChunk.convert(mesh)

        assert len(chunk.chunks) == 3, (cls.__name__, [(_.header.type.value, _.header.id) for _ in chunk.chunks])
        return RsgmChunk(chunk.header, txtr, shdr, mesh)


# Like WHM, but lacks FBIF (file burn info)
@dataclass
class SgmChunky(RelicChunky):
    rsgm: RsgmChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> SgmChunky:
        rsgm = find_chunk(chunky.chunks, "RSGM", ChunkType.Folder)
        rsgm = RsgmChunk.convert(rsgm)
        assert len(chunky.chunks) == 1
        return SgmChunky(chunky.header, rsgm)
