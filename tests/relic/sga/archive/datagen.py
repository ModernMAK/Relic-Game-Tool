import hashlib
from typing import Tuple, List

from serialization_tools.ioutil import WindowPtr, Ptr

from relic.sga import ArchiveHeader, DowIArchiveHeader, DowIIArchiveHeader, DowIIIArchiveHeader, Archive, VirtualDrive, VirtualDriveHeader, Folder, FolderHeader, File, FileHeader, DowIIArchive, DowIArchive, DowIIIArchive, \
    DowIIIFolderHeader, DowIIIFileHeader, DowIIIVirtualDriveHeader, DowIVirtualDriveHeader, DowIFolderHeader, DowIFileHeader, FileCompressionFlag, DowIIFolderHeader, DowIIVirtualDriveHeader, DowIIFileHeader
from relic.sga.common import ArchiveRange


def encode_and_pad(v: str, byte_size: int, encoding: str) -> bytes:
    v_enc = v.encode(encoding)
    v_pad = b"\0" * (byte_size - len(v_enc))
    return v_enc + v_pad


def gen_dow1_header_and_buffer(name: str, toc_size: int, data_offset: int, toc_pos: int = None, csum1: bytes = None, csum2: bytes = None) -> Tuple[ArchiveHeader, bytes, bytes]:
    version = b"\x02\0\0\0"
    name_enc = encode_and_pad(name, 128, "utf-16-le")
    csum1 = b"\x01\x02\0\x04\0\0\0\x08\0\0\0\0\0\0\0\0" if csum1 is None else csum1
    csum2 = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f" if csum2 is None else csum2
    toc_size_enc = int.to_bytes(toc_size, 4, "little", signed=False)
    data_offset_enc = int.to_bytes(data_offset, 4, "little", signed=False)
    TOC_POS = 180 if toc_pos is None else toc_pos
    shared = version + csum1 + name_enc + csum2 + toc_size_enc + data_offset_enc
    header = DowIArchiveHeader(name, WindowPtr(TOC_POS, toc_size), WindowPtr(data_offset), (csum1, csum2))
    good = "_ARCHIVE".encode("ascii") + shared
    bad = f"garbage_".encode("ascii") + shared
    return header, good, bad


def _gen_dow1_archive_toc(vdrive: str, folder: str, file: str, file_uncomp_data: bytes):
    def ushort(v) -> bytes:
        return int.to_bytes(v, length=2, byteorder="little", signed=False)

    def uint(v) -> bytes:
        return int.to_bytes(v, length=4, byteorder="little", signed=False)

    USHORT_ZERO = ushort(0)
    USHORT_ONE = ushort(1)
    UINT_ZERO = uint(0)
    VDRIVE_UNK = b"\xde\xad"
    vdrive_buf = encode_and_pad("data", 64, "ascii") + encode_and_pad(vdrive, 64, "ascii") + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE + VDRIVE_UNK
    file_size_enc = uint(len(file_uncomp_data))
    file_buf = uint(len(folder) + 1) + UINT_ZERO + UINT_ZERO + file_size_enc + file_size_enc
    folder_buf = UINT_ZERO + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE
    name_buf = encode_and_pad(folder, len(folder) + 1, "ascii") + encode_and_pad(file, len(file) + 1, "ascii")
    toc_buf = vdrive_buf + folder_buf + file_buf + name_buf
    PTR_OFF = 24  # 4 * (2 + 6)
    vdrive_off = 0 + PTR_OFF
    folder_off = vdrive_off + len(vdrive_buf)
    file_off = folder_off + len(folder_buf)
    name_off = file_off + len(folder_buf)
    toc_ptr_buf = uint(vdrive_off) + USHORT_ONE + uint(folder_off) + USHORT_ONE + uint(file_off) + USHORT_ONE + uint(name_off) + USHORT_ONE

    return toc_ptr_buf, toc_buf


