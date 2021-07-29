from dataclasses import dataclass
from enum import Enum, auto
from math import sqrt
from typing import Tuple, Any, List


class Matrix:
    def __init__(self, array):
        self._array = array
        self.rows = len(self._array)
        self.cols = len(self._array[0])

        for r in range(1, self.rows):
            assert len(self._array) == self.rows

    def to_vector(self) -> 'Vector3':
        # assert self.rows == 3
        # assert self.cols == 1
        m = self._array
        if self.rows == 3:
            return Vector3(m[0][0], m[1][0], m[2][0])
        elif self.cols == 3:
            return Vector3(m[0][0], m[0][1], m[0][2])
        raise NotImplementedError

    def __get_rc(self, index: int) -> Tuple[int, int]:
        row = int(index // self.cols)
        col = index % self.cols
        return row, col

    def get_flat(self, index: int):
        row, col = self.__get_rc(index)
        return self.get(row, col)

    def set_flat(self, index: int, value: Any):
        row, col = self.__get_rc(index)
        return self.set(row, col, value)

    def get(self, row: int, col: int = 0):
        return self._array[row][col]

    def set(self, row: int, col: int, value: Any):
        self._array[row][col] = value

    def multiply_matrix(self, m: 'Matrix') -> 'Matrix':
        left = self
        right = m
        assert left.cols == right.rows
        items = left.cols
        l_m = left._array
        r_m = right._array
        output: List[List] = [[None for _ in range(left.cols)] for _ in range(right.rows)]

        for row in range(left.rows):
            for col in range(right.cols):
                sum = 0
                for i in range(items):
                    sum += l_m[row][i] * r_m[i][col]
                output[row][col] = sum
        return Matrix(output)

    @classmethod
    def __get_2x2_determinant(cls, a: int, b: int, c: int, d: int):
        return (a * d) - (b * c)

    @classmethod
    def __determinant_2x2(cls, matrix: 'Matrix'):
        assert matrix.rows == 2
        assert matrix.cols == 2
        matrix = matrix._array
        a, b, c, d = matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1]
        return cls.__get_2x2_determinant(a, b, c, d)

    @classmethod
    def __determinant_3x3(cls, matrix: 'Matrix') -> int:
        assert matrix.rows == 3
        assert matrix.cols == 3
        matrix = matrix._array
        a, b, c = matrix[0][0], matrix[0][1], matrix[0][2]
        d, e, f = matrix[1][0], matrix[1][1], matrix[1][2]
        g, h, i = matrix[2][0], matrix[2][1], matrix[2][2]
        a_det = cls.__get_2x2_determinant(e, f, h, i)
        b_det = cls.__get_2x2_determinant(d, f, g, i)
        c_det = cls.__get_2x2_determinant(d, e, g, h)
        return a * a_det - b * b_det + c * c_det

    @classmethod
    def __inverse_2x2(cls, matrix: 'Matrix') -> 'Matrix':
        assert matrix.rows == 2
        assert matrix.cols == 2
        matrix = matrix._array
        a, b, c, d = matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1]
        determinant = cls.__get_2x2_determinant(a, b, c, d)
        assert determinant != 0
        new_matrix = [[d / determinant, -b / determinant],
                      [-c / determinant, a / determinant]]
        return Matrix(new_matrix)

    @classmethod
    def __get_minor_3x3_part(cls, matrix: 'Matrix', r: int, c: int) -> int:
        minor = []
        for r_i in range(3):
            for c_i in range(3):
                if r == r_i or c == c_i:
                    continue
                minor.append(matrix.get(r_i, c_i))
        return cls.__get_2x2_determinant(*minor)

    @classmethod
    def __get_minor_3x3(cls, matrix: 'Matrix') -> List[List[int]]:
        return [[cls.__get_minor_3x3_part(matrix, r, c) for c in range(3)] for r in range(3)]

    @classmethod
    def __apply_3x3_cofactor(cls, minor: List[List[int]]):
        minor[0][1] *= -1
        minor[1][0] *= -1
        minor[1][2] *= -1
        minor[2][1] *= -1

    @classmethod
    def __apply_3x3_adjugate(cls, minor: List[List[int]]):
        # Reflect over the 'Diagonal'
        temp10 = minor[1][0]
        temp20 = minor[2][0]
        temp21 = minor[2][0]

        minor[1][0] = minor[0][1]
        minor[2][0] = minor[0][2]
        minor[2][1] = minor[1][2]

        minor[0][1] = temp10
        minor[0][2] = temp20
        minor[1][2] = temp21

    @classmethod
    def __inverse_3x3(cls, matrix: 'Matrix') -> 'Matrix':
        assert matrix.rows == 3
        assert matrix.cols == 3
        determinant = cls.__determinant_3x3(matrix)
        if determinant == 0:
            raise NotImplementedError

        inverse = cls.__get_minor_3x3(matrix)
        cls.__apply_3x3_cofactor(inverse)
        cls.__apply_3x3_adjugate(inverse)
        for r in range(3):
            for c in range(3):
                inverse[r][c] = inverse[r][c] / determinant
        return Matrix(inverse)

    def inverse(self) -> 'Matrix':
        if self.rows != self.cols:
            raise NotImplementedError
        elif self.rows == 3:
            return Matrix.__inverse_3x3(self)
        elif self.rows == 2:
            return Matrix.__inverse_2x2(self)
        else:
            raise NotImplementedError

    def determinant(self) -> int:
        if self.rows != self.cols:
            raise NotImplementedError
        elif self.rows == 3:
            return Matrix.__determinant_3x3(self)
        elif self.rows == 2:
            return Matrix.__determinant_2x2(self)
        else:
            raise NotImplementedError

    def __matmul__(self, other) -> 'Matrix':
        if isinstance(other, Matrix):
            return self.multiply_matrix(other)
        else:
            raise NotImplementedError


