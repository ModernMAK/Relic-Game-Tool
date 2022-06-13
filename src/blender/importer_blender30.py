from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TextIO, Any
import json
import math
import os
# BLENDER ONLY
import bpy
import mathutils

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

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
        quat = mathutils.Quaternion([w, x, y, z])
        mat = mathutils.Matrix.LocRotScale(pos, quat, None)
        return mat


# IGNORES SCALE
def rotate_matrix_rotaiton(m, q):
    m_t = m.to_translation()
    m_q = m.to_quaternion()
    temp_m = m_q.to_matrix() @ q.to_matrix()
    temp_q = temp_m.to_quaternion()
    return mathutils.Matrix.LocRotScale(m_t, temp_q, None)


def scale_vector(v, s):
    return (v[_] * s[_] for _ in range(len(v)))


# IGNORES SCALE
def scale_matrix_translation(m, s):
    t = m.to_translation()
    q = m.to_quaternion()
    t = scale_vector(t, s)
    return mathutils.Matrix.LocRotScale(t, q, None)


def rotate_quaternion(r, q):
    m = r.to_matrix() @ q.to_matrix()
    return m.to_quaternion()


def rotate_quaternion_axis(r, q):
    axis, angle = q.to_axis_angle()
    axis = rotate_vector(axis, r)
    return mathutils.Quaternion(axis, angle)


def rotate_vector(p: Float3, q):
    v = mathutils.Vector(p)
    v.rotate(q)
    return v


def rotate_vector_list(p: List, q):
    v = [mathutils.Vector(_) for _ in p]
    for _ in v:
        _.rotate(q)
    return v


@dataclass
class RawMesh:
    name: str
    positions: List[Float3]
    normals: List[Float3]
    bones: Dict[int, str]
    bone_weights: Optional[List[List[float, Byte]]]
    uvs: List[Float2]
    sub_meshes: Dict[str, List[Short3]]

    @classmethod
    def rebuild(cls, d: Optional[Dict]) -> Optional[RawMesh]:
        if not d:
            return None
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


@dataclass
class RawAnimBone:
    name: str
    pos: Dict[int, Float3]
    rot: Dict[int, Float4]
    stale: bool

    @classmethod
    def rebuild(cls, d: Dict) -> RawAnimBone:
        name = d['name']
        pos = {int(k): [float(v[_]) for _ in range(3)] for k, v in d['pos'].items()}
        rot = {int(k): [float(v[_]) for _ in range(4)] for k, v in d['rot'].items()}
        stale = d['stale']
        return cls(name, pos, rot, stale)


@dataclass
class RawAnimMesh:
    name: str
    mode: int
    visibility: Dict[int, float]
    unks: Tuple

    @classmethod
    def rebuild(cls, d: Dict) -> RawAnimMesh:
        return cls(**d)


@dataclass
class RawAnim:
    name: str
    key_frames: int  # used to init animaition
    bones: List[RawAnimBone]
    meshes: List[RawAnimMesh]

    # Since IDK what unks animates, I've ignored it

    @classmethod
    def rebuild(cls, d: Dict) -> RawAnim:
        name = d['name']
        key_frames = d['key_frames']
        bones = [RawAnimBone.rebuild(_) for _ in d['bones']]
        meshes = [RawAnimMesh.rebuild(_) for _ in d['meshes']]
        return cls(name, key_frames, bones, meshes)


def create_vert2loops(mesh):
    vert2loops = {}
    for poly in mesh.polygons:
        for v_ix, l_ix in zip(poly.vertices, poly.loop_indices):
            if v_ix in vert2loops:
                vert2loops[v_ix].append(l_ix)
            else:
                vert2loops[v_ix] = [l_ix]
    return vert2loops


def get_material(name: str):
    name = os.path.basename(name)
    if name in bpy.data_chunks.materials:
        mat = bpy.data_chunks.materials[name]
    else:
        mat = bpy.data_chunks.materials.new(name=name)
    return mat


def get_animation(name: str):
    if name in bpy.data_chunks.actions:
        animation = bpy.data_chunks.actions[name]
    else:
        animation = bpy.data_chunks.actions.new(name=name)
    return animation


def create_animation(armature, animation: RawAnim, rotation=None, root_scale: Float3 = None):
    if len(animation.bones) == 0:
        return  # Ignore, we don't support mesh vis currently
    # rotation_dir_fix = mathutils.Quaternion([0, 1, 0], math.radians(90.0))  # Orient bones outward in direction of
    rotate_90y = mathutils.Quaternion([0, 1, 0], math.radians(-90.0))
    armature.animation_data.action = get_animation(animation.name)
    print(armature.animation_data.action)
    for b in animation.bones:
        arm_b = armature.pose.bones[b.name]
        if len(b.pos) > 0:
            for f, v in b.pos.items():
                if rotation:
                    v = rotate_vector(v, rotation)
                # reset_pos = arm_b.location
                arm_b.location = v
                armature.keyframe_insert(data_path=f'pose.bones["{b.name}"].location', frame=f)
                # arm_b.location = reset_pos
        if len(b.rot) > 0:
            for f, v in b.rot.items():
                x, y, z, w = v
                #                x, y, z = z, x ,y # We have swapped
                v = mathutils.Quaternion([w, x, y, z])
                #                rot_90y =
                # if rotation:
                v = rotate_quaternion(v, rotate_90y)
                # v = rotate_quaternion_axis(v, rotation_dir_fix)
                # reset_rot = arm_b.rotation_quaternion
                arm_b.rotation_quaternion = v
                armature.keyframe_insert(data_path=f'pose.bones["{b.name}"].rotation_quaternion', frame=f)
                # arm_b.rotation_quaternion = reset_rot
    for arm_b in armature.pose.bones:
        arm_b.matrix_basis = mathutils.Matrix()


