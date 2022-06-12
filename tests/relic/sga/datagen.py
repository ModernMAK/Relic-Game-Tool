import hashlib
from typing import Tuple, Dict, ClassVar

from relic.sga._core import StorageType


class VirtualDriveABC:
    pass


class ArchiveHeader:
    pass


class v9:
    VirtualDriveHeader = None
    FolderHeader: ClassVar = None
    Archive: ClassVar = None
    FileHeader: ClassVar = None


class v5:
    VirtualDriveHeader = None
    FolderHeader: ClassVar = None
    Archive: ClassVar = None
    FileHeader: ClassVar = None


class v2:
    VirtualDriveHeader = None
    FolderHeader: ClassVar = None
    Archive: ClassVar = None
    FileCompressionFlag: ClassVar = None
    FileHeader: ClassVar = None


class FolderABC:
    pass


class FileABC:
    pass


class ArchiveTOC:
    pass


def encode_and_pad(v: str, byte_size: int, encoding: str) -> bytes:
    v_enc = v.encode(encoding)
    v_pad = b"\0" * (byte_size - len(v_enc))
    return v_enc + v_pad


def ulong(v: int) -> bytes:
    return v.to_bytes(8, "little", signed=False)


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
    DEF_ROOT_FOLDER = ushort(0)  # b"\xde\xad"  # Arbitrary value

    @staticmethod
    def gen_archive_header(name: str, toc_size: int, data_offset: int, csums: Tuple[bytes, bytes] = DEFAULT_CSUMS, toc_pos: int = 180) -> ArchiveHeader:
        raise TypeError("Not currently supported")
        # return v2.ArchiveHeader(name, WindowPtr(toc_pos, toc_size), WindowPtr(data_offset), csums)

    @staticmethod
    def gen_archive_header_buffer(name: str, toc_size: int, data_offset: int, csums: Tuple[bytes, bytes] = DEFAULT_CSUMS, magic: bytes = b"_ARCHIVE") -> bytes:
        version = b"\x02\0\0\0"
        encoded_name = encode_and_pad(name, 64 * 2, "utf-16-le")
        encoded_toc_size = uint(toc_size)
        encoded_data_offset = uint(data_offset)
        return magic + version + csums[0] + encoded_name + csums[1] + encoded_toc_size + encoded_data_offset

    @staticmethod
    def gen_vdrive_header(archive_name: str, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0, path: str = "data", unk: bytes = DEF_ROOT_FOLDER) -> v2.VirtualDriveHeader:
        raise TypeError("Not currently supported")
        # return v2.VirtualDriveHeader(path, archive_name, ArchiveRange(subfolder_offset, subfolder_offset + subfolder_count), ArchiveRange(file_offset, file_offset + file_count), unk)

    @staticmethod
    def gen_vdrive_header_buffer(name: str, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0, path: str = "data", root_folder: bytes = DEF_ROOT_FOLDER):
        return encode_and_pad(path, 64, "ascii") + encode_and_pad(name, 64, "ascii") + ushort(subfolder_offset) + ushort(subfolder_offset + subfolder_count) + ushort(file_offset) + ushort(file_count + file_offset) + root_folder

    @staticmethod
    def gen_folder_header(name_offset: int, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0) -> v2.FolderHeader:
        raise TypeError("Not currently supported")
        # return v2.FolderHeader(name_offset, ArchiveRange(subfolder_offset, subfolder_offset + subfolder_count), ArchiveRange(file_offset, file_offset + file_count))

    @staticmethod
    def gen_folder_header_buffer(name_offset: int, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0) -> bytes:
        return uint(name_offset) + ushort(subfolder_offset) + ushort(subfolder_offset + subfolder_count) + ushort(file_offset) + ushort(file_count + file_offset)

    @staticmethod
    def gen_file_header(name_offset: int, data_offset: int, decomp_size: int, comp_size: int = None, comp_flag: v2.FileCompressionFlag = None) -> v2.FileHeader:
        raise TypeError("Not currently supported")
        # if comp_size is None:
        #     comp_size = decomp_size
        # if comp_flag is None:
        #     if comp_size != decomp_size:
        #         comp_flag = v2.FileCompressionFlag.Compressed16  # IDK, just choose one
        #     else:
        #         comp_flag = v2.FileCompressionFlag.Decompressed
        # return v2.FileHeader(Ptr(name_offset), WindowPtr(data_offset, comp_size), decomp_size, comp_size, comp_flag)

    @staticmethod
    def gen_file_header_buffer(name_offset: int, data_offset: int, decomp_size: int, comp_size: int = None, comp_flag: StorageType = None) -> bytes:
        if comp_size is None:
            comp_size = decomp_size
        if comp_flag is None:
            if comp_size != decomp_size:
                comp_flag = 32  # StorageType.StreamCompress  # IDK, just choose one
            else:
                comp_flag = 0  # StorageType.Store
        return uint(name_offset) + uint(comp_flag) + uint(data_offset) + uint(decomp_size) + uint(comp_size)

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
    def gen_toc(vdrive: VirtualDriveABC, folder: FolderABC, file: FileABC, names: Dict[int, str]) -> ArchiveTOC:
        raise TypeError("Not currently supported")
        # return ArchiveTOC([vdrive], [folder], [file], names)

    @classmethod
    def gen_archive_buffer(cls, archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes, magic: bytes = "_ARCHIVE") -> bytes:
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
        header_buffer = cls.gen_archive_header_buffer(archive_name, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), csums=(csum1, csum2), magic=magic)

        return header_buffer + toc_and_data

    @classmethod
    def gen_sample_archive_buffer(cls, archive_name: str, folder: str, file: str, file_uncomp_data: bytes, magic=b"_ARCHIVE") -> bytes:
        name_buf, name_offsets = cls.gen_name_buffer(folder, file)
        vdrive_buf = cls.gen_vdrive_header_buffer(archive_name, 0, 1, 0, 1)
        folder_buf = cls.gen_folder_header_buffer(name_offsets[folder], 0, 0, 0, 1)
        file_buf = cls.gen_file_header_buffer(name_offsets[file], 0, len(file_uncomp_data))
        toc_buf, toc_offsets = cls.gen_toc_buffer_and_offsets(vdrive_buf, folder_buf, file_buf, name_buf)
        toc_ptrs = splice_toc_offsets(1, 1, 1, 2, toc_offsets)
        toc_ptr_buf = cls.gen_toc_ptr_buffer(*toc_ptrs)
        return cls.gen_archive_buffer(archive_name, toc_ptr_buf, toc_buf, file_uncomp_data, magic)

    @classmethod
    def gen_sample_archive(cls, archive_name: str, folder: str, file: str, file_uncomp_data: bytes, toc_pos: int = 180) -> v2.Archive:
        raise TypeError("Currently not supported")
        # def dirty_toc_hack():
        #     name_buf, name_offsets = cls.gen_name_buffer(folder, file)
        #     vdrive_buf = cls.gen_vdrive_header_buffer(archive_name, 0, 1, 0, 1)
        #     folder_buf = cls.gen_folder_header_buffer(name_offsets[folder], 0, 0, 0, 1)
        #     file_buf = cls.gen_file_header_buffer(name_offsets[file], 0, len(file_uncomp_data))
        #     toc_buf, toc_offsets = cls.gen_toc_buffer_and_offsets(vdrive_buf, folder_buf, file_buf, name_buf)
        #     toc_ptrs = splice_toc_offsets(1, 1, 1, 2, toc_offsets)
        #     return cls.gen_toc_ptr_buffer(*toc_ptrs) + toc_buf
        #
        # toc_buf = dirty_toc_hack()
        #
        # def dirty_csum_hack():
        #     EIGENS = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))
        #
        #     def gen_csum(buffer: bytes, eigen: bytes) -> bytes:
        #         hasher = hashlib.md5(eigen)
        #         hasher.update(buffer)
        #         return bytes.fromhex(hasher.hexdigest())
        #
        #     csum2 = gen_csum(toc_buf, EIGENS[1])
        #     toc_and_data = toc_buf + file_uncomp_data
        #     csum1 = gen_csum(toc_and_data, EIGENS[0])
        #     return csum1, csum2
        #
        # csums = dirty_csum_hack()
        #
        # _, name_offsets = cls.gen_name_buffer(folder, file)
        # vdrive_h = cls.gen_vdrive_header(archive_name, 0, 1, 0, 1)
        # folder_h = cls.gen_folder_header(name_offsets[folder], 0, 0, 0, 1)
        # file_h = cls.gen_file_header(name_offsets[file], 0, len(file_uncomp_data))
        # file_ = v2.File(file_h, file, file_uncomp_data, True)
        # folder_ = v2.Folder(folder_h, folder, [], [file_])
        # vdrive_ = v2.VirtualDrive(vdrive_h, [folder_], [file_])
        # folder_.parent_drive = file_.parent_drive = vdrive_
        # file_.parent_folder = folder_
        # header = cls.gen_archive_header(archive_name, len(toc_buf), len(toc_buf) + toc_pos, csums, toc_pos)
        # return v2.Archive(header, [vdrive_], False)


