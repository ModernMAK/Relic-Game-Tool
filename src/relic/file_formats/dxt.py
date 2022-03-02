# FINALLY DXT DOCUMENTATION
# http://doc.51windows.net/directx9_sdk/graphics/reference/DDSFileReference/ddsfileformat.htm
# http://doc.51windows.net/directx9_sdk/graphics/reference/DDSFileReference/ddstextures.htm
import struct

DDS_MAGIC = "DDS ".encode("ascii")
_HEADER = struct.Struct("< 7l 44s 32s 16s 4s")
__DDPIXELFORMAT = struct.Struct("< l l 4s 5l")  # 32s
__DDCAP = struct.Struct("< l l 8s")

_DXT1 = "DXY1"
_DXT3 = "DXT3"
_DXT5 = "DXT5"
_DEFAULT_FLAGS = 0x00001007
_dwF_MIPMAP = 0x00020000
_dwF_DEPTH = 0x00800000
_dwF_PITCH = 0x00000008
_dwF_LINEAR = 0x00080000
_ddsF_FOURCC = 0x00000004
# I'm under the assumption that I can specify mipmap and then set count to 0
# I COULD alternatively flag when mips aren't present and then make a different constant
# According to 'http://doc.51windows.net/directx9_sdk/graphics/reference/DDSFileReference/ddsfileformat.htm#surface_format_header'
#   Linearsize is the size of the bytes for main image, assuming main image is the data segment,
_DOW_DXT_FLAGS = _DEFAULT_FLAGS | _dwF_MIPMAP | _dwF_LINEAR

_ddscaps_F_TEXTURE = 0x1000
_ddscaps_F_COMPLEX = 0x8
_ddscaps_F_MIPMAP_S = 0x400000
_ddscaps_F_MIPMAP = _ddscaps_F_COMPLEX | _ddscaps_F_MIPMAP_S

# Mipmap requires complex? (Acording to DirectXTex's dds.h)
_DOW_DDSCAPS_FLAGS = _ddscaps_F_TEXTURE | _ddscaps_F_MIPMAP


# Does not include magic
def calculate_dxt_surface_format_header(width: int, height: int, size: int, pixel_format: bytes, dds_caps: bytes,
                                        mips: int = 0) -> bytes:
    _RES_44 = ("\00" * 44).encode("ascii")
    _RES_4 = ("\00" * 4).encode("ascii")

    return _HEADER.pack(124, _DOW_DXT_FLAGS, width, height, size, 0, mips, _RES_44, pixel_format, dds_caps, _RES_4)


def calculate_compressed_dxt_pixel_format(format: str):
    return __DDPIXELFORMAT.pack(32, _ddsF_FOURCC, format.encode("ASCII"), 0, 0, 0, 0, 0)


def calculate_dxt_ddscaps(ddscaps_flags: int = _DOW_DDSCAPS_FLAGS, seconadry_flags: int = 0):
    _RES_8 = ("\00" * 8).encode("ascii")
    return __DDCAP.pack(ddscaps_flags, seconadry_flags, _RES_8)


# DOES NOT INCLUDE DDS MAGIC WORD
def get_full_dxt_header(format: str, width: int, height: int, size: int, mips: int = 0,
                        ddscaps_flags: int = _DOW_DDSCAPS_FLAGS, seconadry_flags: int = 0):
    pixel_format = calculate_compressed_dxt_pixel_format(format)
    caps = calculate_dxt_ddscaps(ddscaps_flags, seconadry_flags)
    return calculate_dxt_surface_format_header(width, height, size, pixel_format, caps, mips)


# TGA
# http://www.paulbourke.net/dataformats/tga/
_TGA_HEADER = struct.Struct("< b b b h h b h h h h b b")

# OH, BOY
_TGA_16_0 = 0x0
_TGA_16_1 = 0x1
_TGA_32 = 0x8
_TGA_24 = 0x0

_SCREEN_ORGIN_LOWER = 0x0
_SCREEN_ORGIN_UPPER = 1 << 5

_NONINTERLAVED = 0x00 << 6
_EvenOddInterlave = 0x01 << 6
_FourWay = 0x10 << 6
_ILLEGAL = 0x11 << 6

# I don't fully understand non-interleaved, but nothing broke when it was set
#   I'd imagine that RGB(A) would be interleaved as such, but maybe not, IDK
_DOW_FORMAT = _TGA_32 | _SCREEN_ORGIN_LOWER | _NONINTERLAVED

# SEE TGA spec linked 'http://www.paulbourke.net/dataformats/tga/'
_COLOR = 2
_GRAY = 3


def build_dow_tga_color_header(width: int, height: int):
    _PIXEL_SIZE = 32
    return _TGA_HEADER.pack(0, 0, _COLOR, 0, 0, 0, 0, 0, width, height, _PIXEL_SIZE, _DOW_FORMAT)


def build_dow_tga_gray_header(width: int, height: int):
    _PIXEL_SIZE = 8  # size seems roughly 1/4th the size of the color
    return _TGA_HEADER.pack(0, 0, _GRAY, 0, 0, 0, 0, 0, width, height, _PIXEL_SIZE, _DOW_FORMAT)
