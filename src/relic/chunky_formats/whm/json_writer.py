from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from enum import Enum
from json import JSONEncoder
from typing import TextIO, List, Any, Dict, Optional, Tuple

from relic.chunky_formats.whm.whm import MslcChunk, WhmChunky, RsgmChunkV3, Byte, Byte3, SkelChunk, MsgrChunk
from relic.file_formats.mesh_io import Float3, Float2, Short3, Float4


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
    bone_weights: Optional[List[Tuple[Float3, Byte3, Byte]]]
    uvs: List[Float2]
    sub_meshes: Dict[str, List[Short3]]

    @classmethod
    def convert_from_mslc(cls, chunk: MslcChunk) -> RawMesh:
        mesh = chunk.data
        name = chunk.header.name
        positions = [flip_float3(p, flip_x=True) for p in mesh.vertex_data.positions]
        normals = [flip_float3(n, flip_x=True) for n in mesh.vertex_data.normals]
        bones = {b.index: b.name for b in mesh.bones}
        bone_weights = mesh.vertex_data.bone_weights
        uvs = mesh.vertex_data.uvs
        indexes = {sm.texture_path: sm.triangles for sm in mesh.sub_meshes}
        return RawMesh(name, positions, normals, bones, bone_weights, uvs, indexes)

    @classmethod
    def convert_from_msgr(cls, chunk: MsgrChunk) -> List[RawMesh]:
        return [cls.convert_from_mslc(c) for c in chunk.mslc]


@dataclass
class RawBone:
    name: str
    # index: int
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

        # bone_lookup = {}
        # bone_lookup[-1] = RawBone(None, -1, None, [])
        # for i, bone in enumerate(chunk.bones):
        #     t = SimpleTransform(bone.pos, bone.quaternion)
        #     bone_lookup[i] = RawBone(bone.name, i, t, [])
        # for i, _ in enumerate(chunk.bones):
        #     parent = bone_lookup[_.parent_index]
        #     current = bone_lookup[i]
        #     parent.children.append(current)
        # return bone_lookup[-1]


class SimpleJsonEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, Enum):
            return {o.name: o.value}
        else:
            return super().default(o)


def write_whm(stream: TextIO, whm: WhmChunky, pretty: bool = True):
    if isinstance(whm.rsgm, RsgmChunkV3):
        meshes = RawMesh.convert_from_msgr(whm.rsgm.msgr)
        skel = RawBone.convert_from_skel(whm.rsgm.skel)
        name = whm.rsgm.header.name
        d = {'name': name, 'skel': skel, 'meshes': meshes}
        try:
            json.dump(d, stream, indent=(4 if pretty else None), cls=SimpleJsonEncoder)
        except Exception as e:
            print(e)
            raise
    else:
        raise NotImplementedError