class DowII:
    DEFAULT_CSUMS = (b"\x01\x02\0\x04\0\0\0\x08\0\0\0\0\0\0\0\0", b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f")
    DEF_ROOT_FOLDER = ushort(0)  # b"\xde\xad"  # Arbitrary value
    ARCHIVE_HEADER_UNK = bytes.fromhex("4d41dFFF")  # F in place of unknowns
    ARCHIVE_HEADER_UNK_INT = int.from_bytes(ARCHIVE_HEADER_UNK, byteorder="little", signed=False)  # F in place of unknowns
    ARCHIVE_HEADER_SIZE = 196

    @classmethod
    def gen_archive_header(cls, name: str, toc_size: int, data_offset: int, toc_offset: int, csums: Tuple[bytes, bytes] = DEFAULT_CSUMS) -> ArchiveHeader:
        raise TypeError("Not currently supported")
        # return v5.ArchiveHeader(name, WindowPtr(toc_offset, toc_size), WindowPtr(data_offset), csums, cls.ARCHIVE_HEADER_UNK_INT)

    @classmethod
    def gen_archive_header_buffer(cls, name: str, toc_size: int, data_offset: int, toc_offset: int, csums: Tuple[bytes, bytes] = DEFAULT_CSUMS, magic: bytes = b"_ARCHIVE") -> bytes:
        version = b"\x05\0\0\0"
        encoded_name = encode_and_pad(name, 64 * 2, "utf-16-le")
        encoded_toc_size = uint(toc_size)
        encoded_toc_offset = uint(toc_offset)
        encoded_data_offset = uint(data_offset)
        return magic + version + csums[0] + encoded_name + csums[1] + encoded_toc_size + encoded_data_offset + encoded_toc_offset + uint(1) + uint(0) + cls.ARCHIVE_HEADER_UNK

    @staticmethod
    def gen_vdrive_header(archive_name: str, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0, path: str = "data", root_folder: bytes = DEF_ROOT_FOLDER) -> v5.VirtualDriveHeader:
        raise TypeError("Not currently supported")
        # return v5.VirtualDriveHeader(path, archive_name, ArchiveRange(subfolder_offset, subfolder_offset + subfolder_count), ArchiveRange(file_offset, file_offset + file_count), unk)

    gen_vdrive_header_buffer = DowI.gen_vdrive_header_buffer  # Same exact layout;

    @staticmethod
    def gen_folder_header(name_offset: int, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0) -> v5.FolderHeader:
        raise TypeError("Not currently supported")
        # return v5.FolderHeader(name_offset, ArchiveRange(subfolder_offset, subfolder_offset + subfolder_count), ArchiveRange(file_offset, file_offset + file_count))

    gen_folder_header_buffer = DowI.gen_folder_header_buffer  # Same exact layout;

    @staticmethod
    def gen_file_header(name_offset: int, data_offset: int, decomp_size: int, comp_size: int = None) -> v5.FileHeader:
        raise TypeError("Not currently supported")
        # comp_size = decomp_size if comp_size is None else comp_size
        # return v5.FileHeader(Ptr(name_offset), Ptr(data_offset, comp_size), decomp_size, comp_size, 0, 0)

    @staticmethod
    def gen_file_header_buffer(name_offset: int, data_offset: int, decomp_size: int, comp_size: int = None) -> bytes:
        comp_size = decomp_size if comp_size is None else comp_size
        return uint(name_offset) + uint(data_offset) + uint(comp_size) + uint(decomp_size) + uint(0) + ushort(0)

    gen_name_buffer = DowI.gen_name_buffer
    gen_toc_buffer_and_offsets = DowI.gen_toc_buffer_and_offsets
    gen_toc_ptr_buffer = DowI.gen_toc_ptr_buffer
    gen_toc = DowI.gen_toc

    @classmethod
    def gen_archive_buffer(cls, archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes, magic: bytes = "_ARCHIVE") -> bytes:
        full_toc = toc_ptrs + toc
        EIGENS = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))

        def gen_csum(buffer: bytes, eigen: bytes) -> bytes:
            hasher = hashlib.md5(eigen)
            hasher.update(buffer)
            return bytes.fromhex(hasher.hexdigest())

        csum2 = gen_csum(full_toc, EIGENS[1])
        toc_and_data = full_toc + data
        csum1 = gen_csum(toc_and_data, EIGENS[0])
        header_buffer = cls.gen_archive_header_buffer(archive_name, len(full_toc), cls.ARCHIVE_HEADER_SIZE + len(full_toc), cls.ARCHIVE_HEADER_SIZE, csums=(csum1, csum2), magic=magic)

        return header_buffer + toc_and_data

    @classmethod
    def gen_sample_archive_buffer(cls, archive_name: str, folder: str, file: str, file_uncomp_data: bytes, magic=b"_ARCHIVE") -> bytes:
        name_buf, name_offsets = cls.gen_name_buffer(folder, file)
        vdrive_buf = cls.gen_vdrive_header_buffer(archive_name, 0, 1, 0, 1)
        folder_buf = cls.gen_folder_header_buffer(name_offsets[folder], 0, 0, 0, 1)
        file_buf = cls.gen_file_header_buffer(name_offsets[file], 0, len(file_uncomp_data))
        toc_buf, toc_offsets = cls.gen_toc_buffer_and_offsets(vdrive_buf, folder_buf, file_buf, name_buf)
        toc_ptrs = splice_toc_offsets(1, 1, 1, 2, toc_offsets)
        toc_ptr_buf = cls.gen_toc_ptr_buffer(*toc_ptrs)
        return cls.gen_archive_buffer(archive_name, toc_ptr_buf, toc_buf, file_uncomp_data, magic)

    @classmethod
    def gen_sample_archive(cls, archive_name: str, folder: str, file: str, file_uncomp_data: bytes, toc_pos: int = 180) -> v5.Archive:
        raise TypeError("Not currently supported")
        # def dirty_toc_hack():
        #     name_buf, name_offsets = cls.gen_name_buffer(folder, file)
        #     vdrive_buf = cls.gen_vdrive_header_buffer(archive_name, 0, 1, 0, 1)
        #     folder_buf = cls.gen_folder_header_buffer(name_offsets[folder], 0, 0, 0, 1)
        #     file_buf = cls.gen_file_header_buffer(name_offsets[file], 0, len(file_uncomp_data))
        #     toc_buf, toc_offsets = cls.gen_toc_buffer_and_offsets(vdrive_buf, folder_buf, file_buf, name_buf)
        #     toc_ptrs = splice_toc_offsets(1, 1, 1, 2, toc_offsets)
        #     return cls.gen_toc_ptr_buffer(*toc_ptrs) + toc_buf
        #
        # full_toc = dirty_toc_hack()
        #
        # def dirty_csum_hack():
        #     EIGENS = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))
        #
        #     def gen_csum(buffer: bytes, eigen: bytes) -> bytes:
        #         hasher = hashlib.md5(eigen)
        #         hasher.update(buffer)
        #         return bytes.fromhex(hasher.hexdigest())
        #
        #     csum2 = gen_csum(full_toc, EIGENS[1])
        #     toc_and_data = full_toc + file_uncomp_data
        #     csum1 = gen_csum(toc_and_data, EIGENS[0])
        #     return csum1, csum2
        #
        # csums = dirty_csum_hack()
        #
        # _, name_offsets = cls.gen_name_buffer(folder, file)
        # vdrive_h = cls.gen_vdrive_header(archive_name, 0, 1, 0, 1)
        # folder_h = cls.gen_folder_header(name_offsets[folder], 0, 0, 0, 1)
        # file_h = cls.gen_file_header(name_offsets[file], 0, len(file_uncomp_data))
        # file_ = FileABC(file_h, file, file_uncomp_data, True)
        # folder_ = FolderABC(folder_h, folder, [], [file_])
        # vdrive_ = VirtualDriveABC(vdrive_h, [folder_], [file_])
        # folder_.parent_drive = file_.parent_drive = vdrive_
        # file_.parent_folder = folder_
        # header = cls.gen_archive_header(archive_name, len(full_toc), cls.ARCHIVE_HEADER_SIZE + len(full_toc), cls.ARCHIVE_HEADER_SIZE, csums)
        # return v5.Archive(header, [vdrive_], False)


