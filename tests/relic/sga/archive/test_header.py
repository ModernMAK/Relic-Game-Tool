import hashlib
from abc import abstractmethod
from io import BytesIO
from typing import List, Tuple

import pytest
from serialization_tools.ioutil import WindowPtr, Ptr
from serialization_tools.size import KiB, MiB, GiB

from tests.helpers import TF
from relic.common import Version
from relic.sga import ArchiveHeader, DowIArchiveHeader, ArchiveVersion, DowIIArchiveHeader, DowIIIArchiveHeader, ArchiveMagicWord
from relic.sga.archive import header


class ArchiveHeaderTests:
    @abstractmethod  # Trick PyCharm into requiring us to redefine this
    def test_validate_checksums(self, archive: bytes):
        for fast in TF:
            for _assert in TF:
                with BytesIO(archive) as stream:
                    archive_header = ArchiveHeader.unpack(stream)
                    archive_header.validate_checksums(stream, fast=fast, _assert=_assert)

    @abstractmethod  # Trick PyCharm into requiring us to redefine this
    def test_version(self, archive: ArchiveHeader, expected: Version):
        assert archive.version == expected

    @abstractmethod  # Trick PyCharm into requiring us to redefine this
    def test_private_unpack(self, buffer: bytes, expected: ArchiveHeader):
        with BytesIO(buffer) as stream:
            result = expected.__class__._unpack(stream)
            assert result == expected

    @abstractmethod  # Trick PyCharm into requiring us to redefine this
    def test_private_pack(self, inst: ArchiveHeader, expected: bytes):
        with BytesIO() as stream:
            inst._pack(stream)
            stream.seek(0)
            result = stream.read()
            assert result == expected

    @abstractmethod  # Trick PyCharm into requiring us to redefine this
    def test_unpack(self, buffer: bytes, expected: ArchiveHeader, bad_magic_word: bool):
        for read_magic in TF:
            with BytesIO(buffer) as stream:
                if not read_magic:
                    ArchiveMagicWord.read_magic_word(stream)  # read past magic

                try:
                    unpacked = ArchiveHeader.unpack(stream, read_magic)
                except AssertionError as e:
                    if read_magic and bad_magic_word:
                        return  # Test passed
                    else:
                        raise e
                else:
                    assert expected.__class__ == unpacked.__class__
                    assert expected == unpacked

    @abstractmethod  # Trick PyCharm into requiring us to redefine this
    def test_pack(self, inst: ArchiveHeader, expected: bytes):
        magic_size = ArchiveMagicWord.layout.size
        for write_magic in TF:
            with BytesIO() as stream:
                written = inst.pack(stream, write_magic)
                # assert len(expected) == written - (0 if write_magic else magic_size)
                if not write_magic:
                    true_expected = expected[magic_size:]
                else:
                    true_expected = expected
                stream.seek(0)
                result = stream.read()
                assert true_expected == result


