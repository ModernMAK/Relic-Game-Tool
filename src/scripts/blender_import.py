from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import bpy
import json

Float2 = Tuple[float, float]
Float3 = Tuple[float, float, float]
Float4 = Tuple[float, float, float, float]
Short3 = Tuple[int, int, int]


@dataclass
class SimpleTransform:
    position: Float3
    rotation: Float4

    @classmethod
    def rebuild(cls, d: Optional[Dict]) -> SimpleTransform:
        if not d:
            return None
        return SimpleTransform(**d)


@dataclass
class RawMesh:
    positions: List[Float3]
    normals: List[Float3]
    uvs: List[Float2]
    sub_meshes: Dict[str, List[Short3]]

    @classmethod
    def rebuild(cls, d: Optional[Dict]) -> RawMesh:
        if not d:
            return None
        return RawMesh(**d)


@dataclass
class RawObject:
    name: str
    transform: SimpleTransform
    mesh: Optional[RawMesh]
    children: List[RawObject]

    @classmethod
    def rebuild(cls, d: Dict) -> RawObject:
        name = d['name']
        transform = SimpleTransform.rebuild(d['transform'])
        mesh = RawMesh.rebuild(d['mesh'])
        children = [RawObject.rebuild(c) for c in d['children']]
        return RawObject(name, transform, mesh, children)


def create_mesh(data: RawObject):
    if data.mesh:
        triangles = []
        for t in data.mesh.sub_meshes:
            triangles.extend(t)

        mesh = bpy.data.meshes.new(data.name)
        print(data.mesh.positions)
        mesh.from_pydata(data.mesh.positions, [], triangles)
        mesh.update()
        for i, v in enumerate(mesh.vertices):
            v.normal = mesh.normals[i]

        for name, indexes in data.mesh.sub_meshes:
            uv = mesh.uv_textures.new()
            uv.name = name
    else:
        mesh = None

    obj = bpy.data.objects.new(data.name, mesh)
    bpy.context.collection.objects.link(obj)

    child_objs = [create_mesh(c) for c in data.children]
    for c in child_objs:
        c.parent = obj


if __name__ == "__main__":
    path = r"C:\Users\moder\AppData\Local\ModernMAK\ArchiveTools\Relic-SGA\DOW_I\WHM_DUMP\DXP2Data-Whm-High\data\art\ebps\races\imperial_guard\troops\baneblade.meshdata.json"
    with open(path, "r") as handle:
        json_data = json.load(handle)
        data = RawObject.rebuild(json_data)
        create_mesh(data)
