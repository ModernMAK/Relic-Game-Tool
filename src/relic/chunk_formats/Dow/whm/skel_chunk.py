import math
import struct
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, List, Dict, Any

from relic.chunk_formats.Dow.whm.shared import num_layout
from relic.chunky import DataChunk
from relic.file_formats.matrix_math import Quaternion, Vector3, Matrix, Transform
from relic.file_formats.mesh_io import Float3, Float4
# STOLEN FROM 'https://automaticaddison.com/how-to-convert-a-quaternion-into-euler-angles-in-python/'
from relic.shared import unpack_from_stream


def euler_from_quaternion(x, y, z, w):
    """
    Convert a quaternion into euler angles (roll, pitch, yaw)
    roll is rotation around x in radians (counterclockwise)
    pitch is rotation around y in radians (counterclockwise)
    yaw is rotation around z in radians (counterclockwise)
    """
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y * y)
    roll_x = math.atan2(t0, t1)

    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    pitch_y = math.asin(t2)

    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    yaw_z = math.atan2(t3, t4)

    return roll_x, pitch_y, yaw_z  # in radians


def quaternion_multiply(Q0, Q1):
    """
    Multiplies two quaternions.

    Input
    :param Q0: A 4 element array containing the first quaternion (q01,q11,q21,q31)
    :param Q1: A 4 element array containing the second quaternion (q02,q12,q22,q32)

    Output
    :return: A 4 element array containing the final quaternion (q03,q13,q23,q33)

    """
    # Extract the values from Q0
    w0 = Q0[0]
    x0 = Q0[1]
    y0 = Q0[2]
    z0 = Q0[3]

    # Extract the values from Q1
    w1 = Q1[0]
    x1 = Q1[1]
    y1 = Q1[2]
    z1 = Q1[3]

    # Computer the product of the two quaternions, term by term
    Q0Q1_w = w0 * w1 - x0 * x1 - y0 * y1 - z0 * z1
    Q0Q1_x = w0 * x1 + x0 * w1 + y0 * z1 - z0 * y1
    Q0Q1_y = w0 * y1 - x0 * z1 + y0 * w1 + z0 * x1
    Q0Q1_z = w0 * z1 + x0 * y1 - y0 * x1 + z0 * w1

    # Create a 4 element array containing the final quaternion
    final_quaternion = [Q0Q1_w, Q0Q1_x, Q0Q1_y, Q0Q1_z]

    # Return a 4 element array containing the final quaternion (q02,q12,q22,q32)
    return final_quaternion


@dataclass
class SkelBone:
    name: str
    parent_index: int

    # Original coordinate system
    pos: Float3
    quaternion: Float4

    _LAYOUT = struct.Struct("< l 3f 4f")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'SkelBone':
        buffer = stream.read(num_layout.size)
        name_size = num_layout.convert(buffer)[0]
        name = stream.read(name_size).decode("ascii")
        parent, px, py, pz, rx, ry, rz, rw = unpack_from_stream(cls._LAYOUT, stream)
        p = (px, py, pz)
        q = (rx, ry, rz, rw)

        return SkelBone(name, parent, p, q)


@dataclass
class SkelChunk:
    # This chunk is super easy
    bones: List[SkelBone]

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'SkelChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(num_layout.size)
            bone_size = num_layout.convert(buffer)[0]
            bones = [SkelBone.unpack(stream) for _ in range(bone_size)]
            return SkelChunk(bones)


_Euler90_0_0 = Quaternion(0.7071068, 0, 0, 0.7071068)
@dataclass
class Skeleton:
    name: str
    transform: Transform
    parent_index:int
    @classmethod
    def create(cls, chunk: SkelChunk) -> List['Skeleton']:

        temp = [Skeleton(bone.name, Transform(Quaternion(*bone.quaternion), Vector3(*bone.pos)), bone.parent_index) for bone in
                chunk.bones]
        for i, skel in enumerate(temp):
            bone = chunk.bones[i]
            # x, y, z = skel.transform.translation.xyz
            if bone.parent_index != -1:
                skel.transform.parent = temp[bone.parent_index].transform
                # skel.transform.translation = Vector3(-x, z, y) # Magically preserves handedness
                # skel.transform.rotation = skel.transform.rotation.Swap(AxisOrder.XZY)
                # rotation_matrix = skel.transform.rotation.Swap(AxisOrder.ZXY).as_matrix()
                # rotation_matrix._array[1][0] *= -1
                # rotation_matrix._array[2][0] *= -1
                # rotation_matrix._array[0][1] *= -1
                # rotation_matrix._array[0][2] *= -1
                # skel.transform.rotation = Quaternion.from_matrix(rotation_matrix)

            # else:
            #     pass
            # skel.transform.translation
            skel.transform.rotation = skel.transform.rotation.normalized()#.Swap(AxisOrder.XZY).normalized()
            # skel.transform.translation = Vector3(-x, z, y)  # Magically preserves handedness

            # r = skel.transform.rotation
            # r = r.Invert(x).Swap(AxisOrder.XZY)
            # skel.transform.rotation = r

        # for bone in temp:
        #     # Convert Axis
        #     pos = bone.local_position.xyz
        #     pos = -pos[0], pos[1], pos[2]
        #     bone.local_position = Vector3(*pos)
        #     # Convert Quaternion
        #     q = bone.local_rotation
        #     q = q.Invert(x=True)  # , w=True)
        #     bone.local_rotation = q
        #
        # for t in temp:
        #     t._children = []
        #
        # for i, bone in enumerate(chunk.bones):
        #     if bone.parent_index != -1:
        #         temp[i]._parent = temp[bone.parent_index]
        #         temp[bone.parent_index]._children.append(temp[i])
        #     temp[i].cache()

        # for bone in temp:
        #     # Convert Axis
        #     pos = bone.world_position.xyz
        #     pos = -pos[0], pos[1], pos[2]
        #     bone._world_position = Vector3(*pos)
        #     # Convert Quaternion
        #     q = bone.world_rotation
        #     q = q.Invert(x=True)#, w=True)
        #     # q = q.Swap(AxisOrder.XZY)
        #     bone._world_rotation = q

        return temp