_KNOWN_EIGEN = b'06BEF126-4E3C-48D3-8D2E-430BF125B54F'
_KNOWN_DATA = b'\xf3\x0cGjx:"\xb7O\x89\xc1\x82H\xb2\xa1\xaa\x82-\xe4\\{\xe2\x905\x0c\xdbT\x0c\x82\xa3y\xdat\xd5\xdf\xb7\x04\x1e\xd0\xaa\xf6\xc9|U%\xf7\x0c\xb9\x92\xc9\xbf\xa9\xa3\xaaQ]\xb6\x8c\x10\x87\xc3r\xe3\x89\x16T\x936\xc5l/(\xbd\xbc\x08\xa2\x9b`|\xec\xd5\xf3\xfd\x83\x85\xadHY\xf4U\xb8\x85\x92\xcd\x1d\xc1\xa2\x0f\xbam!\xd5\xacnft>\'\xf0\x12\x9c\x0c\x1c{\xa2\x15VI\xb0\x13\x89\xde\x889\xdc\x15_\xc8\\\x97\x06\xa7\xde\xc0p\xf9o\t\xd3_\x9d\xa7@.\x81\xed\xdd\x13\x9b m9\xf5\x1bV\xc3\xe0\xd4@\x99\xa2\x8aGr\x04\xff\x05\xedIs\x15\t0\x98G\x87O\x9c\xa1\xd2\tcS\xb3\x1eI\xf5\xe3Qp\xe0\xd0m\xbf;\xfb\x856\xa7\\\xb8\xad\x19\xc1\xa3\xaf+\xd4\x08\xd5Y4\x87p|p`dQ\x1c|>is\x17;\xa6\x8d\xa2\xa4\xdc\xe0\xd6\xaf\xc3\x93\xf59\x9a[\x19J\xc88\xb8\xfd/\xe4\xc6J\x8c\xddCY&\x8f'
_KNOWN_BAD_DATA = b'\xe9F{\x17\xc2\x118\xe4\x0c\xbd\x07\xf2\x07\x03:\xee%\xabx<\xc3\xb5\x98\x7f\xa6[\xc53+Y]t'
_KNOWN_DATA_MD5 = b'\x0f\xd3\xc3|\xb2d\x16U\xfd\xc2<\x98\x0b\xf1\x91\xde'


@pytest.mark.parametrize(
    ["stream_data", "eigen", "md5_checksum"],
    [(_KNOWN_DATA, _KNOWN_EIGEN, _KNOWN_DATA_MD5)]
)
def test_gen_md5_checksum(stream_data: bytes, eigen: bytes, md5_checksum: bytes, buffer_sizes: List[int] = None, ptr: Ptr = None):
    buffer_sizes = [KiB, MiB, GiB] if buffer_sizes is None else buffer_sizes
    ptr = WindowPtr(0, len(stream_data)) if ptr is None else ptr
    for buffer_size in buffer_sizes:
        with BytesIO(stream_data) as stream:
            result = header._gen_md5_checksum(stream, eigen, buffer_size, ptr)
        assert md5_checksum == result


@pytest.mark.parametrize(
    ["stream_data", "eigen", "md5_checksum", "fail_expected"],
    [(_KNOWN_DATA, _KNOWN_EIGEN, _KNOWN_DATA_MD5, False),
     (_KNOWN_BAD_DATA, _KNOWN_EIGEN, _KNOWN_DATA_MD5, True)]
)
def test_validate_md5_checksum(stream_data: bytes, eigen: bytes, md5_checksum: bytes, fail_expected: bool, ptr: WindowPtr = None, buffer_sizes: List[int] = None, ):
    buffer_sizes = [KiB, MiB, GiB] if buffer_sizes is None else buffer_sizes
    ptr = WindowPtr(0, len(stream_data)) if ptr is None else ptr
    for _assert in TF:
        for buffer_size in buffer_sizes:
            try:
                with BytesIO(stream_data) as stream:
                    result = header._validate_md5_checksum(stream, ptr, eigen, md5_checksum, buffer_size, _assert)
                # Own lines to make assertions clearer
            except AssertionError as e:
                if not fail_expected:  # MD5 mismatch; if fail_expected we
                    raise e
            else:
                if fail_expected:
                    # Invalid and should have asserted
                    assert not result and not _assert
                else:
                    assert result


def _encode_and_pad(v: str, byte_size: int, encoding: str) -> bytes:
    v_enc = v.encode(encoding)
    v_pad = b"\0" * (byte_size - len(v_enc))
    return v_enc + v_pad


def _gen_dow1_header_and_buffer(name: str, toc_size: int, data_offset: int, toc_pos: int = None, csum1: bytes = None, csum2: bytes = None) -> Tuple[ArchiveHeader, bytes, bytes]:
    version = b"\x02\0\0\0"
    name_enc = _encode_and_pad(name, 128, "utf-16-le")
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


