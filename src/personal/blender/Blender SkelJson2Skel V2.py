# an attempt at a script to batch convert files
# It works for most files

# it crashes because some files have NAN uvs, which is a sign of a bad WHM-dump
import json
import os
import time

import bpy, bmesh
from mathutils import Quaternion, Vector, Matrix

path = r"D:\Dumps\DOW_I\full_dump\art\ebps\races\imperial_guard\troops\guardsmen_sergeant_skel_3ds.json"

arm_obj = bpy.data.objects['Armature']
# must be in edit mode to add bones
# bpy.context.scene.objects.active = arm_obj
bpy.ops.object.mode_set(mode='EDIT', toggle=False)
edit_bones = arm_obj.data.edit_bones

with open(path, "r") as handle:
    data = json.load(handle)
    bones = []
    for bone_data in data:
        bone = edit_bones.new(bone_data['name'])
        #        p_d = bone_data['pos']
        #        p = Vector(p_d['x'], p_d['y'], p_d['z'])
        #
        #        q_d = bone_data['rot']
        #        q_v = Vector(q_d['w'],q_d['x'],q_d['y'],q_d['z'])
        #        q = Quaternion(q_v)
        x, y, z = 0, 0, 0
        bone.head = x, y, z
        bone.tail = x, y + .1, z

        #        bone.use_inherit_rotation = True
        #        bone.use_inherit_scale = True
        bones.append(bone)

    for i, bone_data in enumerate(data):
        parent = bone_data['parent']
        if parent != -1:
            bones[i].parent = bones[parent]

    for i, bone_data in enumerate(data):
        p_d = bone_data['pos']
        p_t = (p_d['x'], p_d['y'], p_d['z'])
        p = Vector(p_t)

        q_d = bone_data['rot']
        q_t = (q_d['w'], q_d['x'], q_d['y'], q_d['z'])
        q_v = Vector(q_t)
        q = Quaternion(q_v)

        if bones[i].parent:
            parent_local_to_world = bones[i].parent

            local_rot = q.to_matrix()
            print(local_rot)
            local_rot.resize_4x4()
            local_pos = Matrix.Translation(p)
            local_matrix = local_pos @ local_rot

            world_matrix = parent_local_to_world @ local_matrix
            bones[i].matrix = world_matrix
        else:
            local_rot = q.to_matrix()
            print(local_rot)
            local_rot.resize_4x4()
            local_pos = Matrix.Translation(p)
            local_matrix = local_pos @ local_rot

            bones[i].matrix = local_matrix