class AxisOrder(Enum):
    XYZ = auto()
    XZY = auto()

    YXZ = auto()
    YZX = auto()

    ZXY = auto()
    ZYX = auto()

    @property
    def axis_conversions(self) -> int:
        _axis_order_conversions = {AxisOrder.XYZ: 0, AxisOrder.XZY: 1, AxisOrder.YXZ: 1, AxisOrder.YZX: 2,
                                   AxisOrder.ZXY: 2, AxisOrder.ZYX: 1}
        return _axis_order_conversions[self]

    def swap(self, x, y, z) -> Tuple[Any, Any, Any]:
        swaps = {
            self.XYZ: (x, y, z),
            self.XZY: (x, z, y),
            self.YXZ: (y, x, z),
            self.YZX: (y, z, x),
            self.ZXY: (z, x, y),
            self.ZYX: (z, y, x)
        }
        return swaps[self]


@dataclass
class Quaternion:
    x: float
    y: float
    z: float
    w: float

    @property
    def xyzw(self):
        return [self.x, self.y, self.z, self.w]

    @property
    def wxyz(self):
        return [self.w, self.x, self.y, self.z]

    # Helper Methods to specify Layout
    @classmethod
    def Scalar(cls, v: float) -> 'Quaternion':
        return Quaternion(v, v, v, v)

    @classmethod
    def XYZW(cls, x: float, y: float, z: float, w: float) -> 'Quaternion':
        return Quaternion(x, y, z, w)

    @classmethod
    def WXYZ(cls, w: float, x: float, y: float, z: float) -> 'Quaternion':
        return Quaternion(x, y, z, w)

    def Swap(self, ordering: AxisOrder = AxisOrder.XYZ):
        conversions = ordering.axis_conversions
        if conversions == 0:
            return self
        else:
            xyzw = self.xyzw
            w = xyzw[3]
            xyz = xyzw[:3]
            xyz = ordering.swap(*xyz)

            if conversions % 2 == 1:
                w *= -1
            return Quaternion.XYZW(*xyz, w)

    # Performs AXIS inversion
    def Invert(self, x: bool = False, y: bool = False, z: bool = False, w: bool = False) -> 'Quaternion':
        if not any([x, y, z, w]):
            return self

        axis_negations = 0
        inverts = [x, y, z]
        values = self.xyzw
        # Handle Axis flipping, this will affect the angle if we
        for i in range(3):
            if inverts[i]:
                values[i] *= -1
                axis_negations += 1
        # Handle Angle Flip manually (This doesn't affect anything else)
        if w:
            values[3] *= -1
        # Preserve Angle
        if axis_negations % 2 == 1:
            values[3] *= -1
        return Quaternion.XYZW(*values)

    def _quaternion_multiply(self, other: 'Quaternion') -> 'Quaternion':
        left_w, left_x, left_y, left_z = self.wxyz
        right_w, right_x, right_y, right_z = other.wxyz
        return Quaternion.WXYZ(
            left_w * right_w - left_x * right_x - left_y * right_y - left_z * right_z,
            left_x * right_w + left_w * right_x + left_y * right_z - left_z * right_y,
            left_w * right_y - left_x * right_z + left_y * right_w + left_z * right_x,
            left_w * right_z + left_x * right_y - left_y * right_x + left_z * right_w
        )

    def conjugate(self) -> 'Quaternion':
        return Quaternion(-self.x, -self.y, -self.z, self.w)

    def inverse(self) -> 'Quaternion':
        x, y, z, w = self.xyzw
        sum = x ** 2 + y ** 2 + z ** 2 + w ** 2
        x, y, z, w = self.conjugate().xyzw
        return Quaternion.XYZW(-x / sum, -y / sum, -z / sum, w / sum)

    def as_matrix(self) -> Matrix:
        m: List[List, List, List] = [[None, None, None], [None, None, None], [None, None, None]]

        m[0][0] = 2 * (self.x ** 2 + self.y ** 2) - 1
        m[0][1] = 2 * (self.y * self.z - self.x * self.w)
        m[0][2] = 2 * (self.y * self.w + self.x * self.z)

        m[1][0] = 2 * (self.y * self.z + self.x * self.w)
        m[1][1] = 2 * (self.x ** 2 + self.z ** 2) - 1
        m[1][2] = 2 * (self.z * self.w - self.x * self.y)

        m[2][0] = 2 * (self.y * self.w - self.x * self.z)
        m[2][1] = 2 * (self.z * self.w + self.x * self.y)
        m[2][2] = 2 * (self.x ** 2 + self.w ** 2) - 1

        return Matrix(m)

    @classmethod
    def from_matrix_quick(cls, m: Matrix) -> 'Quaternion':
        w = sqrt(1 + m.get(0, 0) + m.get(1, 1) + m.get(2, 2)) / 2
        x = (m.get(2, 1) - m.get(1, 2)) / (4 * w)
        y = (m.get(0, 2) - m.get(2, 0)) / (4 * w)
        z = (m.get(1, 0) - m.get(0, 1)) / (4 * w)
        return Quaternion.XYZW(x, y, z, w)

    @classmethod
    def from_matrix(cls, m: Matrix) -> 'Quaternion':
        # STOLEN 'https://d3cw3dd2w32x2b.cloudfront.net/wp-content/uploads/2015/01/matrix-to-quat.pdf'
        m = m._array
        m00 = m[0][0]
        m11 = m[1][1]
        m22 = m[2][2]
        if m22 < 0:
            if m00 > m11:
                t = 1 + m00 - m11 - m22
                return Quaternion(t, m[0][1] + m[1][0], m[2][0] + m[0][2], m[1][2] - m[2][1])
            else:
                t = 1 - m00 + m11 - m22
                return Quaternion(m[0][1] + m[1][0], t, m[1][2] + m[2][1], m[2][0] - m[0][2])
        else:
            if m00 < -m11:
                t = 1 - m00 - m11 + m22
                return Quaternion(m[2][0] + m[0][2], m[1][2] + m[2][1], t, m[0][1] - m[1][0])
            else:
                t = 1 + m00 + m11 + m22
                return Quaternion(m[1][2] - m[2][1], m[2][0] - m[0][2], m[0][1] - m[1][0], t)

    def __mul__(self, other):
        if isinstance(other, Quaternion):
            return self._quaternion_multiply(other)
        elif isinstance(other, (int, float)):
            x, y, z, w = self.xyzw
            return Quaternion(x * other, y * other, z * other, w * other)
        else:
            raise NotImplementedError

    def __add__(self, other):
        if isinstance(other, Quaternion):
            dx, dy, dz, dw = other.xyzw
        elif isinstance(other, (int, float)):
            dx, dy, dz, dw = other, other, other, other
        else:
            raise NotImplementedError
        return Quaternion(self.x + dx, self.y + dy, self.z + dz, self.w + dw)

    def __sub__(self, other):
        if isinstance(other, Quaternion):
            dx, dy, dz, dw = other.xyzw
        elif isinstance(other, (int, float)):
            dx, dy, dz, dw = other, other, other, other
        else:
            raise NotImplementedError
        return Quaternion(self.x - dx, self.y - dy, self.z - dz, self.w - dw)


