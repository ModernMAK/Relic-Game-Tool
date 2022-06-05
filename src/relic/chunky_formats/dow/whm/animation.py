from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Dict, Tuple, BinaryIO, List

from serialization_tools.ioutil import has_data
from serialization_tools.structx import Struct
from serialization_tools.vstruct import VStruct

from ....chunky import ChunkType, AbstractChunk, GenericDataChunk, FolderChunk
from ...convertable import ChunkConverterFactory
from ...util import UnimplementedDataChunk, ChunkCollectionX


@dataclass
class AnbvChunk(UnimplementedDataChunk):
    # Normally always 12 (or 16, forgot which) '\x00' bytes
    #   If I had to guess; animation bounding volume
    CHUNK_ID = "ANBV"
    CHUNK_TYPE = ChunkType.Data


@dataclass
class AnimDataBoneFrameInfo:
    name: str
    positions: Dict[int, Tuple]
    rotations: Dict[int, Tuple]
    # According to "https://forums.revora.net/topic/116206-tutorial-install-and-set-up-3ds-max-2008/"
    #    'It should also say that all the bones are stale=yes so the vis file doesn't block other animations from playing.'
    stale: bool  # I have no idea how I'm going to emulate this in blender
    # Also lists how meshes are chosen when multiple are given
    # '''You can also group motions together and have the game choose one randomly when the unit spawns. For example:
    # Create 3 vis animations, each one makes a different head visible.
    # Then make 3 motions, one for each head.
    # Then put those in a motion group, and the game will randomize the heads.'''
    # Really neat way of abusing their animation engine to add variety
    #   IMO, you could go so far as adding completely different models (Say for example; a tyranid pack)
    #       Yes, I'm aware of the tyranid mod, but since they explicitly state not to dump their models, I haven't looked at em, but if they aren't doing this, they are missing out.
    #           Although it may be a problem if the engine still is calculating them, which would be a massive oversight imo; since they made this random mesh choice a feature
    NAME_LAYOUT = VStruct("v")
    COUNT_LAYOUT = Struct("i")
    POS_KEYFRAME_LAYOUT = Struct("4f")
    ROT_KEYFRAME_LAYOUT = Struct("5f")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> AnimDataBoneFrameInfo:
        name = cls.NAME_LAYOUT.unpack_stream(stream)[0]
        name = name.decode("ascii")
        pos_frames = {}
        rot_frames = {}
        # POS
        key_pos_frames = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
        for _ in range(key_pos_frames):
            frame, kf_x, kf_y, kf_z = cls.POS_KEYFRAME_LAYOUT.unpack_stream(stream)
            pos_frames[frame] = (frame, kf_x, kf_y, kf_z)
        # ROT
        key_rot_frames = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
        for _ in range(key_rot_frames):
            frame, kf_x, kf_y, kf_z, kf_w = cls.ROT_KEYFRAME_LAYOUT.unpack_stream(stream)
            rot_frames[frame] = (frame, kf_x, kf_y, kf_z, kf_w)
        # FLAG
        unk = stream.read(1)
        assert unk in [b'\00', b'\01'], unk
        flag = (b'\01' == unk)
        return cls(name, pos_frames, rot_frames, flag)


@dataclass
class AnimDataMeshFrameInfo:
    NAME_LAYOUT = VStruct("v")
    MESH_UNKS_LAYOUT = Struct("3i")
    COUNT_LAYOUT = Struct("i")
    VISIBILITY_LAYOUT = Struct("2f")

    name: str
    mode: int
    unks: Tuple[int, int, int, int]
    visibility: Dict[int, Tuple]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> AnimDataMeshFrameInfo:
        name = cls.NAME_LAYOUT.unpack_stream(stream)[0]
        name = name.decode("ascii")
        unks = cls.MESH_UNKS_LAYOUT.unpack_stream(stream)
        mode = unks[0]
        try:
            assert mode in [0, 2], mode
        except Exception as e:
            raise
        key_frame_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
        if mode == 2:
            key_frame_count -= 1  # Meshes have an extra frame?
            unk2 = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
            assert unk2 == 0
            unk3 = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
        else:
            unk2, unk3 = None, None

        visibility = {}
        for _ in range(key_frame_count):
            frame, value = cls.VISIBILITY_LAYOUT.unpack_stream(stream)
            visibility[frame] = (frame, value)

        return cls(name, mode, (unks[1], unks[2], unk2, unk3), visibility)


