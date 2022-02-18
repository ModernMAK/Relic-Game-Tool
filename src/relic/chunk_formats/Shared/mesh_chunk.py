from dataclasses import dataclass
from io import BytesIO
from struct import Struct
from typing import List, Tuple, Optional

from relic.chunky import FolderChunk, ChunkCollection, DataChunk
from relic.file_formats.mesh_io import Float3, Float2
from relic.util.struct_util import unpack_from_stream


@dataclass
class BVolChunk:
    data: bytes

    @classmethod
    def convert(cls, chunk: DataChunk):
        return cls(chunk.data)


@dataclass
class MrfmChunk(DataChunk):
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
    def __parse_40(cls,data:bytes) -> 'TrimVertex':
        with BytesIO(data) as stream:
            pos = unpack_from_stream(Struct("< 3f"), stream)
            # unks = unpack_from_stream(Struct("< 8B"), stream)  # 2?

            INT_16_MAX = 32767
            unks_raw = unpack_from_stream(Struct("< 14B"), stream)
            normal_raw = unpack_from_stream(Struct("< 3h"), stream)
            normal = [v / INT_16_MAX for v in normal_raw]
            # unk_b = unpack_from_stream(Struct("< 4B"), stream)  # RGBA?
            uv = unpack_from_stream(Struct("< 2f"), stream)
            return TrimVertex(pos, normal, uv, unks_raw)

    @classmethod
    def __parse_32(cls,data:bytes) -> 'TrimVertex':
        with BytesIO(data) as stream:

            pos = unpack_from_stream(Struct("< 3f"), stream)
            unks_raw = unpack_from_stream(Struct("< 6B"), stream)
            INT_16_MAX = 32767
            normal_raw = unpack_from_stream(Struct("< 3h"), stream)
            normal = [v / INT_16_MAX for v in normal_raw]

            uv = unpack_from_stream(Struct("< 2f"), stream)
            return TrimVertex(pos, normal, uv, unks_raw)

    @classmethod
    def __parse_24(cls,data:bytes) -> 'TrimVertex':
        with BytesIO(data) as stream:
            pos = unpack_from_stream(Struct("< 3f"), stream)
            unks_raw = unpack_from_stream(Struct("< 4B"), stream)
            # INT_16_MAX = 32767
            # normal_raw = unpack_from_stream(Struct("< 3h"), stream)
            # normal = [v / INT_16_MAX for v in normal_raw]
            #
            uv = unpack_from_stream(Struct("< 2f"), stream)
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