def parse_bone_data(bone_data: List[SkelBone]) -> List[Dict[str, Any]]:
    bones: List = []
    for data in bone_data:
        if data.parent_index == -1:
            q = Quaternion.XYZW(*data.quaternion)
            # WTF is this ?
            # Inverse matrix, multiply by arbitrary and the inverse (while I know order matters, should that still result in the original?)
            #   THEN invert that matrix (to original) and get the quaternion?
            # Im pretty sure this can be simplified to
            #   world_rotation = q.as_matrix()
            rotation_matrix = q.as_matrix().inversed()
            world_matrix = Matrix([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
            matrix = world_matrix @ rotation_matrix @ world_matrix.inverse()
            world_rotation = Quaternion.from_matrix(matrix).inversed()

            # Rotate by euler 90, 0, 0
            x, y, z = data.pos
            world_position = Vector3(-x, -z, y)
            t = (world_rotation, world_position, True, data.parent_index, data.name)
            bones.append(t)
        else:
            rotation_matrix = Quaternion.XYZW(*data.quaternion).as_matrix()
            rotation_matrix._array[1][0] *= -1
            rotation_matrix._array[2][0] *= -1
            rotation_matrix._array[0][1] *= -1
            rotation_matrix._array[0][2] *= -1
            local_rotation = Quaternion.from_matrix(rotation_matrix)
            x, y, z = data.pos
            local_position = Vector3(-x, y, z)
            t = (local_rotation, local_position, False, data.parent_index, data.name)
            bones.append(t)

    # frontier = Queue()
    # for i in range(len(bones)):
    #     frontier.put(i)
    # while not frontier.empty():
    #     i = frontier.get()
    #     rot, pos, world_space, parent_index, name = bones[i]
    #     # If in world space or no parent; nothing to do
    #     if world_space or parent_index == -1:
    #         continue
    #     # IF parent not in world space, add this to the frontier so that next time it's hopefully completed
    #     p_rot, p_pos, p_world_space, _, _ = bones[parent_index]
    #     if not p_world_space:
    #         frontier.put(i)
    #         continue
    #
    #     world_rot = p_rot * rot
    #     world_pos = p_pos + world_rot.as_matrix().multiply_matrix(pos.as_matrix()).to_vector()
    #
    #     bones[i] = world_rot, world_pos, True, parent_index, name
    #     continue

    return [{'pos': pos, "rot": rot, "parent": parent, "name": name} for rot, pos, _, parent, name in bones]

    # (
    #     rotmat = (quat bone_array[i].rot_x bone_array[i].rot_y bone_array[i].rot_z bone_array[i].rot_w) as matrix3
    # rotmat = inverse rotmat
    # mat = matrix3[1, 0, 0][0, 0, 1][0, -1, 0][0, 0, 0]
    # newmat = mat * rotmat * (inverse mat)
    # newmat = newmat as quat
    # new_bone.rotation = (inverse newmat)
    # rot = eulerangles 90 0 0
    # in coordsys local rotate new_bone rot         - - Set Bone Rotation
    # new_bone.pos = (point3 - bone_array[i].pos_x - bone_array[i].pos_z bone_array[i].pos_y) - - Set
    # Bone
    # Position
    # )
    # else -- Child
    # Bones - Parent
    # Coordinates
    # (
    #     newmat = (matrix3[0, 0, 0][0, 0, 0][0, 0, 0][0, 0, 0]) - - Create
    # Zero
    # Matrix
    #
    # bonequat = (quat
    #             bone_array[i].rot_x bone_array[i].rot_y bone_array[i].rot_z bone_array[i].rot_w) as matrix3 - - Turn
    # Quat
    # Into
    # Matrix
    # newmat.row1 = (point3 bonequat[1][1] -bonequat[2][1] -bonequat[3][1]) - - Set
    # 1
    # st
    # Row
    # newmat.row2 = (point3 - bonequat[1][2] bonequat[2][2] bonequat[3][2]) - - Set
    # 2
    # nd
    # Row
    # newmat.row3 = (point3 - bonequat[1][3] bonequat[2][3] bonequat[3][3]) - - Set
    # 3
    # rd
    # Row
    # newmat.row4 = (point3 bone_array[i].pos_x bone_array[i].pos_y bone_array[i].pos_z) - - Set
    # 4
    # th
    # Row
    #
    # newrot = newmat as quat - - Get
    # Rotation
    # Part
    # From
    # Matrix
    # newrot.w *= -1 - - Negate
    # Rotation
    # W
    #
    # newpos = newmat.translationpart - - Get
    # Translation
    # Part
    # From
    # Matrix
    # newpos.x *= -1 - - Negate
    # Position
    # X
    #
    # in coordsys
    # parent
    # new_bone.rotation = newrot - - Set
    # Child
    # Bone
    # Rotation
    # in coordsys
    # parent
    # new_bone.pos = newpos - - Set
    # Child
    # Bone
    # Position
    # )
    # )
