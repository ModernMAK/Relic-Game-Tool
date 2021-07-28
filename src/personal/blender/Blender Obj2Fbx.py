# an attempt at a script to batch convert files
# It works for most files

# it crashes because some files have NAN uvs, which is a sign of a bad WHM-dump
import os
import time

import bpy

search_dir = r"D:\Dumps\DOW I\whm-model"
dump_dir = r"D:\Dumps\DOW I\fbx"

for root, _, files in os.walk(search_dir):
    for file in files:
        full_file = os.path.join(root, file)
        _, ext = os.path.splitext(file)
        ext = ext.lower()
        if ext != ".obj":
            continue

        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass

        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

        bpy.ops.import_scene.obj(filepath=full_file)


        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        bpy.ops.object.select_all(action='SELECT')

        dump_file = full_file.replace(search_dir, dump_dir, 1)
        dump_file, _ = os.path.splitext(dump_file)
        dump_file += ".fbx"

        try:
            os.makedirs(os.path.dirname(dump_file))
        except FileExistsError:
            pass

        try:
            bpy.ops.export_scene.fbx(filepath=dump_file)
        except (RuntimeError, KeyError)  as e:
            print("\t",e)
            pass
        time.sleep(0.001)