from dataclasses import dataclass
from typing import List

from relic.chunk_formats.Shared.skel_chunk import SkelChunk
from relic.chunk_formats.Shared.mesh_chunk import MeshChunk
from relic.chunk_formats.Shared.mgrp_chunk import SharedMgrpChunk, NodeChunk
from relic.chunk_formats.Shared.mrks_chunk import MrksChunk
from relic.chunk_formats.Shared.mtrl_chunk import MtrlChunk
from relic.chunky import ChunkCollection, DataChunk, RelicChunky


@dataclass
class MgrpChunk(SharedMgrpChunk):
    meshes: List[MeshChunk]

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        nodes = [NodeChunk.convert(n) for n in chunks.get_data_chunks("NODE")]
        mesh = [MeshChunk.convert(m) for m in chunks.get_folder_chunks("MESH")]
        return cls(nodes, mesh)


@dataclass
class ModlMeshChunk:
    mgrp: MgrpChunk

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        mgrp = MgrpChunk.convert(chunks.get_folder_chunk("MGRP"))
        return cls(mgrp)


@dataclass
class CuatChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class ModlInfoChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class ModlChunk:
    mtrls: List[MtrlChunk]
    mesh: ModlMeshChunk
    skel: SkelChunk
    cuat: CuatChunk
    info: ModlInfoChunk
    mrks: MrksChunk

    @classmethod
    def convert(cls, chunk: ChunkCollection):
        mtrl = [MtrlChunk.convert(c) for c in chunk.get_folder_chunks("MTRL")]
        mesh = ModlMeshChunk.convert(chunk.get_folder_chunk("MESH"))
        skel = SkelChunk.convert(chunk.get_folder_chunk("SKEL"))
        cuat = CuatChunk.convert(chunk.get_data_chunk("CUAT"))
        info = ModlInfoChunk.convert(chunk.get_data_chunk("INFO"))
        mrks = MrksChunk.convert(chunk.get_data_chunk("MRKS"))
        return ModlChunk(mtrl, mesh, skel, cuat, info, mrks)


@dataclass
class RgmChunky:
    modl: ModlChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'RgmChunky':
        modl = ModlChunk.convert(chunky.get_folder_chunk("MODL"))
        return cls(modl)


if __name__ == "__main__":
    path = r"D:\Dumps\DOW_III\full_dump\art\armies\astra_militarum\troops\cadian\armour\varlock_guard_damage_common\varlock_guard_damage_common.rgm"
    with open(path, "rb") as handle:
        chunky = RelicChunky._unpack(handle)
        rgm = RgmChunky.convert(chunky)
        print(rgm)
