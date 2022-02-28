from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import List, Tuple, Optional

from archive_tools.ioutil import has_data
from archive_tools.structx import Struct
from archive_tools.vstruct import VStruct

from relic.chunky import FolderChunk, ChunkCollection, GenericDataChunk, RelicChunky, ChunkyVersion, GenericRelicChunky, ChunkType, AbstractChunk
from relic.chunky_formats.convertable import ChunkConverterFactory
from relic.chunky_formats.dow.whm.whm import SkelChunk
from relic.chunky_formats.util import ChunkCollectionX
from relic.file_formats.mesh_io import Float3, Float2


@dataclass
class BVolChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        return cls(chunk.raw_bytes)


@dataclass
class MrfmChunk(GenericDataChunk):
    pass
    # data: bytes
    #
    # def convert(self):


@dataclass
class TrimVertex:
    position: Float3
    normal: Optional[Float3]
    # unk_color: bytes
    uv: Float2
    unks: Optional[List[bytes]] = None

    # A bit of reading for Float16s in Vertex Buffers:
    # 'https://www.yosoygames.com.ar/wp/2018/03/vertex-formats-part-1-compression/'
    #   I couldn't find the Normal using Float32 but the wierd placement of byte (0,0,255,0) got me thinking about the Half format
    #       Unfortunately; it wasn't that simple; but my experience with Voxels taught me about other ways to express normals ALA SNorm and UNorm
    #       I do think this is an SNorm Float16, which kinda works out for us, The article has some fancy talk for how to handle SNorm (due to the dreaded -32758

    @classmethod
    def __parse_40(cls, data: bytes) -> 'TrimVertex':
        with BytesIO(data) as stream:
            pos = Struct("< 3f").unpack_stream(stream)
            # unks = Struct("< 8B").unpack_stream(stream)  # 2?
            INT_16_MAX = 32767
            unks_raw = Struct("< 14B").unpack_stream(stream)
            normal_raw = Struct("< 3h").unpack_stream(stream)
            normal = [v / INT_16_MAX for v in normal_raw]
            # unk_b = Struct("< 4B").unpack_stream(stream)  # RGBA?
            uv = Struct("< 2f").unpack_stream(stream)
            return TrimVertex(pos, normal, uv, unks_raw)

    @classmethod
    def __parse_32(cls, data: bytes) -> 'TrimVertex':
        with BytesIO(data) as stream:
            pos = Struct("< 3f").unpack_stream(stream)
            unks_raw = Struct("< 6B").unpack_stream(stream)
            INT_16_MAX = 32767
            normal_raw = Struct("< 3h").unpack_stream(stream)
            normal = [v / INT_16_MAX for v in normal_raw]

            uv = Struct("< 2f").unpack_stream(stream)
            return TrimVertex(pos, normal, uv, unks_raw)

    @classmethod
    def __parse_24(cls, data: bytes) -> 'TrimVertex':
        with BytesIO(data) as stream:
            pos = Struct("< 3f").unpack_stream(stream)
            unks_raw = Struct("< 4B").unpack_stream(stream)
            # INT_16_MAX = 32767
            # normal_raw = Struct("< 3h").unpack_stream(stream)
            # normal = [v / INT_16_MAX for v in normal_raw]
            #
            uv = Struct("< 2f").unpack_stream(stream)
            return TrimVertex(pos, None, uv, unks_raw)

    @classmethod
    def parse(cls, data: bytes):
        if len(data) == 24:
            return cls.__parse_24(data)
        elif len(data) == 32:
            return cls.__parse_32(data)
        elif len(data) == 40:
            return cls.__parse_40(data)
        else:
            raise NotImplementedError(len(data))


