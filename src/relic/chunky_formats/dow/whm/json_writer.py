from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from enum import Enum
from json import JSONEncoder
from typing import TextIO, List, Any, Dict, Optional, Tuple

from .animation import AnimChunk, AnimDataBoneFrameInfo, AnimDataMeshFrameInfo
from .mesh import MslcChunk
from .shared import Byte
from .whm import WhmChunky, RsgmChunkV3, SkelChunk, MsgrChunk
from ....file_formats.mesh_io import Float3, Float2, Short3, Float4


def flip_float3(v: Float3, flip_x: bool = False, flip_y: bool = False, flip_z: bool = False) -> Float3:
    if not any([flip_x, flip_y, flip_z]):  # Used a list to avoid confusion with any((flip_x,flip_y,flip_z))
        return v
    x, y, z = v
    if flip_x:
        x *= -1
    if flip_y:
        y *= -1
    if flip_z:
        z *= -1
    return x, y, z


@dataclass
class SimpleTransform:
    position: Float3
    rotation: Float4


@dataclass
class RawMesh:
    name: str
    positions: List[Float3]
    normals: List[Float3]
    bones: Dict[int, str]
    bone_weights: Optional[List[List[Tuple[Float3, Byte]]]]
    uvs: List[Float2]
    sub_meshes: Dict[str, List[Short3]]

    @classmethod
    def convert_from_mslc(cls, chunk: MslcChunk) -> RawMesh:
        mesh = chunk.data
        name = chunk.header.name
        # DO NOT PERFORM ANY MODIFICATIONS
        #   Let importer handle it to keep it in one location
        positions = mesh.vertex_data.positions
        normals = mesh.vertex_data.normals
        # positions = [flip_float3(p, flip_x=True) for p in mesh.vertex_data.positions]
        # normals = [flip_float3(n, flip_x=True) for n in mesh.vertex_data.normals]
        bones = {b.index: b.name for b in mesh.bones}
        bone_weights = None
        if mesh.vertex_data.bone_weights:
            bone_weights = []
            for bwd in mesh.vertex_data.bone_weights:
                w = []
                t = 0
                for i in range(4):
                    bi = bwd[1][i]
                    if bi == 255:
                        break
                    if i == 3:
                        bw = 1.0 - t
                    else:
                        bw = bwd[0][i]
                        t += bw
                    w.append((bi, bw))
                bone_weights.append(w)

        uvs = mesh.vertex_data.uvs
        indexes = {sm.texture_path: sm.triangles for sm in mesh.sub_meshes}
        return RawMesh(name, positions, normals, bones, bone_weights, uvs, indexes)

    @classmethod
    def convert_from_msgr(cls, chunk: MsgrChunk) -> List[RawMesh]:
        return [cls.convert_from_mslc(c) for c in chunk.mslc]


@dataclass
class RawBone:
    name: str
    transform: SimpleTransform
    children: List[RawBone]

    @classmethod
    def convert_from_skel(cls, chunk: SkelChunk) -> RawBone:
        root = RawBone(chunk.header.name, None, [])
        tree = [RawBone(s.name, SimpleTransform(s.pos, s.quaternion), []) for s in chunk.bones]
        for i, b in enumerate(chunk.bones):
            current = tree[i]
            if b.parent_index == -1:
                parent = root
            else:
                parent = tree[b.parent_index]
            parent.children.append(current)
        return root


def time_to_frame(frame_time: float, frame_count: int) -> int:
    return round(frame_time * (frame_count - 1))


@dataclass
class RawAnimBone:
    name: str
    pos: Dict[int, Float3]
    rot: Dict[int, Float4]
    stale: bool

    @classmethod
    def convert(cls, data: AnimDataBoneFrameInfo, frame_count: int) -> RawAnimBone:
        p = {time_to_frame(f, frame_count): v[1:] for f, v in data.positions.items()}
        r = {time_to_frame(f, frame_count): v[1:] for f, v in data.rotations.items()}
        return cls(data.name, p, r, data.stale)

    @classmethod
    def ignorable(cls, data: AnimDataBoneFrameInfo) -> bool:
        return len(data.positions) + len(data.rotations) == 0


@dataclass
class RawAnimMesh:
    name: str
    mode: int
    visibility: Dict[int, float]
    unks: Tuple

    @classmethod
    def convert(cls, data: AnimDataMeshFrameInfo, frame_count: int) -> RawAnimMesh:
        vis = {time_to_frame(f, frame_count): v[1:] for f, v in data.visibility.items()}
        return cls(data.name, data.mode, vis, data.unks)  # one of those unks is probably stale... ? But why mark it stale in the vis, where it should be implied?

    @classmethod
    def ignorable(cls, data: AnimDataMeshFrameInfo) -> bool:
        return len(data.visibility) + len(data.visibility) == 0


@dataclass
class RawAnim:
    name: str
    key_frames: int  # used to init animaition
    bones: List[RawAnimBone]
    meshes: List[RawAnimMesh]

    # Since idk what unks animates, i've ignored it

    @classmethod
    def convert_from_anim(cls, anim: AnimChunk) -> RawAnim:
        d = anim.data
        bones = [RawAnimBone.convert(b, d.key_frames) for b in d.bones if not RawAnimBone.ignorable(b)]
        meshes = [RawAnimMesh.convert(m, d.key_frames) for m in d.meshes if not RawAnimMesh.ignorable(m)]
        return cls(anim.header.name, d.key_frames, bones, meshes)

    @classmethod
    def convert_from_anim_list(cls, anims: List[AnimChunk]) -> List[RawAnim]:
        return [cls.convert_from_anim(a) for a in anims]


class SimpleJsonEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, Enum):
            return {o.name: o.value}
        else:
            return super().default(o)


def write_whm(stream: TextIO, whm: WhmChunky, pretty: bool = True):
    # After browsing some of those old forums on the Way Back Machine (wish i'd remembered captured the url)
    #   Something about Tread L and Tread R being special bones; those meshes likely auto weight themselves to their special bone?
    # Putting this here since this is the 'best' place I can think of
    #   Some objects have skel's but no bones (vehicles do this alot)
    #       I thought that maybe it was hidden elsewhere, but I decided ot play SS to look at the animations
    #       After 15 minutes I got a blane-blade and carefully watched it raise hell
    #           Despite my initial thoughts; that the cannon and barrels retracted after firing; the animations simply jolt the gun back to achieve a similar, cheaper effect
    #   My conclusion is a skel's bone is implicitly weighted IFF (if anf only if) no bones are listed as bone weights AND the mesh name matches a bone name
    #       Semi-Related, MARKs seem to be empty objects, should try listing that in the OBJ/JSON
    if isinstance(whm.rsgm, RsgmChunkV3):
        meshes = RawMesh.convert_from_msgr(whm.rsgm.msgr)
        skel = RawBone.convert_from_skel(whm.rsgm.skel) if whm.rsgm.skel else None
        name = whm.rsgm.header.name
        anim = RawAnim.convert_from_anim_list(whm.rsgm.anim)
        d = {'name': name, 'skel': skel, 'meshes': meshes, 'animations': anim}
        try:
            json.dump(d, stream, indent=(4 if pretty else None), cls=SimpleJsonEncoder)
        except Exception as e:
            print(e)
            raise
    else:
        raise NotImplementedError