# Not garunteed to be a valid header
def _gen_dow1_archive_toc(vdrive: str, folder: str, file: str, file_uncomp_data: bytes):
    def ushort(v) -> bytes:
        return int.to_bytes(v, length=2, byteorder="little", signed=False)

    def uint(v) -> bytes:
        return int.to_bytes(v, length=4, byteorder="little", signed=False)

    USHORT_ZERO = ushort(0)
    USHORT_ONE = ushort(1)
    UINT_ZERO = uint(0)
    VDRIVE_UNK = b"\xde\xad"
    vdrive_buf = _encode_and_pad("data", 64, "ascii") + _encode_and_pad(vdrive, 64, "ascii") + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE + VDRIVE_UNK
    file_size_enc = uint(len(file_uncomp_data))
    file_buf = uint(len(folder) + 1) + UINT_ZERO + UINT_ZERO + file_size_enc + file_size_enc
    folder_buf = UINT_ZERO + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE
    name_buf = _encode_and_pad(folder, len(folder) + 1, "ascii") + _encode_and_pad(file, len(file) + 1, "ascii")
    toc_buf = vdrive_buf + folder_buf + file_buf + name_buf
    PTR_OFF = 24  # 4 * (2 + 6)
    vdrive_off = 0 + PTR_OFF
    folder_off = vdrive_off + len(vdrive_buf)
    file_off = folder_off + len(folder_buf)
    name_off = file_off + len(folder_buf)
    toc_ptr_buf = uint(vdrive_off) + USHORT_ONE + uint(folder_off) + USHORT_ONE + uint(file_off) + USHORT_ONE + uint(name_off) + USHORT_ONE

    return toc_ptr_buf, toc_buf


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
    _, archive_header_buf, _ = _gen_dow1_header_and_buffer(archive_name, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), csum1=csum1, csum2=csum2)
    return archive_header_buf + toc_and_data


DOW1_HEADER, DOW1_HEADER_DATA, DOW1_HEADER_DATA_BAD_MAGIC = _gen_dow1_header_and_buffer("Dawn Of War 1 Test Header", 0, 120, toc_pos=180)
DOW1_HEADER_INNER, DOW1_HEADER_INNER_DATA, _ = _gen_dow1_header_and_buffer("Dawn Of War 1 Test Header (Inner Pack)", 0, 120,
                                                                           toc_pos=168)  # By not writing Magic/Archive TOC-Pos must be changed in the generated DowIIArchiveHeader; the buffers (should be) identical given the same input
_DOW1_ARCHIVE_DATA = b"You thought this was a test, but it was me, DIO!"
_DOW1_ARCHIVE_TOC_PTR, _DOW1_ARCHIVE_TOC = _gen_dow1_archive_toc("Dawn Of War 1 Test Archive", "Tests", "Dow1 Header Tests.txt", _DOW1_ARCHIVE_DATA)
DOW1_ARCHIVE = _gen_dow1_archive("Dawn Of War 1 Test Archive", _DOW1_ARCHIVE_TOC_PTR, _DOW1_ARCHIVE_TOC, _DOW1_ARCHIVE_DATA)


class TestDowIArchiveHeader(ArchiveHeaderTests):
    @pytest.mark.parametrize(
        ["archive"],
        [(DOW1_ARCHIVE,)])
    def test_validate_checksums(self, archive: bytes):
        super().test_validate_checksums(archive)

    @pytest.mark.parametrize(
        ["expected", "inst"],
        [(DOW1_HEADER_INNER_DATA[12:], DOW1_HEADER_INNER)]
    )
    def test_private_pack(self, inst: ArchiveHeader, expected: bytes):
        super().test_private_pack(inst, expected)

    @pytest.mark.parametrize(
        ["buffer", "expected"],
        [(DOW1_HEADER_INNER_DATA[12:], DOW1_HEADER_INNER)]
    )
    def test_private_unpack(self, buffer: bytes, expected: ArchiveHeader):
        super().test_private_unpack(buffer, expected)

    @pytest.mark.parametrize(
        ["buffer", "expected", "bad_magic_word"],
        [(DOW1_HEADER_DATA, DOW1_HEADER, False),
         (DOW1_HEADER_DATA_BAD_MAGIC, DOW1_HEADER, True)]
    )
    def test_unpack(self, buffer: bytes, expected: ArchiveHeader, bad_magic_word: bool):
        super().test_unpack(buffer, expected, bad_magic_word)

    @pytest.mark.parametrize(
        ["inst", "expected"],
        [(DOW1_HEADER, DOW1_HEADER_DATA)])
    def test_pack(self, inst: ArchiveHeader, expected: bytes):
        super().test_pack(inst, expected)

    @pytest.mark.parametrize(["archive", "expected"], [(DOW1_HEADER, ArchiveVersion.Dow)])
    def test_version(self, archive: ArchiveHeader, expected: Version):
        super().test_version(archive, expected)


