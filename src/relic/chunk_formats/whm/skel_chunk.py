import math
import struct
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, List, Optional, Tuple

import numpy as np

from relic.chunk_formats.whm.shared import num_layout
from relic.chunky import DataChunk
from relic.file_formats.matrix_math import Quaternion, Vector3
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
    # This chunk is also super easy
    name: str
    parent_index: int
    pos: Float3
    quaternion: Float4

    _LAYOUT = struct.Struct("< l 3f 4f")

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'SkelBone':
        buffer = stream.read(num_layout.size)
        name_size = num_layout.unpack(buffer)[0]
        name = stream.read(name_size).decode("ascii")
        parent, px, py, pz, rx, ry, rz, rw = unpack_from_stream(cls._LAYOUT, stream)

        return SkelBone(name, parent, (px, py, pz), (rx, ry, rz, rw))


@dataclass
class SkelChunk:
    # This chunk is super easy
    bones: List[SkelBone]

    @classmethod
    def convert(cls, chunk: DataChunk) -> 'SkelChunk':
        with BytesIO(chunk.data) as stream:
            buffer = stream.read(num_layout.size)
            bone_size = num_layout.unpack(buffer)[0]
            bones = [SkelBone.unpack(stream) for _ in range(bone_size)]
            return SkelChunk(bones)


@dataclass
class Skeleton:
    name: str
    local_position: Vector3
    local_rotation: Quaternion
    _parent_index:int = None

    _parent: Optional['Skeleton'] = None
    _children: List['Skeleton'] = None

    _world_position: Vector3 = None
    _world_rotation: Quaternion = None


    @property
    def world_position(self) -> Vector3:
        return self._world_position or self._calc_world_position()

    @property
    def world_rotation(self) -> Quaternion:
        return self._world_rotation or self._calc_world_rotation()

    def _calc_world_position(self) -> Vector3:
        if self._world_position:
            return self._world_position

        d: Vector3 = self.local_position
        q: Quaternion = self.local_rotation

        if self._parent:
            d = self._parent._calc_world_position()
            q = self._parent._calc_world_rotation() * q

        p = self.local_position
        p = q.as_matrix().multiply_matrix(p.as_matrix()).to_vector()
        return p + d if d else p

    def _calc_world_rotation(self) -> Quaternion:
        if self._world_rotation:
            return self._world_rotation
        q = self.local_rotation
        if self._parent:
            p_q = self._parent._calc_world_rotation()
            q = p_q * q
        return q

    def cache(self):
        self._world_position = self._calc_world_position()
        self._world_rotation = self._calc_world_rotation()

    # def transform(self, v: Float3, parent: np.array = None) -> Float3:
    #     vw = v[0], v[1], v[2], 1
    #     m = self.local_to_world(parent)
    #     r = np.matmul(m, vw)
    #     return r[0], r[1], r[2]
    #
    # def get_position(self) -> Float3:
    #     pos = (0, 0, 0)
    #     return self.transform(pos)
    #
    # def get_simple_position(self) -> Float3:
    #     dx, dy, dz = 0, 0, 0
    #     if self._parent:
    #         dx, dy, dz = self._parent.get_simple_position()
    #     x, y, z = self.local_position
    #     return x + dx, y + dy, z + dz

    @classmethod
    def create(cls, chunk: SkelChunk) -> List['Skeleton']:
        temp = [Skeleton(bone.name, Vector3(*bone.pos), Quaternion(*bone.quaternion), bone.parent_index) for bone in chunk.bones]
        for t in temp:
            t._children = []

        for i, bone in enumerate(chunk.bones):
            if bone.parent_index != -1:
                temp[i]._parent = temp[bone.parent_index]
                temp[bone.parent_index]._children.append(temp[i])
            temp[i].cache()
        return temp


    @classmethod
    def create_wxyz(cls, chunk: SkelChunk) -> List['Skeleton']:
        temp = [Skeleton(bone.name, Vector3(*bone.pos), Quaternion.WXYZ(*bone.quaternion), bone.parent_index) for bone in chunk.bones]
        for t in temp:
            t._children = []

        for i, bone in enumerate(chunk.bones):
            if bone.parent_index != -1:
                temp[i]._parent = temp[bone.parent_index]
                temp[bone.parent_index]._children.append(temp[i])
            temp[i].cache()
        return temp

    @classmethod
    def create_xyzw(cls, chunk: SkelChunk) -> List['Skeleton']:
        temp = [Skeleton(bone.name, Vector3(*bone.pos), Quaternion.XYZW(*bone.quaternion), bone.parent_index) for bone in chunk.bones]
        for t in temp:
            t._children = []

        for i, bone in enumerate(chunk.bones):
            if bone.parent_index != -1:
                temp[i]._parent = temp[bone.parent_index]
                temp[bone.parent_index]._children.append(temp[i])
            temp[i].cache()
        return temp
