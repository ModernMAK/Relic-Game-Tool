# Original https://gist.github.com/nfette/83ab3492738a95b248def4239f3843cd

from struct import unpack, pack


def unpack_float80(b: bytes) -> float:
    raise NotImplementedError
    # exponent, mantissa = unpack('<hQ', b)
    # s = exponent & (1 << 15)



def pack_float80(v: float) -> bytes:
    packed = pack("<d", v)
    unpacked = unpack("<Q", packed)[0]
    sign_flag = (1 << 63)
    exponent_mask = ~(0b11111111111) << (52)
    fraction_mask = ~(0b111111111111) << (52)

    sign = unpacked & sign_flag >> 63  # 1 bit
    exponent = (unpacked & exponent_mask) >> 52  # 11 bits
    fraction = (unpacked & fraction_mask)  # 52 bits

    exponent = (exponent - 1023)  # on float64 -/+ scale (centered on 0)
    exponent = exponent + 16383  # on float80 0/+ scale
    fraction = fraction << 12

    signed_exponent = (sign << 15) | exponent
    return pack("<hQ", signed_exponent, fraction)

#
# if __name__ == "__main__":
#     import gmpy2
#
#     gmpy2.set_context(float80ctx)
#     for h in '0000000000000080ff3f 00000000000000800040 7250177718759da7e373'.split():
#         print(convertBytes(bytes.fromhex(h)).__repr__())
#
#     # mpfr('1.0',64)
#     # mpfr('2.0',64)
#     # mpfr('9.98999999999999990535e+3998',64)
#