def _gen_dow2_header_and_buffer(name: str, toc_size: int, data_offset: int, toc_pos: int, unk: int, csum1: bytes = None, csum2: bytes = None) -> Tuple[ArchiveHeader, bytes, bytes]:
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


# Not garunteed to be a valid header
def _gen_dow2_archive_toc(vdrive: str, folder: str, file: str, file_uncomp_data: bytes):
    def ushort(v) -> bytes:
        return int.to_bytes(v, length=2, byteorder="little", signed=False)

    def uint(v) -> bytes:
        return int.to_bytes(v, length=4, byteorder="little", signed=False)

    USHORT_ZERO = ushort(0)
    USHORT_ONE = ushort(1)
    UINT_ZERO = uint(0)
    VDRIVE_UNK = b"\xde\xad"
    vdrive_buf = _encode_and_pad("data", 64, "ascii") + _encode_and_pad(vdrive, 64, "ascii") + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE + VDRIVE_UNK
    file_size_enc = uint(len(file_uncomp_data))
    file_buf = uint(len(folder) + 1) + UINT_ZERO + UINT_ZERO + file_size_enc + file_size_enc
    folder_buf = UINT_ZERO + USHORT_ZERO + USHORT_ONE + USHORT_ZERO + USHORT_ONE
    name_buf = _encode_and_pad(folder, len(folder) + 1, "ascii") + _encode_and_pad(file, len(file) + 1, "ascii")
    toc_buf = vdrive_buf + folder_buf + file_buf + name_buf
    PTR_OFF = 24  # 4 * (2 + 6)
    vdrive_off = 0 + PTR_OFF
    folder_off = vdrive_off + len(vdrive_buf)
    file_off = folder_off + len(folder_buf)
    name_off = file_off + len(folder_buf)
    toc_ptr_buf = uint(vdrive_off) + USHORT_ONE + uint(folder_off) + USHORT_ONE + uint(file_off) + USHORT_ONE + uint(name_off) + USHORT_ONE

    return toc_ptr_buf, toc_buf


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
    _, archive_header_buf, _ = _gen_dow2_header_and_buffer(archive_name, len(full_toc), ARCHIVE_HEADER_SIZE + len(full_toc), toc_pos=ARCHIVE_HEADER_SIZE, csum1=csum1, csum2=csum2,                                                           unk=0x4d41dfff)  # UNK chosen to mostly match my knowledge of common archive files
    return archive_header_buf + toc_and_data


DOW2_HEADER, DOW2_HEADER_DATA, DOW2_HEADER_DATA_BAD_MAGIC = _gen_dow2_header_and_buffer("Dawn Of War 2 Test Header", 0, 120, 120, 0xff)
_DOW2_ARCHIVE_DATA = b"By the Emperor, we're ready to unleash eleven barrels, m' lord, sir!"
_DOW2_ARCHIVE_TOC_PTR, _DOW2_ARCHIVE_TOC = _gen_dow2_archive_toc("Dawn Of War 2 Test Archive", "Dow2 Tests", "Imperial Propoganda.txt", _DOW2_ARCHIVE_DATA)
DOW2_ARCHIVE = _gen_dow2_archive("Dawn Of War 2 Test Archive", _DOW2_ARCHIVE_TOC_PTR, _DOW2_ARCHIVE_TOC, _DOW2_ARCHIVE_DATA)


