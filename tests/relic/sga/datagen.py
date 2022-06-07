import hashlib
from typing import Tuple, List, Dict

from serialization_tools.ioutil import WindowPtr, Ptr

from relic.sga import ArchiveHeader, DowIArchiveHeader, DowIIArchiveHeader, DowIIIArchiveHeader, Archive, VirtualDrive, VirtualDriveHeader, Folder, FolderHeader, File, FileHeader, DowIIArchive, DowIArchive, DowIIIArchive, \
    DowIIIFolderHeader, DowIIIFileHeader, DowIIIVirtualDriveHeader, DowIVirtualDriveHeader, DowIFolderHeader, DowIFileHeader, FileCompressionFlag, DowIIFolderHeader, DowIIVirtualDriveHeader, DowIIFileHeader
from relic.sga.common import ArchiveRange
from relic.sga.toc.toc import ArchiveTOC


def encode_and_pad(v: str, byte_size: int, encoding: str) -> bytes:
    v_enc = v.encode(encoding)
    v_pad = b"\0" * (byte_size - len(v_enc))
    return v_enc + v_pad


def uint(v: int) -> bytes:
    return v.to_bytes(4, "little", signed=False)


def ushort(v: int) -> bytes:
    return v.to_bytes(2, "little", signed=False)


def splice_toc_offsets(vdrive: int, folders: int, files: int, names: int, offsets: Tuple[int, int, int, int]):
    """Merges the counts provided for each param to their respective offset; creating a tuple of (offset, count)"""
    counts = [vdrive, folders, files, names]
    return tuple(zip(offsets, counts))