@dataclass
class TrimDataChunk:
    unk_a_blocks: List[Tuple[int, int, int]]
    vertexes: List[TrimVertex]
    unk_b: int
    unk_c: int
    indexes: List[int]
    material_name: str
    skel: List[Tuple[str, List[float]]]
    unk_d: int
    unk_e: int

    __short_layout = Struct("< H")
    __int_layout = Struct("< L")
    __int2_layout = Struct("< 2L")
    __int3_Layout = Struct("< 3L")
    __int4_Layout = Struct("< 4L ")
    __unk_skel_layout = Struct("< 24f")

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        with BytesIO(chunk.raw_bytes) as stream:
            unk_a_count = cls.__int_layout.unpack_stream(stream)[0]
            unk_a = [cls.__int3_Layout.unpack_stream(stream) for _ in range(unk_a_count)]
            v_count = cls.__int_layout.unpack_stream(stream)[0]
            v_size = cls.__int_layout.unpack_stream(stream)[0]
            # Vertexes in this format are 'packed' instead of 'flattened'
            # This is probably why this format specifies the vertex size explicitly.
            vertexes = [TrimVertex.parse(stream.read(v_size)) for _ in range(v_count)]
            unk_b, index_count, unk_c, index_count_2 = cls.__int4_Layout.unpack_stream(stream)
            assert index_count == index_count_2
            indexes = [cls.__short_layout.unpack_stream(stream)[0] for _ in range(index_count)]
            name_size = cls.__int_layout.unpack_stream(stream)[0]
            name = stream.read(name_size).decode("ascii")
            skel_count = cls.__int_layout.unpack_stream(stream)[0]
            skels = []
            for _ in range(skel_count):
                skel_unks = cls.__unk_skel_layout.unpack_stream(stream)
                skel_name_len = cls.__int_layout.unpack_stream(stream)[0]
                skel_name = stream.read(skel_name_len).decode("ascii")
                skels.append((skel_name, skel_unks))
            unk_d, unk_e = cls.__int2_layout.unpack_stream(stream)
            return cls(unk_a, vertexes, unk_b, unk_c, indexes, name, skels, unk_d, unk_e)

            # # PSUEDOCODE
        # unk_count_a = read_int32
        # unk_a_block = [read_int32x3 for _ in range(unk_count_a)]
        # v_count = read_int32
        # v_size = read_int32
        # v_buffer = read_bytes(v_size*v_count)
        # unk_ba, index_count, unk_bb, index_count_again = read_int32 * 4
        # i_buffer = read_bytes(index_count * 2)
        # name = read_length_string # AKA len = read_int32, read_bytes(len)
        # skel_count = read_int32
        # skels = []
        # for _ in range(skel_count):
        #     skel_unks = read_float32 * 6 * 4
        #     skel_name = read_length_string
        #     skel = (skel_unks, skel_name)
        #     skels.add(skel)
        # unk_ca, unk_cb = read_int32 * 2


# @ 0x58 ~ Vertex Count
# 40 is Vertex Size
# @ 0x4958 ~ Index Block


@dataclass
class TrimChunk:
    bvol: List[BVolChunk]
    data: TrimDataChunk
    mrfm: Optional[MrfmChunk]

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        bvol = [BVolChunk.convert(c) for c in chunks.get_data_chunks("BVOL")]
        data = TrimDataChunk.convert(chunks.get_data_chunk("DATA"))
        mrfm = chunks.get_data_chunk("MFRM", optional=True)
        return TrimChunk(bvol, data, mrfm)


@dataclass
class MeshChunk:
    name: str
    trim: TrimChunk

    @classmethod
    def convert(cls, chunk: FolderChunk):
        name = chunk.header.name
        trim = TrimChunk.convert(chunk.get_folder_chunk("TRIM"))
        return MeshChunk(name, trim)


@dataclass
class NodeChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        return cls(chunk.raw_bytes)


@dataclass
class SharedMgrpChunk:
    nodes: List[NodeChunk]


@dataclass
class MtrlInfoChunk:
    LAYOUT = VStruct("v")
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "INFO"
    VERSIONS = [1]
    shader_name: str

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        # with BytesIO(chunk.raw_bytes) as stream:
        name = cls.LAYOUT.unpack(chunk.raw_bytes)[0]
        # name_len = Struct("< L").unpack_stream(stream)[0]
        name = name.decode("ascii")
        return cls(name)


class MaterialVarType(Enum):
    Texture = 9
    WorldMaybe = 8
    HighlightMaybe = 10
    MultiplierMaybe = 1
    OcclusionFlagMaybe = 0
    MatrixRow = 5


