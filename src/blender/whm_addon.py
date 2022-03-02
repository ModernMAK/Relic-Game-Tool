from os.path import basename
from typing import Tuple, List, Optional

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator, TOPBAR_MT_file_import, Object, Armature, Action, PoseBone
from bpy.utils import unregister_class, register_class
from bpy_extras.io_utils import ImportHelper
from mathutils import Matrix, Vector, Quaternion

from relic.chunky.serializer import read_chunky
from relic.chunky_formats.dow.whm.animation import AnimChunk
from relic.chunky_formats.dow.whm.mesh import MslcChunk
from relic.chunky_formats.dow.whm.whm import WhmChunky, RsgmChunkV3, SkelChunk

bl_info = {
    "name": "Relic WHM Importer",
    "blender": (3, 0, 1),
    "category": "Object",
}


class ImportRelicWHM(Operator, ImportHelper):
    """Imports a Relic WHM file"""  # Use this as a tooltip for menu items and buttons.
    bl_idname = "importer.relic_whm"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Relic WHM (.whm)"  # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    import_skeleton: BoolProperty(name="Include Armature", default=True)
    import_animation: BoolProperty(name="Include Animations", default=True)
    import_embedded_textures: BoolProperty(name="Include Embedded Textures", default=True)
    flip_triangle_winding: BoolProperty(name="Flip Triangle Winding", default=True)

    filter_glob: StringProperty(default='*.whm', options={'HIDDEN'})

    def calculate_triangles(self, mslc: MslcChunk) -> List[Tuple[int, int, int]]:
        triangles = []
        for sub_mesh in mslc.data.sub_meshes:
            if self.flip_triangle_winding:
                for t in sub_mesh.triangles:
                    triangles.append([t[2], t[1], t[0]])
            else:
                triangles.extend(sub_mesh.triangles)
        return triangles

    @staticmethod
    def get_material(name: str):
        name = basename(name)
        if name in bpy.data.materials:
            mat = bpy.data.materials[name]
        else:
            mat = bpy.data.materials.new(name=name)
        return mat

    def generate_mesh(self, mslc: MslcChunk) -> Object:
        mesh_data = mslc.data

        # Gather data
        positions = mesh_data.vertex_data.positions
        normals = mesh_data.vertex_data.normals
        uvs = mesh_data.vertex_data.uvs
        triangles = self.calculate_triangles(mslc)

        # Make Mesh
        mesh = bpy.data.meshes.new(mslc.header.name)
        mesh.from_pydata(positions, [], triangles)
        mesh.update()
        # Normals
        for i, v in enumerate(mesh.vertices):
            v.normal = normals[i]
        # Uvs
        uv_layer = mesh.uv_layers.new()
        for poly in mesh.polygons:
            for v_ix, l_ix in zip(poly.vertices, poly.loop_indices):
                uv_layer.data[l_ix].uv = uvs[v_ix]
        # Sub-Meshes
        # First map face => material
        face_lookup = {}
        for sub_mesh in mesh_data.sub_meshes:
            mat = self.get_material(sub_mesh.texture_path)
            mesh.materials.append(mat)
            for tri in sub_mesh.triangles:
                t_key = frozenset(tri)
                face_lookup[t_key] = len(mesh.materials) - 1
        # Then walk faces and assign materials
        for face in mesh.polygons:
            f_key = frozenset(face.vertices)
            face.material_index = face_lookup[f_key]
        obj = bpy.data.objects.new(mslc.header.name, mesh)
        bpy.context.collection.objects.link(obj)
        return obj

    @staticmethod
    def generate_armature(skel: SkelChunk) -> Object:
        BIP_BONE_SIZE = 0.25
        DEF_BONE_SIZE = 1.0
        # Preserve state after running script
        old_mode, old_obj = None, None
        try:
            armature = bpy.data.armatures.new("Armature")
            armature_obj = bpy.data.objects.new("Armature", armature)
            armature_obj.show_in_front = True
            bpy.context.collection.objects.link(armature_obj)

            old_obj = bpy.context.active_object
            bpy.context.view_layer.objects.active = armature_obj

            old_mode = bpy.context.mode
            bpy.ops.object.mode_set(mode='EDIT')

            # 3 passes, Gen Bones, Assemble Hierarchy, Apply Transforms
            bones = []
            local_matrix = []
            world_matrix: List[Matrix] = [None] * len(skel.bones)
            # Gen Bones
            for transform in skel.bones:
                bone = armature.edit_bones.new(transform.name)
                bone_size = BIP_BONE_SIZE if "bip" in transform.name else DEF_BONE_SIZE
                bone.tail = Vector([-bone_size, 0, 0])
                bones.append(bone)

                pos = Vector(transform.pos)
                qx, qy, qz, qw = transform.quaternion
                rot = Quaternion([qw, qx, qy, qz])  # Blender wants w first
                matrix = Matrix.LocRotScale(pos, rot, Vector([1, 1, 1]))
                local_matrix.append(matrix)
            # Assemble Hierarchy
            for i, transform in enumerate(skel.bones):
                if transform.parent_index == -1:  # ROOT
                    world_matrix[i] = local_matrix[i]
                    continue
                parent_bone = bones[transform.parent_index]
                child_bone = bones[i]
                child_bone.parent = parent_bone

            unapplied = list(i for i, _ in enumerate(world_matrix) if _ is None)
            while len(unapplied) > 0:
                i = unapplied.pop(0)
                transform = skel.bones[i]
                parent_i = transform.parent_index
                if world_matrix[parent_i]:
                    world_matrix[i] = world_matrix[parent_i] @ local_matrix[i]
                else:
                    unapplied.append(i)

            # Apply Transforms (Could be merged but assemble is ugly enough as-is)
            for i in range(len(skel.bones)):
                bone = bones[i]
                bone.matrix = world_matrix[i]

        finally:
            if old_obj:
                bpy.context.view_layer.objects.active = old_obj
            if old_mode:
                bpy.ops.object.mode_set(mode=old_mode)
        return armature_obj

    @staticmethod
    def apply_bone_weights(skel: SkelChunk, mslc: MslcChunk, armature_obj: Object, mesh_obj: Object):
        name2index = {}
        for i, b in enumerate(skel.bones):
            _ = mesh_obj.vertex_groups.new(name=b.name)  # Ensure all bones exist
            name2index[b.name] = i

        bone_weights = mslc.data.vertex_data.bone_weights
        if bone_weights is not None:
            for vi, bw_data in enumerate(bone_weights):
                (w1, w2, w3), (i1, i2, i3, i4) = bw_data
                w4 = 1 - (w1 + w2 + w3)
                w = [w1, w2, w3, w4]
                i = [i1, i2, i3, i4]
                for bi, bw in zip(i, w):
                    if bi not in [-1, 255]:  # Only one should be right, but the other should never occur, not defensive programming, but idc enough right now
                        mesh_obj.vertex_groups[bi].add([vi], bw, 'REPLACE')
        elif len(skel.bones) > 0:
            bwi = None
            if mslc.header.name in name2index:
                bwi = name2index[mslc.header.name]
            # elif alt_name and alt_name in name2index:
            #     bwi = name2index[alt_name]
            if bwi:
                vgroup = mesh_obj.vertex_groups[bwi]
                for i in range(len(mslc.data.vertex_data.positions)):
                    vgroup.add([i], 1.0, 'REPLACE')
            
        for group in mesh_obj.vertex_groups:
            group.lock_weight = True

        armature_mod = mesh_obj.modifiers.new("Armature", "ARMATURE")  # name is 'Armature' (Default when using ui), class is 'ARMATURE'
        armature_mod.object = armature_obj
        mesh_obj.parent = armature_obj

    def get_animation(self, name: str):
        if name in bpy.data.actions:
            animation = bpy.data.actions[name]
        else:
            animation = bpy.data.actions.new(name=name)
        return animation

    def generate_animation(self, armature_obj: Object, anim: AnimChunk) -> Optional[Action]:
        if len(anim.data.bones) == 0:
            return None  # Ignore, we don't support mesh vis currently
        if not any(len(b.positions) > 0 or len(b.rotations) > 0 for b in anim.data.bones):
            return None  # Ignore, we don't support mesh vis currently
        armature_obj.animation_data.action = self.get_animation(anim.header.name)
        for anim_bone in anim.data.bones:
            bone = armature_obj.pose.bones[anim_bone.name]
            if len(anim_bone.positions) > 0:
                for _, v in anim_bone.positions.items():
                    # TODO, currently anim includes frame in v and doesn't convert to a frame number
                    f = round(v[0] * (anim.data.key_frames - 1))
                    v = v[1:]

                    bone.location = v
                    armature_obj.keyframe_insert(data_path=f'pose.bones["{anim_bone.name}"].location', frame=f)
            if len(anim_bone.rotations) > 0:
                for f, v in anim_bone.rotations.items():
                    # TODO, currently anim includes frame in v and doesn't convert to a frame number
                    f = round(v[0] * (anim.data.key_frames - 1))
                    v = v[1:]
                    x, y, z, w = v
                    v = Quaternion([w, x, y, z])
                    bone.rotation_quaternion = v
                    armature_obj.keyframe_insert(data_path=f'pose.bones["{anim_bone.name}"].rotation_quaternion', frame=f)
        for bone in armature_obj.pose.bones:
            bone.matrix_basis = Matrix()

    def import_whm(self, context, whm_chunky: WhmChunky):
        scene = context.scene
        rsgm = whm_chunky.rsgm
        armature_obj = None
        mesh_objs = []
        if isinstance(rsgm, RsgmChunkV3):
            skel = rsgm.skel
            for mslc in rsgm.msgr.mslc:
                mesh_obj = self.generate_mesh(mslc)
                mesh_objs.append(mesh_obj)

            if self.import_skeleton and skel:
                armature_obj = self.generate_armature(skel)
                for i, mslc in enumerate(rsgm.msgr.mslc):
                    self.apply_bone_weights(skel, mslc, armature_obj, mesh_objs[i])
                if self.import_animation:
                    if not armature_obj.animation_data:
                        armature_obj.animation_data_create()
                    for anim in rsgm.anim:
                        self.generate_animation(armature_obj, anim)
        else:
            raise TypeError(rsgm.header)

    def execute(self, context):
        try:
            with open(self.filepath, "rb") as handle:
                chunky = read_chunky(handle)
                whm_chunky = WhmChunky.convert(chunky)
                self.import_whm(context, whm_chunky)
        except:
            print("A fatal error has occurred!")
            raise
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(ImportRelicWHM.bl_idname)


def register():
    register_class(ImportRelicWHM)
    TOPBAR_MT_file_import.append(menu_func)


def unregister():
    unregister_class(ImportRelicWHM)
    TOPBAR_MT_file_import.remove(menu_func)


if __name__ == "__main__":
    #    unregister()
    register()
