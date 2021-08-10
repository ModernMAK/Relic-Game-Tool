# an attempt at a script to batch convert files
# It works for most files

# it crashes because some files have NAN uvs, which is a sign of a bad WHM-dump
import json
import os
import time

import bpy, bmesh

root = r"D:\Dumps\DOW_I\full_dump"
fold = r"art\ebps\races\imperial_guard\troops"
file = r"guardsmen_sergeant_skel.json"
path = os.path.join(root,fold,file)
arm_obj = bpy.data.objects['Armature']
# must be in edit mode to add bones
#bpy.context.scene.objects.active = arm_obj
bpy.ops.object.mode_set(mode='EDIT', toggle=False)
edit_bones = arm_obj.data.edit_bones

with open(path, "r") as handle:
    data = json.load(handle)
    bones = []
    for bone_data in data:
        bone = edit_bones.new(bone_data['name'])
        x, y, z = bone_data['pos']
        bone.head = x, y, z
        bone.tail = x, y, z + .1
        bone.use_connect = True
        bones.append(bone)
    for i, bone_data in enumerate(data):
        parent = bone_data['parent_index']
        if parent != -1:
            bones[i].parent = bones[parent]