@dataclass
class VarChunk(AbstractChunk):
    LAYOUT = VStruct("< v l v")
    CHUNK_TYPE = ChunkType.Data
    CHUNK_ID = "VAR"
    VERSIONS = [1]

    property_name: str
    var_type: MaterialVarType
    property_data:bytes

    # args: Optional[Tuple] = None
    # excess: Optional[Tuple[bytes, bytes]] = None

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        with BytesIO(chunk.raw_bytes) as stream:
            prop, var_type, buffer = cls.LAYOUT.unpack_stream(stream)
            prop = prop.decode("ascii")
            var_type = MaterialVarType(var_type)
            # This acts as a soft assertion; if the buffer is too small, we'll get an unpack error
            # if either exceess has extra bytes, then somethings probably wrong, but I don't check for it
            # T-o-d-o check for it ~ archive_tools VStruct will make sure the buffer does not have any missing bytes (still does not check for excess tho)
            assert not has_data(stream), stream.read()
            return cls(chunk.header,prop,var_type,buffer)
            # with BytesIO(buffer) as buffer_stream:
            #     if var_type == MaterialVarType.Texture:
            #         args = buffer_stream.read().decode("ascii").strip("\0")
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(chunk.header, prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.HighlightMaybe:
            #         args = Struct("< b").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.MatrixRow:
            #         args = Struct("< 4f").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.MultiplierMaybe:
            #         args = Struct("< f").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.OcclusionFlagMaybe:
            #         args = Struct("< L").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)
            #     elif var_type == MaterialVarType.WorldMaybe:
            #         args = Struct("< 16f").unpack_stream(buffer_stream)
            #         excess = buffer_stream.read(), stream.read()
            #         return VarChunk(prop, var_type, args, excess)

                # raise NotImplementedError


@dataclass
class SkelInfoChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        return cls(chunk.raw_bytes)


@dataclass
class BoneChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        return cls(chunk.raw_bytes)


@dataclass
class SkelChunk:
    info: SkelInfoChunk
    bones: List[BoneChunk]

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        info = SkelInfoChunk.convert(chunks.get_data_chunk("INFO"))
        bones = [BoneChunk.convert(c) for c in chunks.get_data_chunks("BONE")]
        return SkelChunk(info, bones)


@dataclass
class MtrlChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MTRL"
    VERSIONS = [1]
    # name: str
    info: MtrlInfoChunk
    var: List[VarChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'MtrlChunk':
        assert chunk.header.version in cls.VERSIONS
        converted = ModelChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        info = x.find(MtrlInfoChunk)
        var = x.find(VarChunk, True)
        assert len(chunk.chunks) == 1+len(var), [c.header.id for c in chunk.chunks]
        return MtrlChunk(chunk.header, info, var)


@dataclass
class MrksChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        return cls(chunk.raw_bytes)


@dataclass
class ImodDataChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        return cls(chunk.raw_bytes)


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
    def convert(cls, chunk: GenericDataChunk):
        with BytesIO(chunk.raw_bytes) as stream:
            if chunk.header.unk_v3_1[0] == cls.__INVALID:
                one = cls.__INT.unpack_stream(stream)[0]
                return cls(None, one, None)
            else:
                name_a = stream.read(cls.__INT.unpack_stream(stream)[0]).decode("ascii")
                one = cls.__INT.unpack_stream(stream)[0]
                name_b = stream.read(cls.__INT.unpack_stream(stream)[0]).decode("ascii")
                return cls(name_a, one, name_b)


@dataclass
class CnbpChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: GenericDataChunk):
        return cls(chunk.raw_bytes)


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
    def convert(cls, chunk: GenericDataChunk):
        return cls(chunk.raw_bytes)


@dataclass
class ModlChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "MODL"
    VERSIONS = [1]

    mtrls: List[MtrlChunk]
    mesh: ModlMeshChunk
    skel: SkelChunk
    msbp: MsbpChunk
    dtbp: DtbpChunk
    mrks: MrksChunk

    @classmethod
    def convert(cls, chunk: FolderChunk):
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = ModelChunkConverter.convert_many(chunk.chunks)
        x = ChunkCollectionX.list2col(converted)
        mtrl = x.find(MtrlChunk, True)
        mesh = x.find(MeshChunk)
        skel = x.find(SkelChunk)
        msbp = x.find(MsbpChunk)
        dtbp = x.find(DtbpChunk)
        mrks = x.find(MrksChunk)
        assert len(chunk.chunks) == len(mtrl) + 5, (len(chunk.chunks), [c.header.name for c in chunk.chunks])
        return ModlChunk(chunk.header, mtrl, mesh, skel, msbp, dtbp, mrks)


@dataclass
class ModelChunky(RelicChunky):
    VERSIONS = [ChunkyVersion.Dow2]
    modl: ModlChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> ModelChunky:
        assert chunky.header.version in cls.VERSIONS, chunky.header.version
        assert len(chunky.chunks) == 1, len(chunky.chunks)
        converted = ModelChunkConverter.convert_many(chunky.chunks)
        x = ChunkCollectionX.list2col(converted)
        modl = x.find(ModlChunk)
        return ModelChunky(chunky.header, modl)


if __name__ == "__main__":
    # path = r"D:\Dumps\DOW_II\full_dump\art\race_ig\troops_wargear\heads\general\general_head.model"
    path = r"D:\Dumps\DOW_II\full_dump\art\race_ig\troops_wargear\armour\cadian_armour\cadian_armour.model"
    with open(path, "rb") as handle:
        chunky = RelicChunky._unpack(handle)
        model = ModelChunky.convert(chunky)
        print(model)

ModelChunkConverter = ChunkConverterFactory()
ModelChunkConverter.register(ModlChunk)
ModelChunkConverter.register(MtrlChunk)
ModelChunkConverter.register(MtrlInfoChunk)