@dataclass
class AnimDataUnkFrameInfo:
    name: str
    positions: Dict[int, Tuple]
    rotations: Dict[int, Tuple]

    NAME_LAYOUT = VStruct("v")
    COUNT_LAYOUT = Struct("i")
    POS_KEYFRAME_LAYOUT = Struct("4f")
    ROT_KEYFRAME_LAYOUT = Struct("5f")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> AnimDataUnkFrameInfo:
        name = cls.NAME_LAYOUT.unpack_stream(stream)[0]
        name = name.decode("ascii")
        pos_frames = {}
        rot_frames = {}
        # POS
        key_pos_frames = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
        for _ in range(key_pos_frames):
            frame, kf_x, kf_y, kf_z = cls.POS_KEYFRAME_LAYOUT.unpack_stream(stream)
            pos_frames[frame] = (frame, kf_x, kf_y, kf_z)
        # ROT
        key_rot_frames = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
        for _ in range(key_rot_frames):
            frame, kf_x, kf_y, kf_z, kf_w = cls.ROT_KEYFRAME_LAYOUT.unpack_stream(stream)
            rot_frames[frame] = (frame, kf_x, kf_y, kf_z, kf_w)
        return cls(name, pos_frames, rot_frames)


@dataclass
class AnimDataChunk(AbstractChunk):
    CHUNK_ID = "DATA"
    CHUNK_TYPE = ChunkType.Data
    VERSIONS = [1, 2]  # ig\troops\battle_tank uses #1, basilisk uses #2, may use different anim layout?

    LAYOUT = Struct("i i i")
    COUNT_LAYOUT = Struct("i")

    key_frames: int
    bones: List[AnimDataBoneFrameInfo]
    meshes: List[AnimDataMeshFrameInfo]
    # Cams or markers, lacks stale flag, so it doens't support layering, which makes sense for cams (why turn it off, its not visible, and it shouldn't be stacking since it's technically just a point in space)
    # Markers (TMK) are also just points in space, but they might need to be layered; like an FX which wiggles or something
    unks: List[AnimDataUnkFrameInfo]

    @classmethod
    def convert(cls, chunk: GenericDataChunk) -> AnimDataChunk:
        version = chunk.header.version
        assert version in cls.VERSIONS, version
        with BytesIO(chunk.raw_bytes) as stream:
            # Never actually used frame count, I assumed it was FPS, and I'd multiply, but it's not clean 24,30,60 it's things like 37
            # I assumed it was the total number of keyframes across the anim, but 'frames' are floats inside the parts
            #   So its probably the animation length in frames
            frame_count, unk, bone_count = cls.LAYOUT.unpack_stream(stream)
            bones = [AnimDataBoneFrameInfo.unpack(stream) for _ in range(bone_count)]
            # MESH
            mesh_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
            mesh = [AnimDataMeshFrameInfo.unpack(stream) for _ in range(mesh_count)]

            # Missing in V1
            if version in [2]:
                unk_count = cls.COUNT_LAYOUT.unpack_stream(stream)[0]
                unks = [AnimDataUnkFrameInfo.unpack(stream) for _ in range(unk_count)]
            else:
                unks = None
            try:
                assert not has_data(stream), stream.read()
            except Exception as e:
                raise
            return cls(chunk.header, frame_count, bones, mesh, unks)


@dataclass
class AnimChunk(AbstractChunk):
    CHUNK_TYPE = ChunkType.Folder
    CHUNK_ID = "ANIM"
    VERSIONS = [3]

    data: AnimDataChunk
    anbv: AnbvChunk

    @classmethod
    def convert(cls, chunk: FolderChunk) -> AnimChunk:
        assert chunk.header.version in cls.VERSIONS, chunk.header.version
        converted = AnimChunkConverter.convert_many(chunk.chunks)
        coll = ChunkCollectionX.list2col(converted)
        data = coll.find(AnimDataChunk)
        anbv = coll.find(AnbvChunk)

        assert len(chunk.chunks) == 2
        return AnimChunk(chunk.header, data, anbv)


def add_anim_chunk_converter(conv):
    conv.register(AnimDataChunk)
    conv.register(AnbvChunk)
    return conv


def generate_anim_chunk_converter():
    conv = ChunkConverterFactory()
    add_anim_chunk_converter(conv)
    return conv


AnimChunkConverter = generate_anim_chunk_converter()
