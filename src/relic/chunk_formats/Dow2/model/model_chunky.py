from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from struct import Struct
from typing import List, Tuple, Optional

from relic.chunky import RelicChunky, AbstractRelicChunky, ChunkCollection, DataChunk, FolderChunk
from relic.file_formats.mesh_io import Float3, Float2
from relic.util.struct_util import unpack_from_stream


@dataclass
class MtrlInfoChunk:
    shader_name: str

    @classmethod
    def convert(cls, chunk: DataChunk):
        with BytesIO(chunk.data) as stream:
            name_len = unpack_from_stream(Struct("< L"), stream)[0]
            name = stream.read(name_len).decode("ascii")
            return cls(name)


class MaterialVarType(Enum):
    Texture = 9
    WorldMaybe = 8
    HighlightMaybe = 10
    MultiplierMaybe = 1
    OcclusionFlagMaybe = 0
    MatrixRow = 5


@dataclass
class VarChunk:
    property_name: str
    var_type: MaterialVarType

    args: Optional[Tuple] = None
    excess: Optional[Tuple[bytes, bytes]] = None

    @classmethod
    def convert(cls, chunk: DataChunk):
        with BytesIO(chunk.data) as stream:
            prop_len = unpack_from_stream(Struct("< L"), stream)[0]
            prop = stream.read(prop_len).decode("ascii")
            var_type_val = unpack_from_stream(Struct("< L"), stream)[0]
            var_type = MaterialVarType(var_type_val)
            buffer_len = unpack_from_stream(Struct("< L "), stream)[0]
            buffer = stream.read(buffer_len)
            # This acts as a soft assertion; if the buffer is too small, we'll get an unpack error
            # if either exceess has extra bytes, then somethings probably wrong, but I don't check for it
            # TODO check for it
            with BytesIO(buffer) as buffer_stream:
                if var_type == MaterialVarType.Texture:
                    args = buffer_stream.read(buffer_len).decode("ascii").strip("\0")
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.HighlightMaybe:
                    args = unpack_from_stream(Struct("< b"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.MatrixRow:
                    args = unpack_from_stream(Struct("< 4f"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.MultiplierMaybe:
                    args = unpack_from_stream(Struct("< f"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.OcclusionFlagMaybe:
                    args = unpack_from_stream(Struct("< L"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)
                elif var_type == MaterialVarType.WorldMaybe:
                    args = unpack_from_stream(Struct("< 16f"), buffer_stream)
                    excess = buffer_stream.read(), stream.read()
                    return VarChunk(prop, var_type, args, excess)

                raise NotImplementedError


@dataclass
class MtrlChunk:
    name: str
    info: MtrlInfoChunk
    vars: List[VarChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk):
        info = MtrlInfoChunk.convert(chunk.get_data_chunk("INFO"))
        vars = [VarChunk.convert(v) for v in chunk.get_data_chunks("VAR")]
        return MtrlChunk(chunk.header.name, info, vars)


@dataclass
class NodeChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class ImodDataChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class BVolChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class TrimVertex:
    position: Float3
    normal: Float3
    # unk_color: bytes
    uv: Float2
    unks: List[bytes]

    # A bit of reading for Float16s in Vertex Buffers:
    # 'https://www.yosoygames.com.ar/wp/2018/03/vertex-formats-part-1-compression/'
    #   I couldn't find the Normal using Float32 but the wierd placement of byte (0,0,255,0) got me thinking about the Half format
    #       Unfortunately; it wasn't that simple; but my experience with Voxels taught me about other ways to express normals ALA SNorm and UNorm
    #       I do think this is an SNorm Float16, which kinda works out for us, The article has some fancy talk for how to handle SNorm (due to the dreaded -32758

    @classmethod
    def parse(cls, data: bytes):
        with BytesIO(data) as stream:
            pos = unpack_from_stream(Struct("< 3f"), stream)
            # unks = unpack_from_stream(Struct("< 8B"), stream)  # 2?

            INT_16_MAX = 32767
            unks_raw = unpack_from_stream(Struct("< 7H"), stream)
            normal_raw = unpack_from_stream(Struct("< 3h"), stream)
            normal = [v / INT_16_MAX for v in normal_raw]
            # unk_b = unpack_from_stream(Struct("< 4B"), stream)  # RGBA?
            uv = unpack_from_stream(Struct("< 2f"), stream)
            return TrimVertex(pos, normal, uv, unks_raw)


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
    def convert(cls, chunk: DataChunk):
        with BytesIO(chunk.data) as stream:
            unk_a_count = unpack_from_stream(cls.__int_layout, stream)[0]
            unk_a = [unpack_from_stream(cls.__int3_Layout, stream) for _ in range(unk_a_count)]
            v_count = unpack_from_stream(cls.__int_layout, stream)[0]
            v_size = unpack_from_stream(cls.__int_layout, stream)[0]
            # Vertexes in this format are 'packed' instead of 'flattened'
            # This is probably why this format specifies the vertex size explicitly.
            vertexes = [TrimVertex.parse(stream.read(v_size)) for _ in range(v_count)]
            unk_b, index_count, unk_c, index_count_2 = unpack_from_stream(cls.__int4_Layout, stream)
            assert index_count == index_count_2
            indexes = [unpack_from_stream(cls.__short_layout, stream)[0] for _ in range(index_count)]
            name_size = unpack_from_stream(cls.__int_layout, stream)[0]
            name = stream.read(name_size).decode("ascii")
            skel_count = unpack_from_stream(cls.__int_layout, stream)[0]
            skels = []
            for _ in range(skel_count):
                skel_unks = unpack_from_stream(cls.__unk_skel_layout, stream)
                skel_name_len = unpack_from_stream(cls.__int_layout, stream)[0]
                skel_name = stream.read(skel_name_len).decode("ascii")
                skels.append((skel_name, skel_unks))
            unk_d, unk_e = unpack_from_stream(cls.__int2_layout, stream)
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

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        bvol = [BVolChunk.convert(c) for c in chunks.get_data_chunks("BVOL")]
        data = TrimDataChunk.convert(chunks.get_data_chunk("DATA"))
        return TrimChunk(bvol, data)


@dataclass
class ImodMeshChunk:
    name: str
    trim: TrimChunk

    @classmethod
    def convert(cls, chunk: FolderChunk):
        name = chunk.header.name
        trim = TrimChunk.convert(chunk.get_folder_chunk("TRIM"))
        return ImodMeshChunk(name, trim)


@dataclass
class ImodChunk:
    name: str
    data: ImodDataChunk
    meshs: List[ImodMeshChunk]

    @classmethod
    def convert(cls, chunk: FolderChunk):
        name = chunk.header.name
        data = ImodDataChunk.convert(chunk.get_data_chunk("DATA"))
        meshs = [ImodMeshChunk.convert(c) for c in chunk.get_folder_chunks("MESH")]
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
class MgrpChunk:
    node: NodeChunk
    mesh: MgrpMeshChunk

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        node = NodeChunk.convert(chunks.get_data_chunk("NODE"))
        mesh = MgrpMeshChunk.convert(chunks.get_folder_chunk("MESH"))
        return cls(node, mesh)


@dataclass
class ModlMeshChunk:
    mgrp: MgrpChunk

    @classmethod
    def convert(cls, chunks: ChunkCollection):
        mgrp = MgrpChunk.convert(chunks.get_folder_chunk("MGRP"))
        return cls(mgrp)


@dataclass
class SkelInfoChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class BoneChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


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
class MrksChunk:
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