@dataclass
class Vector3:
    x: float
    y: float
    z: float

    # SWIZZLES
    @property
    def xyz(self):
        return self.x, self.y, self.z

    @property
    def xzy(self):
        return self.x, self.z, self.y

    @property
    def yxz(self):
        return self.y, self.x, self.z

    @property
    def yzx(self):
        return self.y, self.z, self.x

    @property
    def zxy(self):
        return self.z, self.x, self.y

    @property
    def zyx(self):
        return self.z, self.y, self.x

    # OPERATORS
    def __neg__(self):
        return Vector3(-self.x, -self.y, -self.z)

    def __add__(self, other):
        if isinstance(other, Vector3):
            x, y, z = other.xyz
        elif isinstance(other, (float, int)):
            x, y, z = other, other, other
        else:
            raise NotImplementedError(other)
        return Vector3(self.x + x, self.y + y, self.z + z)

    def __sub__(self, other):
        if isinstance(other, Vector3):
            x, y, z = other.xyz
        elif isinstance(other, (float, int)):
            x, y, z = other, other, other
        else:
            raise NotImplementedError(other)
        return Vector3(self.x - x, self.y - y, self.z - z)

    def __mul__(self, other):
        if isinstance(other, Vector3):
            x, y, z = other.xyz
        elif isinstance(other, (float, int)):
            x, y, z = other, other, other
        else:
            raise NotImplementedError(other)
        return Vector3(self.x * x, self.y * y, self.z * z)

    def __mod__(self, other):
        if isinstance(other, Vector3):
            x, y, z = other.xyz
        elif isinstance(other, (float, int)):
            x, y, z = other, other, other
        else:
            raise NotImplementedError(other)
        return Vector3(self.x % x, self.y % y, self.z % z)

    def __truediv__(self, other):
        if isinstance(other, Vector3):
            x, y, z = other.xyz
        elif isinstance(other, (float, int)):
            x, y, z = other, other, other
        else:
            raise NotImplementedError(other)
        return Vector3(self.x / x, self.y / y, self.z / z)

    def __floordiv__(self, other):
        if isinstance(other, Vector3):
            x, y, z = other.xyz
        elif isinstance(other, (float, int)):
            x, y, z = other, other, other
        else:
            raise NotImplementedError(other)
        return Vector3(self.x // x, self.y // y, self.z // z)

    def as_matrix(self) -> Matrix:
        return Matrix([[self.x], [self.y], [self.z]])


if __name__ == "__main__":
    q_arr = [-0.5, 0.5, 0.5, -0.5]
    q_wxyz = Quaternion.WXYZ(*q_arr)
    q_xyzw = Quaternion.XYZW(*q_arr)

    m_wxyz = q_wxyz.as_matrix()
    m_xyzw = q_xyzw.as_matrix()

    o = Vector3(0, 1.012724, 0)
    p = Vector3(0, 0, 0.158141)
    p_m = Matrix.from_vector_3x1(p)

    p_m_wxyz = m_wxyz.multiply_matrix(p_m)
    p_m_xyzw = m_xyzw.multiply_matrix(p_m)

    p_wxyz = p_m_wxyz.to_vector()
    p_xyzw = p_m_xyzw.to_vector()

    wo_rot = o + p
    w_rot_wxyz = o + p_wxyz
    w_rot_xyzw = o + p_xyzw

    print("Without    :\t", wo_rot.x, wo_rot.y, wo_rot.z)
    print("With   WXYZ:\t", w_rot_wxyz.x, w_rot_wxyz.y, w_rot_wxyz.z, "\t", *q_wxyz.xyzw)
    print("With   XYZW:\t", w_rot_xyzw.x, w_rot_xyzw.y, w_rot_xyzw.z, "\t", *q_xyzw.xyzw)