class DowI:
    DEFAULT_CSUMS = (b"\x01\x02\0\x04\0\0\0\x08\0\0\0\0\0\0\0\0", b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f")
    VDRIVE_UNK = bytes.fromhex("dead")  # Arbitrary value

    @staticmethod
    def gen_archive_header(name: str, toc_size: int, data_offset: int, csums: Tuple[bytes, bytes] = DEFAULT_CSUMS, toc_pos: int = 180) -> ArchiveHeader:
        return DowIArchiveHeader(name, WindowPtr(toc_pos, toc_size), WindowPtr(data_offset), csums)

    @staticmethod
    def gen_archive_header_buffer(name: str, toc_size: int, data_offset: int, csums: Tuple[bytes, bytes] = DEFAULT_CSUMS, magic: bytes = b"_ARCHIVE") -> bytes:
        version = b"\x02\0\0\0"
        encoded_name = encode_and_pad(name, 64 * 2, "utf-16-le")
        encoded_toc_size = uint(toc_size)
        encoded_data_offset = uint(data_offset)
        return magic + version + csums[0] + encoded_name + csums[1] + encoded_toc_size + encoded_data_offset

    @staticmethod
    def gen_vdrive_header(archive_name: str, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0, path: str = "data", unk: bytes = VDRIVE_UNK) -> DowIVirtualDriveHeader:
        return DowIVirtualDriveHeader(path, archive_name, ArchiveRange(subfolder_offset, subfolder_offset + subfolder_count), ArchiveRange(file_offset, file_offset + file_count), unk)

    @staticmethod
    def gen_vdrive_header_buffer(name: str, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0, path: str = "data", unk: bytes = VDRIVE_UNK):
        return encode_and_pad(path, 64, "ascii") + encode_and_pad(name, 64, "ascii") + ushort(subfolder_offset) + ushort(subfolder_offset + subfolder_count) + ushort(file_offset) + ushort(file_count + file_offset) + unk

    @staticmethod
    def gen_folder_header(name_offset: int, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0) -> DowIFolderHeader:
        return DowIFolderHeader(name_offset, ArchiveRange(subfolder_offset, subfolder_offset + subfolder_count), ArchiveRange(file_offset, file_offset + file_count))

    @staticmethod
    def gen_folder_header_buffer(name_offset: int, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0) -> bytes:
        return uint(name_offset) + ushort(subfolder_offset) + ushort(subfolder_offset + subfolder_count) + ushort(file_offset) + ushort(file_count + file_offset)

    @staticmethod
    def gen_file_header(name_offset: int, data_offset: int, decomp_size: int, comp_size: int = None, comp_flag: FileCompressionFlag = None) -> DowIFileHeader:
        if comp_size is None:
            comp_size = decomp_size
        if comp_flag is None:
            if comp_size != decomp_size:
                comp_flag = FileCompressionFlag.Compressed16  # IDK, just choose one
            else:
                comp_flag = FileCompressionFlag.Decompressed
        return DowIFileHeader(Ptr(name_offset), Ptr(data_offset), decomp_size, comp_size, comp_flag)

    @staticmethod
    def gen_file_header_buffer(name_offset: int, data_offset: int, decomp_size: int, comp_size: int = None, comp_flag: FileCompressionFlag = None) -> bytes:
        if comp_size is None:
            comp_size = decomp_size
        if comp_flag is None:
            if comp_size != decomp_size:
                comp_flag = FileCompressionFlag.Compressed16  # IDK, just choose one
            else:
                comp_flag = FileCompressionFlag.Decompressed
        return uint(name_offset) + uint(comp_flag.value) + uint(data_offset) + uint(decomp_size) + uint(comp_size)

    @staticmethod
    def gen_name_buffer(*names: str, encoding: str = "ascii") -> Tuple[bytes, Dict[str, int]]:
        packed = [name.encode(encoding) + b"\0" for name in names]
        offset = 0
        lookup = {}
        for i, name in enumerate(names):
            lookup[name] = offset
            offset += len(packed[i])
        return b"".join(packed), lookup

    @staticmethod
    def gen_toc_buffer_and_offsets(vdrive: bytes, folder: bytes, file: bytes, names: bytes) -> Tuple[bytes, Tuple[int, int, int, int]]:
        vdrive_off = 0
        folder_off = vdrive_off + len(vdrive)
        file_off = folder_off + len(folder)
        name_off = file_off + len(file)

        return vdrive + folder + file + names, (vdrive_off, folder_off, file_off, name_off)

    @staticmethod
    def gen_toc_ptr_buffer(vdrive: Tuple[int, int], folders: Tuple[int, int], files: Tuple[int, int], names: Tuple[int, int], ptr_off: int = 24):
        pairs = [vdrive, folders, files, names]
        parts = [uint(ptr + ptr_off) + ushort(count) for (ptr, count) in pairs]
        return b"".join(parts)

    @staticmethod
    def gen_toc(vdrive: VirtualDrive, folder: Folder, file: File, names: Dict[int, str]) -> ArchiveTOC:
        return ArchiveTOC([vdrive], [folder], [file], names)

    @classmethod
    def gen_archive_buffer(self, archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes, magic: bytes = "_ARCHIVE") -> bytes:
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
        header_buffer = self.gen_archive_header_buffer(archive_name, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), csums=(csum1, csum2), magic=magic)

        return header_buffer + toc_and_data

    @classmethod
    def gen_sample_archive_buffer(self, archive_name: str, folder: str, file: str, file_uncomp_data: bytes, magic=b"_ARCHIVE") -> bytes:
        name_buf, name_offsets = self.gen_name_buffer(folder, file)
        vdrive_buf = self.gen_vdrive_header_buffer(archive_name, 0, 1, 0, 1)
        folder_buf = self.gen_folder_header_buffer(name_offsets[folder], 0, 0, 0, 1)
        file_buf = self.gen_file_header_buffer(name_offsets[file], 0, len(file_uncomp_data))
        toc_buf, toc_offsets = self.gen_toc_buffer_and_offsets(vdrive_buf, folder_buf, file_buf, name_buf)
        toc_ptrs = splice_toc_offsets(1, 1, 1, 2, toc_offsets)
        toc_ptr_buf = self.gen_toc_ptr_buffer(*toc_ptrs)
        return self.gen_archive_buffer(archive_name, toc_ptr_buf, toc_buf, file_uncomp_data, magic)

    @classmethod
    def gen_sample_archive(self, archive_name: str, folder: str, file: str, file_uncomp_data: bytes, toc_pos: int = 180) -> DowIArchive:
        def dirty_toc_hack():
            name_buf, name_offsets = self.gen_name_buffer(folder, file)
            vdrive_buf = self.gen_vdrive_header_buffer(archive_name, 0, 1, 0, 1)
            folder_buf = self.gen_folder_header_buffer(name_offsets[folder], 0, 0, 0, 1)
            file_buf = self.gen_file_header_buffer(name_offsets[file], 0, len(file_uncomp_data))
            toc_buf, toc_offsets = self.gen_toc_buffer_and_offsets(vdrive_buf, folder_buf, file_buf, name_buf)
            toc_ptrs = splice_toc_offsets(1, 1, 1, 2, toc_offsets)
            return self.gen_toc_ptr_buffer(*toc_ptrs) + toc_buf

        toc_buf = dirty_toc_hack()

        def dirty_csum_hack():
            EIGENS = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))

            def gen_csum(buffer: bytes, eigen: bytes) -> bytes:
                hasher = hashlib.md5(eigen)
                hasher.update(buffer)
                return bytes.fromhex(hasher.hexdigest())

            csum2 = gen_csum(toc_buf, EIGENS[1])
            toc_and_data = toc_buf + file_uncomp_data
            csum1 = gen_csum(toc_and_data, EIGENS[0])
            return csum1, csum2

        csums = dirty_csum_hack()

        _, name_offsets = self.gen_name_buffer(folder, file)
        vdrive_h = self.gen_vdrive_header(archive_name, 0, 1, 0, 1)
        folder_h = self.gen_folder_header(name_offsets[folder], 0, 0, 0, 1)
        file_h = self.gen_file_header(name_offsets[file], 0, len(file_uncomp_data))
        file_ = File(file_h, file, file_uncomp_data, True)
        folder_ = Folder(folder_h, folder, [], [file_])
        vdrive_ = VirtualDrive(vdrive_h, [folder_], [file_])
        folder_._drive = file_._drive = vdrive_
        file_._parent = folder_
        header = self.gen_archive_header(archive_name, len(toc_buf), len(toc_buf) + toc_pos, csums, toc_pos)
        return DowIArchive(header, [vdrive_], False)


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