def gen_dow1_archive_toc(vdrive: str, folder: str, file: str, file_uncomp_data: bytes):
    def ushort(v) -> bytes:
        return int.to_bytes(v, length=2, byteorder="little", signed=False)

    def uint(v) -> bytes:
        return int.to_bytes(v, length=4, byteorder="little", signed=False)

    USHORT_ZERO = ushort(0)
    USHORT_ONE = ushort(1)
    UINT_ZERO = uint(0)
    VDRIVE_UNK = b"\xde\xad"
    vdrive_buf = encode_and_pad("data", 64, "ascii") + encode_and_pad(vdrive, 64, "ascii") + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE + VDRIVE_UNK
    file_size_enc = uint(len(file_uncomp_data))
    file_buf = uint(len(folder) + 1) + UINT_ZERO + UINT_ZERO + file_size_enc + file_size_enc
    folder_buf = UINT_ZERO + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE
    name_buf = encode_and_pad(folder, len(folder) + 1, "ascii") + encode_and_pad(file, len(file) + 1, "ascii")
    toc_buf = vdrive_buf + folder_buf + file_buf + name_buf
    PTR_OFF = 24  # 4 * (2 + 6)
    vdrive_off = 0 + PTR_OFF
    folder_off = vdrive_off + len(vdrive_buf)
    file_off = folder_off + len(folder_buf)
    name_off = file_off + len(file_buf)
    toc_ptr_buf = uint(vdrive_off) + USHORT_ONE + uint(folder_off) + USHORT_ONE + uint(file_off) + USHORT_ONE + uint(name_off) + ushort(2)

    vdrive_h = DowIVirtualDriveHeader("data", vdrive, ArchiveRange(0, 1), ArchiveRange(0, 1), VDRIVE_UNK)
    folder_h = DowIFolderHeader(0, ArchiveRange(0, 0), ArchiveRange(0, 1))
    file_h = DowIFileHeader(Ptr(len(folder) + 1), Ptr(0), len(file_uncomp_data), len(file_uncomp_data), FileCompressionFlag.Decompressed)
    file_obj = File(file_h, file, file_uncomp_data, True, None, None)
    folder_obj = Folder(folder_h, folder, [], [file_obj], None, None)
    vdrive_obj = VirtualDrive(vdrive_h, [folder_obj], [file_obj])
    file_obj._parent = folder_obj
    file_obj._drive = vdrive_obj
    folder_obj._drive = vdrive_obj
    return [vdrive_obj], (toc_ptr_buf, toc_buf)


def _gen_dow1_archive(archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes) -> bytes:
    ARCHIVE_HEADER_SIZE = 180
    full_toc = toc_ptrs + toc
    EIGENS = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))

    def gen_csum(buffer: bytes, eigen: bytes) -> bytes:
        hasher = hashlib.md5(eigen)
        hasher.update(buffer)
        return bytes.fromhex(hasher.hexdigest())

    csum2 = gen_csum(full_toc, EIGENS[1])
    toc_and_data = full_toc + data
    csum1 = gen_csum(toc_and_data, EIGENS[0])
    _, archive_header_buf, _ = gen_dow1_header_and_buffer(archive_name, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), csum1=csum1, csum2=csum2)
    return archive_header_buf + toc_and_data


def gen_dow1_archive(archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes, drives: List[VirtualDrive] = None, sparse: bool = False) -> Tuple[Archive, bytes]:
    ARCHIVE_HEADER_SIZE = 180
    full_toc = toc_ptrs + toc
    EIGENS = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))

    def gen_csum(buffer: bytes, eigen: bytes) -> bytes:
        hasher = hashlib.md5(eigen)
        hasher.update(buffer)
        return bytes.fromhex(hasher.hexdigest())

    csum2 = gen_csum(full_toc, EIGENS[1])
    toc_and_data = full_toc + data
    csum1 = gen_csum(toc_and_data, EIGENS[0])
    header, archive_header_buf, _ = gen_dow1_header_and_buffer(archive_name, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), csum1=csum1, csum2=csum2)
    archive = DowIArchive(header, drives, sparse)

    return archive, archive_header_buf + toc_and_data


def _full_gen_dow1_archive(archive_name: str, folder: str, file: str, file_uncomp_data: bytes):
    toc_ptr, toc = _gen_dow1_archive_toc(archive_name, folder, file, file_uncomp_data)
    return _gen_dow1_archive(archive_name, toc_ptr, toc, file_uncomp_data)


def full_gen_dow1_archive(archive_name: str, folder: str, file: str, file_uncomp_data: bytes):
    drives, (toc_ptr, toc) = gen_dow1_archive_toc(archive_name, folder, file, file_uncomp_data)
    return gen_dow1_archive(archive_name, toc_ptr, toc, file_uncomp_data, drives, False)


