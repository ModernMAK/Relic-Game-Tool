from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import bpy
import json

Float2 = Tuple[float, float]
Float3 = Tuple[float, float, float]
Float4 = Tuple[float, float, float, float]
Short3 = Tuple[int, int, int]
Byte3 = Tuple[int, int, int]
Byte = int


@dataclass
class SimpleTransform:
    position: Float3
    rotation: Float4

    @classmethod
    def rebuild(cls, d: Optional[Dict]) -> Optional[SimpleTransform]:
        if not d:
            return None
        return SimpleTransform(**d)


# Fix CoordSys alignment for pos/norm
def fix_float3(items: List[Float3]) -> List[Float3]:
    return [(x, z, y) for (x, y, z) in items]


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
    def rebuild(cls, d: Optional[Dict]) -> Optional[RawMesh]:
        if not d:
            return None
        d['positions'] = fix_float3(d['positions'])
        d['normals'] = fix_float3(d['normals'])
        return RawMesh(**d)


@dataclass
class RawBone:
    name: str
    transform: SimpleTransform
    children: List[RawBone]

    @classmethod
    def rebuild(cls, d: Dict) -> RawBone:
        name = d['name']
        transform = SimpleTransform.rebuild(d['transform'])
        children = [RawBone.rebuild(c) for c in d['children']]
        return RawBone(name, transform, children)


def create_mesh(data: RawMesh):
    triangles = []
    for t in data.sub_meshes.values():
        triangles.extend(t)

    mesh = bpy.data.meshes.new(data.name)
    mesh.from_pydata(data.positions, [], triangles)
    mesh.update()
    for i, v in enumerate(mesh.vertices):
        v.normal = data.normals[i]

    # for name, indexes in data.sub_meshes:
    #     uv = mesh.uv_textures.new()
    #     uv.name = name

    obj = bpy.data.objects.new(data.name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def rebuild_from_json(data: Dict) -> Tuple[str, List[RawMesh], RawBone]:
    name = data['name']
    meshes = data['meshes']
    meshes = [RawMesh.rebuild(m) for m in meshes]
    skel = data['skel']
    skel = RawBone.rebuild(skel)
    return name, meshes, skel


if __name__ == "__main__":
    path = r"C:\Users\moder\AppData\Local\ModernMAK\ArchiveTools\Relic-SGA\DOW_I\WHM_DUMP\DXP2Data-Whm-High\data\art\ebps\races\imperial_guard\troops\baneblade.meshdata.json"
    with open(path, "r") as handle:
        json_data = json.load(handle)
        name, meshes, bones = rebuild_from_json(json_data)

        container_obj = bpy.data.objects.new(name, None)
        bpy.context.collection.objects.link(container_obj)

        for mesh in meshes:
            mesh_obj = create_mesh(mesh)
            mesh_obj.parent = container_obj
