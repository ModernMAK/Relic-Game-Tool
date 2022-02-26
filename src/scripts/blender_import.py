from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json
# BLENDER ONLY
import bpy
import mathutils

Float2 = Tuple[float, float]
Float3 = Tuple[float, float, float]
Float4 = Tuple[float, float, float, float]
Short3 = Tuple[int, int, int]
Byte3 = Tuple[int, int, int]
Byte = int


class CoordConv:
    # DOH, 3dsmax, not maya

    @classmethod
    def blender2threeds_pos(cls, pos: Float3) -> Float3:
        # Left, Foward, Up => Right Up Forward
        bx, by, bz = pos
        return -bx, bz, by

    @classmethod
    def threeds2blender_pos(cls, pos: Float3) -> Float3:
        # Right Up Forward=>Left, Foward, Up
        tx, ty, tz = pos
        return -tx, tz, ty

    @classmethod
    def blender2threeds_rot(cls, rot: Float4) -> Float4:
        x, y, z, w = rot
        # Blender: RHS?
        # Maya: RHS?
        pos = x, y, z
        w *= -1
        x, y, z = cls.blender2threeds_pos(pos)
        return x, y, z, w

    @classmethod
    def threeds2blender_rot(cls, rot: Float4) -> Float4:
        x, y, z, w = rot
        # Blender: RHS?
        # Maya: RHS?
        pos = x, y, z
        w *= -1
        x, y, z = cls.threeds2blender_pos(pos)
        return x, y, z, w

    @classmethod
    def blender2maya_rot(cls, rot: Float4) -> Float4:
        x, y, z, w = rot
        # Blender: RHS?
        # Maya: RHS?
        pos = x, y, z
        # w *= -1
        x, y, z = cls.blender2maya_pos(pos)
        return x, y, z, w

    @classmethod
    def maya2blender_rot(cls, rot: Float4) -> Float4:
        x, y, z, w = rot
        # Blender: RHS?
        # Maya: RHS?
        pos = x, y, z
        # w *= -1
        x, y, z = cls.maya2blender_pos(pos)
        return x, y, z, w

    @classmethod
    def blender2maya_pos(cls, pos: Float3) -> Float3:
        # Blender: Right, Back, Up
        bx, by, bz = pos
        # Maya: Right, Up, Forward
        return bx, bz, -by

    @classmethod
    def maya2blender_pos(cls, pos: Float3) -> Float3:
        # Maya: Right, Up, Forward
        mx, my, mz = pos
        # Blender: Right, Back, Up
        return mx, -mz, my


def data2quat(data: Float4):
    # DOH
    # Blender expects w,xyz
    x, y, z, w = data
    return mathutils.Quaternion([w, x, y, z])


@dataclass
class SimpleTransform:
    position: Float3
    rotation: Float4

    @classmethod
    def rebuild(cls, d: Optional[Dict]) -> Optional[SimpleTransform]:
        if not d:
            return None
        return SimpleTransform(**d)

    def apply_fix(self) -> SimpleTransform:
        px, py, pz = self.position
        px, py, pz = px, py, pz
        position = px, py, pz

        qx, qy, qz, qw = self.rotation
        #        qx, qy, qz, qw = qx, qz, qy, qw
        rotation = qx, qy, qz, qw
        return SimpleTransform(position, rotation)

    def as_matrix(self):
        pos = mathutils.Vector(self.position)
        quat = data2quat(self.rotation)
        #        quat = mathutils.Quaternion(self.rotation)
        mat = mathutils.Matrix.LocRotScale(pos, quat, None)
        return mat


# Fix CoordSys alignment for pos/norm
# -x is flipped beforehand
def fix_float3(items: List[Float3]) -> List[Float3]:
    return [(x, z, y) for (x, y, z) in items]


#
# def unfix_posnorm(items: List[Float3]) -> List[Float3]:
#     return [(-x,y,  y) for (x, y, z) in items]


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


def create_bone(armature, data: RawBone, parent_mat=None):
    bone = armature.edit_bones.new(data.name)
    bone.tail = mathutils.Vector([0, 0, 0.25])

    transform = data.transform
    #    print(transform.rotation)
    transform = transform.apply_fix()
    #    print(transform.rotation)
    #    if -0.1 <= (transform.rotation.x[0] - transform.rotation[3]) <= 0.1
    #        raise NotImplementedError
    mat = transform.as_matrix()

    bone_mat = mat
    if parent_mat and True:
        bone_mat = parent_mat @ mat

    bone.matrix = bone_mat

    for c in data.children:
        child_bone = create_bone(armature, c, bone_mat)
        child_bone.parent = bone
    #        child_bone.use_connect = True

    return bone


def create_armature(data: RawBone):
    if not data:
        return None
    # Preserve state after runnign script
    old_mode, old_obj = None, None
    try:
        root = bpy.data.armatures.new("Armature")
        root_obj = bpy.data.objects.new("Armature", root)
        bpy.context.collection.objects.link(root_obj)

        old_obj = bpy.context.active_object
        #        bpy.context.active_object = root_obj
        bpy.context.view_layer.objects.active = root_obj

        old_mode = bpy.context.mode
        bpy.ops.object.mode_set(mode='EDIT')

        # Root shouldn't have Transform, being a contianer
        #   Start bones from children
        root_m = mathutils.Matrix.LocRotScale(None, mathutils.Euler([-90.0 / 2.0 * 1.5, 0, 0]).to_quaternion(), None)
        for child in data.children:
            create_bone(root, child, root_m)
    finally:
        if old_obj:
            bpy.context.view_layer.objects.active = old_obj
        if old_mode:
            bpy.ops.object.mode_set(mode=old_mode)
    return root_obj


def create_skel_groups(skel, mesh, data: RawMesh):
    for b in skel.bones:
        _ = mesh.vertex_groups.new(name=b.name)  # Ensure all bones exist
    if data.bone_weights:
        for vi, bw_data in enumerate(data.bone_weights):
            if bw_data[2] != 255:
                raise ValueError(bw_data[2])

            for bw, bwi in zip(bw_data[0], bw_data[1]):
                if bwi != 255:
                    mesh.vertex_groups[bwi].add([vi], bw, 'REPLACE')


def rebuild_from_json(data: Dict) -> Tuple[str, List[RawMesh], RawBone]:
    name = data['name']
    meshes = data['meshes']
    meshes = [RawMesh.rebuild(m) for m in meshes]
    skel = data['skel']
    skel = RawBone.rebuild(skel)
    return name, meshes, skel


if __name__ == "__main__":
    r = r"C:\Users\moder\AppData\Local\ModernMAK\ArchiveTools\Relic-SGA\DOW_I\WHM_DUMP\DXP2Data-Whm-High"
    p = r"data\art\ebps\races\imperial_guard\troops"
    f = "guardsmen"
    x = ".meshdata.json"
    path = rf"{r}\{p}\{f}{x}"
    with open(path, "r") as handle:
        json_data = json.load(handle)
        name, meshes, bones = rebuild_from_json(json_data)

        skel_obj = create_armature(bones)
        skel_obj.name = name
        for mesh_data in meshes:
            mesh = create_mesh(mesh_data)
            mesh.parent = skel_obj  # Parent to Armature
            create_skel_groups(skel_obj.data, mesh, mesh_data)
            armature_mod = mesh.modifiers.new("Armature", "ARMATURE")  # name is 'Armature' (Default when using ui), class is 'ARMATURE'
            armature_mod.object = skel_obj
