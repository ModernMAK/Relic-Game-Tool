# Original https://gist.github.com/nfette/83ab3492738a95b248def4239f3843cd

from struct import unpack, pack


def unpack_float80(b: bytes) -> float:
    exponent, mantissa = unpack('<hQ', b)
    return mantissa * (2 ** (-63 + exponent))


def pack_float80(v:float) -> bytes:
    packed = pack("<d", v)
    sign = packed[0] & (1 << 7) == (1 << 7)
    exponent = (packed[0] << 8 + packed[1]) >> 4
    fraction = unpack("<Q",packed)[0]
    fraciton_mask = ~(0b111111111111) << 52
    fraction &= fraciton_mask

    signed_exponent = (1 if sign else 0) << 15 + exponent + 16 # add 16 for missing bits
    fraction <<= 16 # shift left to keep mantissa sign
    return pack("<hQ",signed_exponent, fraction)





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