def gen_dow2_header_and_buffer(name: str, toc_size: int, data_offset: int, toc_pos: int, unk: int, csum1: bytes = None, csum2: bytes = None) -> Tuple[ArchiveHeader, bytes, bytes]:
    version = b"\x05\0\0\0"
    name_enc = name.encode("utf-16-le")
    name_pad = b"\0" * (128 - len(name) * 2)
    csum1 = b"\x01\x02\0\x04\0\0\0\x08\0\0\0\0\0\0\0\0" if csum1 is None else csum1
    csum2 = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f" if csum2 is None else csum2
    toc_size_enc = int.to_bytes(toc_size, 4, "little", signed=False)
    data_offset_enc = int.to_bytes(data_offset, 4, "little", signed=False)
    toc_pos_enc = int.to_bytes(toc_pos, 4, "little", signed=False)
    RSV_1 = int.to_bytes(1, 4, "little", signed=False)
    RSV_0 = int.to_bytes(0, 4, "little", signed=False)
    unk_enc = int.to_bytes(unk, 4, "little", signed=False)
    shared = version + csum1 + name_enc + name_pad + csum2 + toc_size_enc + data_offset_enc + toc_pos_enc + RSV_1 + RSV_0 + unk_enc

    header = DowIIArchiveHeader(name, WindowPtr(toc_pos, toc_size), WindowPtr(data_offset), (csum1, csum2), unk)
    good = "_ARCHIVE".encode("ascii") + shared
    bad = f"garbage_".encode("ascii") + shared
    return header, good, bad


def _gen_dow2_archive_toc(vdrive: str, folder: str, file: str, file_uncomp_data: bytes):
    def ushort(v) -> bytes:
        return int.to_bytes(v, length=2, byteorder="little", signed=False)

    def uint(v) -> bytes:
        return int.to_bytes(v, length=4, byteorder="little", signed=False)

    USHORT_ZERO = ushort(0)
    USHORT_ONE = ushort(1)
    UINT_ZERO = uint(0)
    VDRIVE_UNK = b"\xde\xad"
    vdrive_buf = encode_and_pad("data", 64, "ascii") + encode_and_pad(vdrive, 64, "ascii") + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE + VDRIVE_UNK
    file_size_enc = uint(len(file_uncomp_data))
    file_buf = uint(len(folder) + 1) + UINT_ZERO + UINT_ZERO + file_size_enc + file_size_enc
    folder_buf = UINT_ZERO + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE
    name_buf = encode_and_pad(folder, len(folder) + 1, "ascii") + encode_and_pad(file, len(file) + 1, "ascii")
    toc_buf = vdrive_buf + folder_buf + file_buf + name_buf
    PTR_OFF = 24  # 4 * (2 + 6)
    vdrive_off = 0 + PTR_OFF
    folder_off = vdrive_off + len(vdrive_buf)
    file_off = folder_off + len(folder_buf)
    name_off = file_off + len(folder_buf)
    toc_ptr_buf = uint(vdrive_off) + USHORT_ONE + uint(folder_off) + USHORT_ONE + uint(file_off) + USHORT_ONE + uint(name_off) + USHORT_ONE

    return toc_ptr_buf, toc_buf