def create_mesh(data: RawMesh, root_rotation=None, root_scale=None, flip_winding: bool = False):
    triangles = []
    for tri_buffers in data.sub_meshes.values():
        if flip_winding:
            for t in tri_buffers:
                triangles.append([t[2], t[1], t[0]])
        else:
            triangles.extend(tri_buffers)

    positions = data.positions
    normals = data.normals

    if root_rotation:
        positions = rotate_vector_list(positions, root_rotation)
        normals = rotate_vector_list(normals, root_rotation)

    def apply_scale(values: List):
        s = root_scale
        return [(v[0] * s[0], v[1] * s[1], v[2] * s[2]) for v in values]

    if root_scale:
        positions = apply_scale(positions)
        normals = apply_scale(normals)

    mesh = bpy.data_chunks.meshes.new(data.name)
    mesh.from_pydata(positions, [], triangles)
    mesh.update()
    for i, v in enumerate(mesh.vertices):
        v.normal = normals[i]

    vert2loops = create_vert2loops(mesh)
    uvs = data.uvs
    uv_layer = mesh.uv_layers.new()
    for i in range(len(positions)):
        if i in vert2loops:  # THIS COULD BE A BUG! OR STRAY VERTEX?!
            for loop in vert2loops[i]:
                uv_layer.data_chunks[loop].uv = uvs[i]

    face_lookup = {}
    for mat_name, tris in data.sub_meshes.items():
        mat = get_material(mat_name)
        mesh.materials.append(mat)
        for tri in tris:
            t_key = frozenset(tri)
            face_lookup[t_key] = len(mesh.materials) - 1
    for face in mesh.polygons:
        f_key = frozenset(face.vertices)
        face.material_index = face_lookup[f_key]
    obj = bpy.data_chunks.objects.new(data.name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def create_bone(armature, data: RawBone, parent_mat=None, final_scale=None, parent_small: bool = False):
    bone = armature.edit_bones.new(data.name)

    is_small = "bip" in bone.name
    BIG_SIZE = 1
    SMALL_SIZE = 0.25
    MID_SIZE = .375
    bone_size = SMALL_SIZE if is_small else (MID_SIZE if parent_small else BIG_SIZE)
    parent_small |= is_small

    bone.tail = mathutils.Vector([0, 0, bone_size])

    transform = data.transform
    mat = transform.to_matrix()

    bone_mat = mat
    if parent_mat:
        bone_mat = parent_mat @ mat
    final_mat = bone_mat
    #    const_rotation = mathutils.Quaternion([1, 0, 0], math.radians(90.0))  # Orient bones outward in direction of

    #    const_rotation_a = mathutils.Quaternion([0, 1, 0], math.radians(90.0))  # Orient bones outward in direction of
    #    const_rotation_b = mathutils.Quaternion([1, 0, 0], math.radians(-90.0))  # Orient bones outward in direction of
    #    const_rotation = rotate_quaternion(const_rotation_a,const_rotation_b)
    #    final_mat = rotate_matrix_rotaiton(final_mat, const_rotation)
    if final_scale:
        final_mat = scale_matrix_translation(final_mat, final_scale)
    bone.matrix = final_mat

    for c in data.children:
        child_bone = create_bone(armature, c, parent_mat=bone_mat, parent_small=parent_small, final_scale=final_scale)
        # HACK TO PRETIFY BONES
        if "bip" in bone.name and "bip" in child_bone.name:
            if len(data.children) == 1 or ("pelvis" in bone.name and "spine" in child_bone.name):
                bone.tail = child_bone.head
                child_bone.use_connect = True
        child_bone.parent = bone

    return bone


def create_armature(data: RawBone, rotation=None, root_scale: Float3 = None):
    if not data:
        return None
    # Preserve state after runnign script
    old_mode, old_obj = None, None
    try:
        root = bpy.data_chunks.armatures.new("Armature")
        root_obj = bpy.data_chunks.objects.new("Armature", root)
        bpy.context.collection.objects.link(root_obj)

        old_obj = bpy.context.active_object
        bpy.context.view_layer.objects.active = root_obj

        old_mode = bpy.context.mode
        bpy.ops.object.mode_set(mode='EDIT')

        root_m = mathutils.Matrix.LocRotScale(None, rotation, None) if rotation else None
        for child in data.children:
            create_bone(root, child, root_m, final_scale=root_scale)
    finally:
        if old_obj:
            bpy.context.view_layer.objects.active = old_obj
        if old_mode:
            bpy.ops.object.mode_set(mode=old_mode)
    return root_obj


def create_skel_groups(skel, mesh, data: RawMesh):
    if len(skel.bones) == 0:
        return

    name2index = {}
    for i, b in enumerate(skel.bones):
        _ = mesh.vertex_groups.new(name=b.name)  # Ensure all bones exist
        name2index[b.name] = i

    if data.bone_weights:
        for vi, bw_data in enumerate(data.bone_weights):
            for bi, bw in bw_data:
                mesh.vertex_groups[bi].add([vi], bw, 'REPLACE')
    elif data.has_implied_bone:
        name = data.name
        alt_name = None
        if "_obj_" in name:  # IG Marauder has this and no bone weights
            name = name.replace("_obj_", "_")
        # HACK for tanks
        if "tread_l" in name:
            alt_name = "left_tread"
        elif "tread_r" in name:
            alt_name = "right_tread"

        bwi = None
        if name in name2index:
            bwi = name2index[name]
        elif alt_name and alt_name in name2index:
            bwi = name2index[alt_name]
        if bwi:
            vgroup = mesh.vertex_groups[bwi]
            for i in range(len(data.positions)):
                vgroup.add([i], 1.0, 'REPLACE')


def rebuild_from_json(data: Dict) -> tuple[Any, list[RawMesh | None], RawBone, list[RawAnim]]:
    name = data['name']
    meshes = data['meshes']
    meshes = [RawMesh.rebuild(m) for m in meshes]
    skel = data['skel']
    skel = RawBone.rebuild(skel)
    anims = data['animations']
    anims = [RawAnim.rebuild(a) for a in anims]
    return name, meshes, skel, anims


def build_from_stream(stream: TextIO):
    json_data = json.load(stream)
    name, meshes, bones, anims = rebuild_from_json(json_data)
    root_rot = mathutils.Quaternion([1, 0, 0], math.radians(90.0))
    root_scale: Float3 = (-1.0, 1.0, 1.0)

    skel_obj = create_armature(bones, root_rot, root_scale)

    for mesh_data in meshes:
        mesh = create_mesh(mesh_data, root_rotation=root_rot, root_scale=root_scale, flip_winding=True)
        mesh.parent = skel_obj  # Parent to skel
        create_skel_groups(skel_obj.data, mesh, mesh_data)
        armature_mod = mesh.modifiers.new("Armature", "ARMATURE")  # name is 'Armature' (Default when using ui), class is 'ARMATURE'
        armature_mod.object = skel_obj

    # Ensure anim_data
    if not skel_obj.animation_data:
        skel_obj.animation_data_create()
        # skel_obj.keyframe_insert("location")  #
        # skel_obj.animation_data.action.name = "DELETE ME"

    for anim_data in anims:
        create_animation(skel_obj, anim_data, root_scale=root_scale)

    skel_obj.show_in_front = True
    return skel_obj


def spiral():
    # Stolen for time
    # https://stackoverflow.com/questions/398299/looping-in-a-spiral
    x = y = 0
    dx = 0
    dy = -1
    while True:
        yield x, y
        if x == y or (x < 0 and x == -y) or (x > 0 and x == 1 - y):
            dx, dy = -dy, dx
        x, y = x + dx, y + dy


def build(context, filepath):
    if os.path.isfile(filepath):
        print("Reading WHM Dumped JSON")
        with open(filepath, 'r') as handle:
            build_from_stream(handle)
        return {'FINISHED'}
    else:
        print("Reading WHM Dumped JSONs")
        s = spiral()
        for root, _, files in os.walk(filepath):
            _[:] = []
            for file in files:
                a, x = os.path.splitext(file)
                if x != ".json":
                    continue
                b, x = os.path.splitext(a)
                if x != ".meshdata":
                    continue
                #                if "aa_" in file:
                #                    continue
                subfilepath = os.path.join(root, file)
                print(f"\t{subfilepath}")
                with open(subfilepath, 'r') as handle:
                    OFFSET = 10.0
                    x, y = next(s)
                    r = build_from_stream(handle)

                    l = r.location
                    l[0] += x * OFFSET
                    l[1] += y * OFFSET
                    r.location = l
        return {'FINISHED'}


class ImportWHM(Operator, ImportHelper):
    """Convert WHM data to mesh"""
    bl_idname = "importer.whm"  # important since It's how bpy.ops.import_test.some_data is constructed
    bl_label = "open"

    # ImportHelper mixin class uses this
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.meshdata.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return build(context, self.filepath)  # , self.use_setting)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportWHM.bl_idname, text="Import WHM")


# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access)
def register():
    bpy.utils.register_class(ImportWHM)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unreister_class(ImportWHM)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # Was tired of using the dialouge to test
    quick_test = r"D:\Relic-SGA\DOW_I\WHM_DUMP\DXP2Data-Whm-High\data\art\ebps\races\imperial_guard\troops\baneblade.meshdata.json"
    build(None, quick_test)
    # test call
#    bpy.ops.importer.whm('INVOKE_DEFAULT')
