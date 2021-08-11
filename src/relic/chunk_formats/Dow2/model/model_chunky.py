from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from struct import Struct
from typing import List, Tuple, Optional

from relic.chunk_formats.Dow.whm import SkelChunk
from relic.chunk_formats.Shared.mesh_chunk import MeshChunk
from relic.chunk_formats.Shared.mgrp_chunk import SharedMgrpChunk, NodeChunk
from relic.chunk_formats.Shared.mrks_chunk import MrksChunk
from relic.chunk_formats.Shared.mtrl_chunk import MtrlChunk
from relic.chunky import RelicChunky, AbstractRelicChunky, ChunkCollection, DataChunk, FolderChunk
from relic.util.struct_util import unpack_from_stream




@dataclass
class ImodDataChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)



@dataclass
class ImodChunk:
    name: str
    data: ImodDataChunk
    meshs: List[MeshChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk):
        name = chunk.header.name
        data = ImodDataChunk.convert(chunk.get_data_chunk("DATA"))
        meshs = [MeshChunk.convert(c) for c in chunk.get_folder_chunks("MESH")]
        return ImodChunk(name, data, meshs)


@dataclass
class ImdgMeshChunk:
    imod: ImodChunk

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        imod = ImodChunk.convert(chunks.get_folder_chunk("IMOD"))
        return cls(imod)


@dataclass
class ImdgChunk:
    mesh: ImdgMeshChunk

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        mesh = ImdgMeshChunk.convert(chunks.get_folder_chunk("MESH"))
        return cls(mesh)


@dataclass
class MgrpMeshChunk:
    imdg: ImdgChunk

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        imdg = ImdgChunk.convert(chunks.get_folder_chunk("IMDG"))
        return MgrpMeshChunk(imdg)


@dataclass
class MgrpChunk(SharedMgrpChunk):
    mesh: MgrpMeshChunk

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        nodes = [NodeChunk.convert(n) for n in chunks.get_data_chunks("NODE")]
        mesh = MgrpMeshChunk.convert(chunks.get_folder_chunk("MESH"))
        return cls(nodes, mesh)


@dataclass
class ModlMeshChunk:
    mgrp: MgrpChunk

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        mgrp = MgrpChunk.convert(chunks.get_folder_chunk("MGRP"))
        return cls(mgrp)



@dataclass
class MsdChunk:
    name_a: Optional[str]
    one: int
    name_b: Optional[str]

    __INT = Struct("< L")
    __INVALID = __INT.unpack(bytes([0xff, 0xff, 0xff, 0xff]))[0]

    # data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        with BytesIO(chunk.data) as stream:
            if chunk.header.unk_v3_1[0] == cls.__INVALID:
                one = unpack_from_stream(cls.__INT, stream)[0]
                return cls(None, one, None)
            else:
                name_a = stream.read(unpack_from_stream(cls.__INT, stream)[0]).decode("ascii")
                one = unpack_from_stream(cls.__INT, stream)[0]
                name_b = stream.read(unpack_from_stream(cls.__INT, stream)[0]).decode("ascii")
                return cls(name_a, one, name_b)


@dataclass
class CnbpChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class MsbpChunk:
    msd: List[MsdChunk]
    cnbp: CnbpChunk

    @classmethod
    def convert(cls, chunk: ChunkCollection):
        msd = [MsdChunk.convert(c) for c in chunk.get_data_chunks("MSD ")]  # SPACE IS IMPORTANT
        cnbp = CnbpChunk.convert(chunk.get_data_chunk("CNBP"))
        return cls(msd, cnbp)


@dataclass
class DtbpChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)




@dataclass
class ModlChunk:
    mtrls: List[MtrlChunk]
    mesh: ModlMeshChunk
    skel: SkelChunk
    msbp: MsbpChunk
    dtbp: DtbpChunk
    mrks: MrksChunk

    @classmethod
    def convert(cls, chunk: ChunkCollection):
        mtrl = [MtrlChunk.convert(c) for c in chunk.get_folder_chunks("MTRL")]
        mesh = ModlMeshChunk.convert(chunk.get_folder_chunk("MESH"))
        skel = SkelChunk.convert(chunk.get_folder_chunk("SKEL"))
        msbp = MsbpChunk.convert(chunk.get_folder_chunk("MSBP"))
        dtbp = DtbpChunk.convert(chunk.get_data_chunk("DTBP"))
        mrks = MrksChunk.convert(chunk.get_data_chunk("MRKS"))
        return ModlChunk(mtrl, mesh, skel, msbp, dtbp, mrks)


@dataclass
class ModelChunky(AbstractRelicChunky):
    modl: ModlChunk

    @classmethod
    def convert(cls, chunky: RelicChunky) -> 'ModelChunky':
        modl = ModlChunk.convert(chunky.get_folder_chunk("MODL"))
        return ModelChunky(chunky.chunks, chunky.header, modl)


if __name__ == "__main__":
    # path = r"D:\Dumps\DOW_II\full_dump\art\race_ig\troops_wargear\heads\general\general_head.model"
    path = r"D:\Dumps\DOW_II\full_dump\art\race_ig\troops_wargear\armour\cadian_armour\cadian_armour.model"
    with open(path, "rb") as handle:
        chunky = RelicChunky.unpack(handle)
        model = ModelChunky.convert(chunky)
        print(model)