def gen_dow2_archive_toc(vdrive: str, folder: str, file: str, file_uncomp_data: bytes):
    def ushort(v) -> bytes:
        return int.to_bytes(v, length=2, byteorder="little", signed=False)

    def uint(v) -> bytes:
        return int.to_bytes(v, length=4, byteorder="little", signed=False)

    USHORT_ZERO = ushort(0)
    USHORT_ONE = ushort(1)
    UINT_ZERO = uint(0)
    VDRIVE_UNK = uint(0xdead)
    vdrive_buf = encode_and_pad("data", 64, "ascii") + encode_and_pad(vdrive, 64, "ascii") + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE + VDRIVE_UNK
    file_size_enc = uint(len(file_uncomp_data))
    file_buf = uint(len(folder) + 1) + UINT_ZERO + UINT_ZERO + file_size_enc + file_size_enc + UINT_ZERO + USHORT_ZERO
    folder_buf = UINT_ZERO + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE
    name_buf = encode_and_pad(folder, len(folder) + 1, "ascii") + encode_and_pad(file, len(file) + 1, "ascii")
    toc_buf = vdrive_buf + folder_buf + file_buf + name_buf
    PTR_OFF = 24  # 4 * (2 + 6)
    vdrive_off = 0 + PTR_OFF
    folder_off = vdrive_off + len(vdrive_buf)
    file_off = folder_off + len(folder_buf)
    name_off = file_off + len(file_buf)
    toc_ptr_buf = uint(vdrive_off) + USHORT_ONE + uint(folder_off) + USHORT_ONE + uint(file_off) + USHORT_ONE + uint(name_off) + ushort(2)

    vdrive_h = DowIIVirtualDriveHeader("data", vdrive, ArchiveRange(0, 1), ArchiveRange(0, 1), VDRIVE_UNK)
    folder_h = DowIIFolderHeader(0, ArchiveRange(0, 0), ArchiveRange(0, 1))
    file_h = DowIIFileHeader(Ptr(len(folder) + 1), Ptr(0), len(file_uncomp_data), len(file_uncomp_data), 0, 0)
    file_obj = File(file_h, file, file_uncomp_data, True, None, None)
    folder_obj = Folder(folder_h, folder, [], [file_obj], None, None)
    vdrive_obj = VirtualDrive(vdrive_h, [folder_obj], [file_obj])
    file_obj._parent = folder_obj
    file_obj._drive = vdrive_obj
    folder_obj._drive = vdrive_obj
    return [vdrive_obj], (toc_ptr_buf, toc_buf)


# Old style; depricated
def _gen_dow2_archive(archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes) -> bytes:
    ARCHIVE_HEADER_SIZE = 196  # v5.0 has an extra 16 bytes
    full_toc = toc_ptrs + toc
    EIGENS = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))

    def gen_csum(buffer: bytes, eigen: bytes) -> bytes:
        hasher = hashlib.md5(eigen)
        hasher.update(buffer)
        return bytes.fromhex(hasher.hexdigest())

    csum2 = gen_csum(full_toc, EIGENS[1])
    toc_and_data = full_toc + data
    csum1 = gen_csum(toc_and_data, EIGENS[0])
    _, archive_header_buf, _ = gen_dow2_header_and_buffer(archive_name, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), toc_pos=ARCHIVE_HEADER_SIZE, csum1=csum1, csum2=csum2,
                                                          unk=0x4d41dfff)  # UNK chosen to mostly match my knowledge of common archive files
    return archive_header_buf + toc_and_data


def gen_dow2_archive(archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes, drives: List[VirtualDrive] = None, sparse: bool = False) -> Tuple[Archive, bytes]:
    ARCHIVE_HEADER_SIZE = 196  # v5.0 has an extra 16 bytes
    full_toc = toc_ptrs + toc
    EIGENS = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))

    def gen_csum(buffer: bytes, eigen: bytes) -> bytes:
        hasher = hashlib.md5(eigen)
        hasher.update(buffer)
        return bytes.fromhex(hasher.hexdigest())

    csum2 = gen_csum(full_toc, EIGENS[1])
    toc_and_data = full_toc + data
    csum1 = gen_csum(toc_and_data, EIGENS[0])
    header, archive_header_buf, _ = gen_dow2_header_and_buffer(archive_name, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), toc_pos=ARCHIVE_HEADER_SIZE, csum1=csum1, csum2=csum2,
                                                               unk=0x4d41dfff)  # UNK chosen to mostly match my knowledge of common archive files
    return DowIIArchive(header, drives, sparse), archive_header_buf + toc_and_data


def full_gen_dow2_archive(archive_name: str, folder: str, file: str, file_uncomp_data: bytes):
    drives, (toc_ptr, toc) = gen_dow2_archive_toc(archive_name, folder, file, file_uncomp_data)
    return gen_dow2_archive(archive_name, toc_ptr, toc, file_uncomp_data, drives, False)


