from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from enum import Enum
from json import JSONEncoder
from typing import TextIO, List, Any, Dict, Optional

from relic.chunky_formats.whm.whm import MslcChunk, WhmChunky, RsgmChunkV3
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
    positions: List[Float3]
    normals: List[Float3]
    uvs: List[Float2]
    sub_meshes: Dict[str, List[Short3]]

    @classmethod
    def convert_from_mslc(cls, chunk: MslcChunk) -> RawMesh:
        mesh = chunk.data
        positions = [flip_float3(p, flip_x=True) for p in mesh.positions()]
        normals = [flip_float3(n, flip_x=True) for n in mesh.normals()]
        uvs = mesh.uvs()
        indexes = {name: buffer for name, buffer, _ in mesh.triangle_buffers}
        return RawMesh(positions, normals, uvs, indexes)


@dataclass
class RawObject:
    name: str
    transform: SimpleTransform
    mesh: Optional[RawMesh]
    children: List[RawObject]

    @classmethod
    def convert_from_rsgm(cls, chunk: RsgmChunkV3) -> RawObject:
        # build skeleton OBJs:
        root = RawObject(chunk.header.name, None, None, [])
        if chunk.skel:
            _ = chunk.skel.transforms
            tree = [RawObject(s.name, SimpleTransform(s.pos, s.quaternion), None, []) for s in chunk.skel.transforms]
            for i, s in enumerate(chunk.skel.transforms):
                current = tree[i]
                if s.parent_index == -1:
                    parent = root
                else:
                    parent = tree[s.parent_index]
                parent.children.append(current)

            meshes = {n.name: RawMesh.convert_from_mslc(m) for n, m in zip(chunk.msgr.data.items, chunk.msgr.mslc)}
            used = set()
            for o in tree:
                if o.name in meshes:
                    o.mesh = meshes[o.name]
                    used.add(o.name)
            assert len(used) == len(meshes), (len(used), len(meshes), [n for n,_  in meshes.items() if n not in used], used)
        else:
            children = [RawObject(n, None, RawMesh.convert_from_mslc(m), []) for n, m in zip(chunk.msgr.data.items, chunk.msgr.mslc)]
            root.children.extend(children)
        return root

        # names = [_.name for _ in chunk.msgr.data.items]
        # meshes = {n.name:RawMesh.convert_from_mslc(m) for n,m in zip(chunk.msgr.data.items,chunk.msgr.mslc)}
        # objs: List[RawObject] = [RawObject(None, None, meshes[i], []) for i in range(len(meshes))]
        # obj_lookup: Dict[str, RawObject] = {names[i]: objs[i] for i in range(len(names))}
        # Hierarchy
        # root = RawObject(chunk.header.name, None, None, [])
        # if chunk.skel:
        #     transforms = [SimpleTransform(_.pos, _.quaternion) for _ in chunk.skel.transforms]
        #     for i, s in enumerate(chunk.skel.transforms):
        #         if s.name in obj_lookup:
        #                 root.name = s.name
        #                 root.transform = transforms[i]
        #             else:
        #                 parent = objs[s.parent_index] if s.parent_index >= 0 else root
        #                 current = obj_lookup[s.name]
        #                 current.transform = transforms[i]
        #                 parent.children.append(current)
        #         else:
        #             current = RawObject(s.name,transforms[i],None,[])
        #
        # elif len(meshes) == 1:
        #     root.mesh = meshes[0]
        # else:
        #     root.children = objs
        # return root


class SimpleJsonEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, Enum):
            return {o.name: o.value}
        else:
            return o


def write_whm(stream: TextIO, whm: WhmChunky, pretty: bool = True):
    if isinstance(whm.rsgm, RsgmChunkV3):
        raw_obj = RawObject.convert_from_rsgm(whm.rsgm)
        try:
            json.dump(raw_obj, stream, indent=(4 if pretty else None), cls=SimpleJsonEncoder)
        except Exception as e:
            print(e)
            raise
    else:
        raise NotImplementedError
