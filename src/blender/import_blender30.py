from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json
import math
# BLENDER ONLY
import bpy
import mathutils

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

    def to_matrix(self):
        pos = mathutils.Vector(self.position)
        x, y, z, w = self.rotation
        quat = w, x, y, z
        #        quat = None
        mat = mathutils.Matrix.LocRotScale(pos, quat, None)
        return mat


# IGNORES SCALE
def rotate_matrix(m, q):
    m_t = m.to_translation()
    m_q = m.to_quaternion()
    temp_m = m_q.to_matrix() @ q.to_matrix()
    temp_q = temp_m.to_quaternion()
    return mathutils.Matrix.LocRotScale(m_t, temp_q, None)


def apply_rotations(v: List, q):
    return [mathutils.Vector(p).rotate(q) for p in v]


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
        #        d['positions'] = fix_float3(d['positions'])
        #        d['normals'] = fix_float3(d['normals'])
        return RawMesh(**d)

    @property
    def has_implied_bone(self) -> bool:
        return len(self.bones) == 0


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


def create_mesh(data: RawMesh, root_rotation=None):
    triangles = []
    for t in data.sub_meshes.values():
        triangles.extend(t)

    if root_rotation:
        positions = apply_rotations(data.positions, root_rotation)
        normals = apply_rotations(data.normals, root_rotation)
    else:
        positions = data.positions
        normals = data.normals

    mesh = bpy.data.meshes.new(data.name)
    mesh.from_pydata(positions, [], triangles)
    mesh.update()
    for i, v in enumerate(mesh.vertices):
        v.normal = normals[i]

    obj = bpy.data.objects.new(data.name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def create_bone(armature, data: RawBone, parent_mat=None):
    bone = armature.edit_bones.new(data.name)
    bone.tail = mathutils.Vector([0, 1, 0])

    transform = data.transform
    mat = transform.to_matrix()

    bone_mat = mat
    if parent_mat:
        bone_mat = parent_mat @ mat

    const_rotation = mathutils.Quaternion([0, 0, 1], math.radians(90.0))  # Orient bones outward in direction of
    bone.matrix = rotate_matrix(bone_mat, const_rotation)

    for c in data.children:
        child_bone = create_bone(armature, c, bone_mat)
        child_bone.parent = bone

    return bone


def create_armature(data: RawBone, rotation=None):
    if not data:
        return None
    # Preserve state after runnign script
    old_mode, old_obj = None, None
    try:
        root = bpy.data.armatures.new("Armature")
        root_obj = bpy.data.objects.new("Armature", root)
        bpy.context.collection.objects.link(root_obj)

        old_obj = bpy.context.active_object
        bpy.context.view_layer.objects.active = root_obj

        old_mode = bpy.context.mode
        bpy.ops.object.mode_set(mode='EDIT')

        root_m = mathutils.Matrix.LocRotScale(None, rotation, None) if rotation else None
        for child in data.children:
            create_bone(root, child, root_m)
    finally:
        if old_obj:
            bpy.context.view_layer.objects.active = old_obj
        if old_mode:
            bpy.ops.object.mode_set(mode=old_mode)
    return root_obj


def create_skel_groups(skel, mesh, data: RawMesh):
    name2index = {}
    for i, b in enumerate(skel.bones):
        _ = mesh.vertex_groups.new(name=b.name)  # Ensure all bones exist
        name2index[b.name] = i

    if data.bone_weights:
        for vi, bw_data in enumerate(data.bone_weights):
            if bw_data[2] != 255:
                raise ValueError(bw_data[2])

            for bw, bwi in zip(bw_data[0], bw_data[1]):
                if bwi != 255:
                    mesh.vertex_groups[bwi].add([vi], bw, 'REPLACE')
    elif data.has_implied_bone and data.name in name2index:
        bwi = name2index[data.name]
        vgroup = mesh.vertex_groups[bwi]
        for i in range(len(data.positions)):
            vgroup.add([i], 1.0, 'REPLACE')


def rebuild_from_json(data: Dict) -> Tuple[str, List[RawMesh], RawBone]:
    name = data['name']
    meshes = data['meshes']
    meshes = [RawMesh.rebuild(m) for m in meshes]
    skel = data['skel']
    skel = RawBone.rebuild(skel)
    return name, meshes, skel

def build(path:str):
    with open(path, "r") as handle:
        json_data = json.load(handle)
        name, meshes, bones = rebuild_from_json(json_data)
        root_rot = mathutils.Quaternion([1, 0, 0], math.radians(90.0))
        skel_obj = create_armature(bones, root_rot)
        skel_obj.name = name
        for mesh_data in meshes:
            mesh = create_mesh(mesh_data, root_rot)
            mesh.parent = skel_obj  # Parent to Armature
            create_skel_groups(skel_obj.data, mesh, mesh_data)
            armature_mod = mesh.modifiers.new("Armature", "ARMATURE")  # name is 'Armature' (Default when using ui), class is 'ARMATURE'
            armature_mod.object = skel_obj

if __name__ == "__main__":
    r = r"C:\Users\moder\AppData\Local\ModernMAK\ArchiveTools\Relic-SGA\DOW_I\WHM_DUMP\DXP2Data-Whm-High"
    p = r"data\art\ebps\races\imperial_guard\troops"
    f = "baneblade"
    x = ".meshdata.json"
    path = rf"{r}\{p}\{f}{x}"
    build(path)
