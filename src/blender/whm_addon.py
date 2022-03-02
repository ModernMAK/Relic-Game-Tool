from os.path import basename
from typing import Tuple, List

import bpy
from bpy.types import Operator, TOPBAR_MT_file_import, Object
from bpy.props import BoolProperty, StringProperty
from bpy.utils import unregister_class, register_class
from bpy_extras.io_utils import ImportHelper

import relic.chunky_formats.dow.whm as whm
from relic.chunky.serializer import read_chunky
from relic.chunky_formats.dow.whm.mesh import MslcChunk
from relic.chunky_formats.dow.whm.whm import WhmChunky, RsgmChunkV3

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

    def calculate_triangles(self, mslc:MslcChunk) -> List[Tuple[int,int,int]]:
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

    def generate_mesh(self, mslc:MslcChunk) -> Object:
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

    def import_whm(self, context, whm_chunky:WhmChunky):
        scene = context.scene
        rsgm = whm_chunky.rsgm
        if isinstance(rsgm,RsgmChunkV3):
            for mslc in rsgm.msgr.mslc:
                self.generate_mesh(mslc)

    def execute(self, context):
        try:
            with open(self.filepath,"rb") as handle:
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