import os
import random
from abc import abstractmethod
from io import BytesIO
from typing import BinaryIO, List, Tuple, Type

import pytest
from serialization_tools.ioutil import WindowPtr, Ptr
from serialization_tools.size import KiB, MiB, GiB

from helpers import TF
from relic.common import Version
from relic.sga import ArchiveHeader, DowIArchiveHeader, ArchiveVersion, DowIIArchiveHeader, DowIIIArchiveHeader, ArchiveMagicWord
from relic.sga.archive import header


class ArchiveHeaderTests:
    def test_validate_checksums(self):
        raise NotImplementedError

    @abstractmethod  # Trick PyCharm into requiring us to redefine this
    def test_version(self, archive: ArchiveHeader, expected: Version):
        assert archive.version == expected

    def test_private_unpack(self):
        raise NotImplementedError

    def test_private_pack(self):
        raise NotImplementedError

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
                assert len(expected) == written - (0 if write_magic else magic_size)
                stream.seek(0)
                if write_magic:
                    assert expected == stream.read()
                else:
                    stream.seek(magic_size)
                    assert expected[magic_size:] == stream.read()


_KNOWN_EIGEN = b'06BEF126-4E3C-48D3-8D2E-430BF125B54F'
_KNOWN_DATA = b'\xf3\x0cGjx:"\xb7O\x89\xc1\x82H\xb2\xa1\xaa\x82-\xe4\\{\xe2\x905\x0c\xdbT\x0c\x82\xa3y\xdat\xd5\xdf\xb7\x04\x1e\xd0\xaa\xf6\xc9|U%\xf7\x0c\xb9\x92\xc9\xbf\xa9\xa3\xaaQ]\xb6\x8c\x10\x87\xc3r\xe3\x89\x16T\x936\xc5l/(\xbd\xbc\x08\xa2\x9b`|\xec\xd5\xf3\xfd\x83\x85\xadHY\xf4U\xb8\x85\x92\xcd\x1d\xc1\xa2\x0f\xbam!\xd5\xacnft>\'\xf0\x12\x9c\x0c\x1c{\xa2\x15VI\xb0\x13\x89\xde\x889\xdc\x15_\xc8\\\x97\x06\xa7\xde\xc0p\xf9o\t\xd3_\x9d\xa7@.\x81\xed\xdd\x13\x9b m9\xf5\x1bV\xc3\xe0\xd4@\x99\xa2\x8aGr\x04\xff\x05\xedIs\x15\t0\x98G\x87O\x9c\xa1\xd2\tcS\xb3\x1eI\xf5\xe3Qp\xe0\xd0m\xbf;\xfb\x856\xa7\\\xb8\xad\x19\xc1\xa3\xaf+\xd4\x08\xd5Y4\x87p|p`dQ\x1c|>is\x17;\xa6\x8d\xa2\xa4\xdc\xe0\xd6\xaf\xc3\x93\xf59\x9a[\x19J\xc88\xb8\xfd/\xe4\xc6J\x8c\xddCY&\x8f'
_KNOWN_BAD_DATA = b'\xe9F{\x17\xc2\x118\xe4\x0c\xbd\x07\xf2\x07\x03:\xee%\xabx<\xc3\xb5\x98\x7f\xa6[\xc53+Y]t'
_KNOWN_DATA_MD5 = b'\x0f\xd3\xc3|\xb2d\x16U\xfd\xc2<\x98\x0b\xf1\x91\xde'.hex()


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
                assert fail_expected  # MD5 mismatch; if fail_expected we don't do
            else:
                if fail_expected:
                    # Invalid and should have asserted
                    assert not result and not _assert
                else:
                    assert result


class TestDowIArchiveHeader(ArchiveHeaderTests):
    def test_validate_checksums(self):
        raise NotImplementedError("Requires sample DowI Archive")

    @pytest.mark.parametrize(["archive", "expected"], [(DowIArchiveHeader(None, None, None, None), ArchiveVersion.Dow)])
    def test_version(self, archive: ArchiveHeader, expected: Version):
        super().test_version(archive, expected)

    def test_private_unpack(self):
        raise NotImplementedError("Requires sample DowI Archive")

    def test_private_pack(self):
        raise NotImplementedError("Requires sample DowI Archive")


def _gen_dow2_header_and_buffer(name: str, toc_size: int, data_offset: int, toc_pos: int, unk: int) -> Tuple[ArchiveHeader, bytes, bytes]:
    version = b"\0\x05\0\0"
    name_enc = name.encode("utf-16-le")
    name_pad = b"\0" * (128 - len(name) * 2)
    csum1 = b"\x01\x02\0\x04\0\0\0\x08\0\0\0\0\0\0\0\0"
    csum2 = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
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


DOW2_HEADER, DOW2_HEADER_DATA, DOW2_HEADER_DATA_BAD_MAGIC = _gen_dow2_header_and_buffer("Dawn Of War 2 Test Header", 0, 120, 120, 0xff)


class TestDowIIArchiveHeader(ArchiveHeaderTests):
    @pytest.mark.parametrize(
        ["buffer", "expected", "bad_magic_word"],
        [(DOW2_HEADER_DATA, DowIIArchiveHeader, False), (DOW2_HEADER_DATA_BAD_MAGIC, DowIIArchiveHeader, True)],
    )
    def test_unpack(self, buffer: bytes, expected: ArchiveHeader, bad_magic_word: bool):
        super().test_unpack(buffer, expected, bad_magic_word)

    @pytest.mark.parametrize(
        ["inst", "expected"],
        [(DOW2_HEADER, DOW2_HEADER_DATA)])
    def test_pack(self, inst: ArchiveHeader, expected: bytes):
        super().test_pack(inst, expected)

    def test_validate_checksums(self):
        pass

    @pytest.mark.parametrize(["archive", "expected"], [(DowIIArchiveHeader(None, None, None, None, None), ArchiveVersion.Dow2)])
    def test_version(self, archive: ArchiveHeader, expected: Version):
        super().test_version(archive, expected)

    def test_private_unpack(self):
        pass

    def test_private_pack(self):
        pass


class TestDowIIIArchiveHeader(ArchiveHeaderTests):
    def test_validate_checksums(self):
        pass

    @pytest.mark.parametrize(["archive", "expected"], [(DowIIIArchiveHeader(None, None, None, None), ArchiveVersion.Dow3)])
    def test_version(self, archive: ArchiveHeader, expected: Version):
        super().test_version(archive, expected)

    def test_private_unpack(self):
        pass

    def test_private_pack(self):
        pass

    def test_unpack(self):
        pass

    def test_pack(self):
        pass