def gen_dow3_archive_toc(vdrive: str, folder: str, file: str, file_uncomp_data: bytes):
    def uint(v) -> bytes:
        return int.to_bytes(v, length=4, byteorder="little", signed=False)

    def ushort(v) -> bytes:
        return int.to_bytes(v, length=4, byteorder="little", signed=False)

    USHORT_ZERO = ushort(0)
    UINT_ZERO = uint(0)
    UINT_ONE = uint(1)
    VDRIVE_UNK = uint(0xdead)
    vdrive_buf = encode_and_pad("data", 64, "ascii") + encode_and_pad(vdrive, 64, "ascii") + UINT_ZERO + UINT_ONE + UINT_ZERO + UINT_ONE + VDRIVE_UNK
    file_size_enc = uint(len(file_uncomp_data))
    file_buf = uint(len(folder) + 1) + UINT_ZERO + UINT_ZERO + UINT_ZERO + file_size_enc + file_size_enc + UINT_ZERO + USHORT_ZERO + UINT_ZERO
    folder_buf = UINT_ZERO + UINT_ONE + UINT_ZERO + UINT_ONE + UINT_ONE
    name_buf = encode_and_pad(folder, len(folder) + 1, "ascii") + encode_and_pad(file, len(file) + 1, "ascii")
    toc_buf = vdrive_buf + folder_buf + file_buf + name_buf
    PTR_OFF = 24  # 4 * (2 + 6)
    vdrive_off = 0 + PTR_OFF
    folder_off = vdrive_off + len(vdrive_buf)
    file_off = folder_off + len(folder_buf)
    name_off = file_off + len(file_buf)
    toc_ptr_buf = uint(vdrive_off) + UINT_ONE + uint(folder_off) + UINT_ONE + uint(file_off) + UINT_ONE + uint(name_off) + uint(len(name_buf))

    vdrive_h = DowIIIVirtualDriveHeader("data", vdrive, ArchiveRange(0, 1), ArchiveRange(0, 1), VDRIVE_UNK)
    folder_h = DowIIIFolderHeader(0, ArchiveRange(0, 0), ArchiveRange(0, 1))
    file_h = DowIIIFileHeader(Ptr(len(folder) + 1), Ptr(0), len(file_uncomp_data), len(file_uncomp_data), 0, 0, 0, 0, 0)
    file_obj = File(file_h, file, file_uncomp_data, True, None, None)
    folder_obj = Folder(folder_h, folder, [], [file_obj], None, None)
    vdrive_obj = VirtualDrive(vdrive_h, [folder_obj], [file_obj])
    file_obj._parent = folder_obj
    file_obj._drive = vdrive_obj
    folder_obj._drive = vdrive_obj
    return [vdrive_obj], (toc_ptr_buf, toc_buf)


def gen_dow3_header_and_buffer(name: str, toc_offset: int, toc_size: int, data_offset: int, data_size: int) -> Tuple[ArchiveHeader, bytes, bytes]:
    version = b"\x09\0\0\0"
    name_enc = name.encode("utf-16-le")
    name_pad = b"\0" * (128 - len(name) * 2)
    toc_offset_enc = int.to_bytes(toc_offset, 8, "little", signed=False)
    toc_size_enc = int.to_bytes(toc_size, 4, "little", signed=False)
    data_offset_enc = int.to_bytes(data_offset, 8, "little", signed=False)
    data_size_enc = int.to_bytes(data_size, 4, "little", signed=False)
    RSV_0 = int.to_bytes(0, 4, "little", signed=False)
    RSV_1 = int.to_bytes(1, 4, "little", signed=False)
    unk = b"\xda" * 256
    shared = version + name_enc + name_pad + toc_offset_enc + toc_size_enc + data_offset_enc + data_size_enc + RSV_0 + RSV_1 + RSV_0 + unk

    header = DowIIIArchiveHeader(name, WindowPtr(toc_offset, toc_size), WindowPtr(data_offset, data_size), unk)
    good = "_ARCHIVE".encode("ascii") + shared
    bad = f"garbage_".encode("ascii") + shared
    return header, good, bad


def gen_dow3_archive(archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes, drives: List[VirtualDrive] = None, sparse: bool = False) -> Tuple[Archive, bytes]:
    ARCHIVE_HEADER_SIZE = 428  # v9.0 is huge
    full_toc = toc_ptrs + toc

    toc_and_data = full_toc + data
    header, archive_header_buf, _ = gen_dow3_header_and_buffer(archive_name, ARCHIVE_HEADER_SIZE, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), len(data))
    return DowIIIArchive(header, drives, sparse), archive_header_buf + toc_and_data


def full_gen_dow3_archive(archive_name: str, folder: str, file: str, file_uncomp_data: bytes):
    drives, (toc_ptr, toc) = gen_dow3_archive_toc(archive_name, folder, file, file_uncomp_data)
    return gen_dow3_archive(archive_name, toc_ptr, toc, file_uncomp_data, drives, False)