class DowIII:
    DEF_ROOT_FOLDER = ushort(0)  # bytes.fromhex("dead")  # Arbitrary value
    ARCHIVE_HEADER_SIZE = 428
    ARCHIVE_HEADER_UNK = b"dead " * 51 + b"\0"  # 256 bytes spamming `dead ` in ascii; with one byte '\0' to pad to 256

    @classmethod
    def gen_archive_header(cls, name: str, toc_offset: int, toc_size: int, data_offset: int, data_size: int) -> ArchiveHeader:
        raise TypeError("Not currently supported")
        # return v9.ArchiveHeader(name, WindowPtr(toc_offset, toc_size), WindowPtr(data_offset, data_size), cls.ARCHIVE_HEADER_UNK)

    @classmethod
    def gen_archive_header_buffer(cls, name: str, toc_offset: int, toc_size: int, data_offset: int, data_size: int, magic: bytes = b"_ARCHIVE") -> bytes:
        version = b"\x09\0\0\0"
        encoded_name = encode_and_pad(name, 64 * 2, "utf-16-le")
        encoded_toc_offset = ulong(toc_offset)
        encoded_toc_size = uint(toc_size)
        encoded_data_offset = ulong(data_offset)
        encoded_data_size = uint(data_size)
        return magic + version + encoded_name + encoded_toc_offset + encoded_toc_size + encoded_data_offset + encoded_data_size + uint(0) + uint(1) + cls.ARCHIVE_HEADER_UNK

    @staticmethod
    def gen_vdrive_header(archive_name: str, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0, path: str = "data", unk: bytes = DEF_ROOT_FOLDER) -> v9.VirtualDriveHeader:
        raise TypeError("Not currently supported")
        # return v9.VirtualDriveHeader(path, archive_name, ArchiveRange(subfolder_offset, subfolder_offset + subfolder_count), ArchiveRange(file_offset, file_offset + file_count), unk)

    @staticmethod
    def gen_vdrive_header_buffer(name: str, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0, path: str = "data", unk: bytes = DEF_ROOT_FOLDER):
        return encode_and_pad(path, 64, "ascii") + encode_and_pad(name, 64, "ascii") + uint(subfolder_offset) + uint(subfolder_offset + subfolder_count) + uint(file_offset) + uint(file_count + file_offset) + unk

    @staticmethod
    def gen_folder_header(name_offset: int, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0) -> v9.FolderHeader:
        raise TypeError("Not currently supported")
        # return v9.FolderHeader(name_offset, ArchiveRange(subfolder_offset, subfolder_offset + subfolder_count), ArchiveRange(file_offset, file_offset + file_count))

    @staticmethod
    def gen_folder_header_buffer(name_offset: int, subfolder_offset: int = 0, subfolder_count: int = 0, file_offset: int = 0, file_count: int = 0) -> bytes:
        return uint(name_offset) + uint(subfolder_offset) + uint(subfolder_offset + subfolder_count) + uint(file_offset) + uint(file_count + file_offset)

    @staticmethod
    def gen_file_header(name_offset: int, data_offset: int, decomp_size: int, comp_size: int = None) -> v9.FileHeader:
        if comp_size is None:
            comp_size = decomp_size
        raise TypeError("Not currently supported")
        # return v9.FileHeader(Ptr(name_offset), Ptr(data_offset), decomp_size, comp_size, 0, 0, 0, 0, 0)

    @staticmethod
    def gen_file_header_buffer(name_offset: int, data_offset: int, decomp_size: int, comp_size: int = None) -> bytes:
        if comp_size is None:
            comp_size = decomp_size
        return uint(name_offset) + uint(0) + uint(data_offset) + uint(0) + uint(comp_size) + uint(decomp_size) + uint(0) + ushort(0) + uint(0)

    @staticmethod
    def gen_name_buffer(*names: str, encoding: str = "ascii") -> Tuple[bytes, Dict[str, int]]:
        packed = [name.encode(encoding) + b"\0" for name in names]
        offset = 0
        lookup = {}
        for i, name in enumerate(names):
            lookup[name] = offset
            offset += len(packed[i])
        return b"".join(packed), lookup

    gen_toc_buffer_and_offsets = DowI.gen_toc_buffer_and_offsets  # Still the same; should be moved out of DowI probably

    @staticmethod
    def gen_toc_ptr_buffer(vdrive: Tuple[int, int], folders: Tuple[int, int], files: Tuple[int, int], names: Tuple[int, int], ptr_off: int = 32):
        pairs = [vdrive, folders, files, names]
        parts = [uint(ptr + ptr_off) + uint(count) for (ptr, count) in pairs]
        return b"".join(parts)

    @staticmethod
    def gen_toc(vdrive: VirtualDriveABC, folder: FolderABC, file: FileABC, names: Dict[int, str]) -> ArchiveTOC:
        raise TypeError("Not currently supported")
        # return ArchiveTOC([vdrive], [folder], [file], names)

    @classmethod
    def gen_archive_buffer(cls, archive_name: str, toc_ptrs: bytes, toc: bytes, data: bytes, magic: bytes = "_ARCHIVE") -> bytes:
        full_toc = toc_ptrs + toc
        toc_and_data = full_toc + data
        header_buffer = cls.gen_archive_header_buffer(archive_name, cls.ARCHIVE_HEADER_SIZE, len(full_toc), cls.ARCHIVE_HEADER_SIZE + len(full_toc), len(data), magic=magic)
        return header_buffer + toc_and_data

    @classmethod
    def gen_sample_archive_buffer(cls, archive_name: str, folder: str, file: str, file_uncomp_data: bytes, magic=b"_ARCHIVE") -> bytes:
        name_buf, name_offsets = cls.gen_name_buffer(folder, file)
        vdrive_buf = cls.gen_vdrive_header_buffer(archive_name, 0, 1, 0, 1)
        folder_buf = cls.gen_folder_header_buffer(name_offsets[folder], 0, 0, 0, 1)
        file_buf = cls.gen_file_header_buffer(name_offsets[file], 0, len(file_uncomp_data))
        toc_buf, toc_offsets = cls.gen_toc_buffer_and_offsets(vdrive_buf, folder_buf, file_buf, name_buf)
        toc_ptrs = splice_toc_offsets(1, 1, 1, len(name_buf), toc_offsets)  # WE NEED TO USE BYTE-SIZE of NAME BUFFER!!!!
        toc_ptr_buf = cls.gen_toc_ptr_buffer(*toc_ptrs)
        return cls.gen_archive_buffer(archive_name, toc_ptr_buf, toc_buf, file_uncomp_data, magic)

    @classmethod
    def gen_sample_archive(cls, archive_name: str, folder: str, file: str, file_uncomp_data: bytes) -> v9.Archive:
        raise TypeError("Not currently supported")
        # name_buf, name_offsets = cls.gen_name_buffer(folder, file)
        # vdrive_h = cls.gen_vdrive_header(archive_name, 0, 1, 0, 1)
        # folder_h = cls.gen_folder_header(name_offsets[folder], 0, 0, 0, 1)
        # file_h = cls.gen_file_header(name_offsets[file], 0, len(file_uncomp_data))
        # file_ = FileABC(file_h, file, file_uncomp_data, True)
        # folder_ = FolderABC(folder_h, folder, [], [file_])
        # vdrive_ = VirtualDriveABC(vdrive_h, [folder_], [file_])
        # folder_.parent_drive = file_.parent_drive = vdrive_
        # file_.parent_folder = folder_
        #
        # vdrive_buf = cls.gen_vdrive_header_buffer(archive_name, 0, 1, 0, 1)
        # folder_buf = cls.gen_folder_header_buffer(name_offsets[folder], 0, 0, 0, 1)
        # file_buf = cls.gen_file_header_buffer(name_offsets[file], 0, len(file_uncomp_data))
        # toc_buf, toc_offsets = cls.gen_toc_buffer_and_offsets(vdrive_buf, folder_buf, file_buf, name_buf)
        # toc_ptrs = splice_toc_offsets(1, 1, 1, len(name_buf), toc_offsets)  # WE NEED TO USE BYTE-SIZE of NAME BUFFER!!!!
        # toc_ptr_buf = cls.gen_toc_ptr_buffer(*toc_ptrs)
        # full_toc = toc_ptr_buf + toc_buf
        #
        # header = cls.gen_archive_header(archive_name,  cls.ARCHIVE_HEADER_SIZE, len(full_toc), cls.ARCHIVE_HEADER_SIZE + len(full_toc), len(file_uncomp_data))
        # return v9.Archive(header, [vdrive_], False)