class TestDowIIArchiveHeader(ArchiveHeaderTests):
    @pytest.mark.parametrize(
        ["expected", "inst"],
        [(DOW2_HEADER_DATA[12:], DOW2_HEADER)],
    )
    def test_private_pack(self, inst: ArchiveHeader, expected: bytes):
        super().test_private_pack(inst, expected)

    @pytest.mark.parametrize(
        ["buffer", "expected"],
        [(DOW2_HEADER_DATA[12:], DOW2_HEADER)],
    )
    def test_private_unpack(self, buffer: bytes, expected: ArchiveHeader):
        super().test_private_unpack(buffer, expected)

    @pytest.mark.parametrize(
        ["buffer", "expected", "bad_magic_word"],
        [(DOW2_HEADER_DATA, DOW2_HEADER, False),
         (DOW2_HEADER_DATA_BAD_MAGIC, DOW2_HEADER, True)],
    )
    def test_unpack(self, buffer: bytes, expected: ArchiveHeader, bad_magic_word: bool):
        super().test_unpack(buffer, expected, bad_magic_word)

    @pytest.mark.parametrize(
        ["inst", "expected"],
        [(DOW2_HEADER, DOW2_HEADER_DATA)])
    def test_pack(self, inst: ArchiveHeader, expected: bytes):
        super().test_pack(inst, expected)

    @pytest.mark.parametrize(
        ["archive"],
        [(DOW2_ARCHIVE,)],
    )
    def test_validate_checksums(self, archive: bytes):
        super().test_validate_checksums(archive)

    @pytest.mark.parametrize(["archive", "expected"], [(DOW2_HEADER, ArchiveVersion.Dow2)])
    def test_version(self, archive: ArchiveHeader, expected: Version):
        super().test_version(archive, expected)


def _gen_dow3_header_and_buffer(name: str, toc_offset: int, toc_size: int, data_offset: int, data_size: int) -> Tuple[ArchiveHeader, bytes, bytes]:
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


DOW3_HEADER, DOW3_HEADER_DATA, DOW3_HEADER_DATA_BAD_MAGIC = _gen_dow3_header_and_buffer("Dawn Of War 3 Test Header", 180, 1, 181, 1)


class TestDowIIIArchiveHeader(ArchiveHeaderTests):
    @pytest.mark.parametrize(
        ["archive"],
        [(None,)])
    def test_validate_checksums(self, archive: bytes):
        for fast in TF:
            for _assert in TF:
                # HACK but if it fails it means logic has changed
                assert DowIIIArchiveHeader.validate_checksums(None, None, fast=fast, _assert=_assert)

    @pytest.mark.parametrize(
        ["expected", "inst"],
        [(DOW3_HEADER_DATA[12:], DOW3_HEADER)],
    )
    def test_private_pack(self, inst: ArchiveHeader, expected: bytes):
        super().test_private_pack(inst, expected)

    @pytest.mark.parametrize(
        ["buffer", "expected"],
        [(DOW3_HEADER_DATA[12:], DOW3_HEADER)],
    )
    def test_private_unpack(self, buffer: bytes, expected: ArchiveHeader):
        super().test_private_unpack(buffer, expected)

    @pytest.mark.parametrize(
        ["buffer", "expected", "bad_magic_word"],
        [(DOW3_HEADER_DATA, DOW3_HEADER, False),
         (DOW3_HEADER_DATA_BAD_MAGIC, DOW3_HEADER, True)],
    )
    def test_unpack(self, buffer: bytes, expected: ArchiveHeader, bad_magic_word: bool):
        super().test_unpack(buffer, expected, bad_magic_word)

    @pytest.mark.parametrize(
        ["inst", "expected"],
        [(DOW3_HEADER, DOW3_HEADER_DATA)])
    def test_pack(self, inst: ArchiveHeader, expected: bytes):
        super().test_pack(inst, expected)

    @pytest.mark.parametrize(["archive", "expected"], [(DOW3_HEADER, ArchiveVersion.Dow3)])
    def test_version(self, archive: ArchiveHeader, expected: Version):
        super().test_version(archive, expected)
