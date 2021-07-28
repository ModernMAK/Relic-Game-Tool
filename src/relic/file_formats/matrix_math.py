from dataclasses import dataclass


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

    def multiply_matrix(self, m: 'Matrix') -> 'Matrix':
        left = self
        right = m
        assert left.cols == right.rows
        items = left.cols
        l_m = left._array
        r_m = right._array
        output = [[None for _ in range(left.cols)] for _ in range(right.rows)]

        for row in range(left.rows):
            for col in range(right.cols):
                sum = 0
                for i in range(items):
                    sum += l_m[row][i] * r_m[i][col]
                output[row][col] = sum
        return Matrix(output)


@dataclass
class Quaternion:
    x: float
    y: float
    z: float
    w: float

    @property
    def xyzw(self):
        return self.x, self.y, self.z, self.w

    @property
    def wxyz(self):
        return self.w, self.x, self.y, self.z

    @classmethod
    def XYZW(cls, x: float, y: float, z: float, w: float) -> 'Quaternion':
        return Quaternion(x, y, z, w)

    @classmethod
    def WXYZ(cls, w: float, x: float, y: float, z: float) -> 'Quaternion':
        return Quaternion(x, y, z, w)

    def _quaternion_multiply(self, other: 'Quaternion') -> 'Quaternion':
        a, b, c, d = self.wxyz
        e, f, g, h = other.wxyz
        return Quaternion.WXYZ(
            a * e - b * f - c * g - d * h,
            b * e + a * f + c * h - d * g,
            a * g - b * h + c * e + d * f,
            a * h + b * g - c * f + d * e
        )

    def as_matrix(self) -> Matrix:
        m = [[None, None, None], [None, None, None], [None, None, None]]

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
