# from abc import abstractmethod
# from io import BytesIO
# from typing import List, Type
#
# import pytest
# from serialization_tools.ioutil import WindowPtr, Ptr
# from serialization_tools.size import KiB, MiB, GiB
#
# from relic.common import Version
# from relic.sga_old import protocols as proto, v2, v5, v9
# from relic.sga_old.checksums import gen_md5_checksum, validate_md5_checksum
# from relic.sga_old.common import ArchiveVersion
# from tests.helpers import TF
# from tests.relic.sga.datagen import DowI, DowII, DowIII
#
#
# class ArchiveHeaderTests:
#     @abstractmethod  # Trick PyCharm into requiring us to redefine this
#     def test_validate_checksums(self, archive: bytes, cls: Type[proto.ArchiveHeader]):
#         for fast in TF:
#             for _assert in TF:
#                 with BytesIO(archive) as stream:
#                     stream.seek(12)  # skip magic/version
#                     archive_header = cls.unpack(stream)
#                     archive_header.validate_checksums(stream, fast=fast, _assert=_assert)
#
#     @abstractmethod  # Trick PyCharm into requiring us to redefine this
#     def test_version(self, archive: proto.ArchiveHeader, expected: Version):
#         assert archive.version == expected
#
#     @abstractmethod
#     def test_unpack(self, buffer: bytes, expected: proto.ArchiveHeader):
#         with BytesIO(buffer) as stream:
#             unpacked = expected.__class__.unpack(stream)
#             assert expected == unpacked
#
#     @abstractmethod
#     def test_pack(self, inst: proto.ArchiveHeader, expected: bytes):
#         with BytesIO() as stream:
#             written = inst.pack(stream)
#             stream.seek(0)
#             packed = stream.read()
#             assert len(packed) == written
#             assert expected == packed
#
#
# _KNOWN_EIGEN = b'06BEF126-4E3C-48D3-8D2E-430BF125B54F'
# _KNOWN_DATA = b'\xf3\x0cGjx:"\xb7O\x89\xc1\x82H\xb2\xa1\xaa\x82-\xe4\\{\xe2\x905\x0c\xdbT\x0c\x82\xa3y\xdat\xd5\xdf\xb7\x04\x1e\xd0\xaa\xf6\xc9|U%\xf7\x0c\xb9\x92\xc9\xbf\xa9\xa3\xaaQ]\xb6\x8c\x10\x87\xc3r\xe3\x89\x16T\x936\xc5l/(\xbd\xbc\x08\xa2\x9b`|\xec\xd5\xf3\xfd\x83\x85\xadHY\xf4U\xb8\x85\x92\xcd\x1d\xc1\xa2\x0f\xbam!\xd5\xacnft>\'\xf0\x12\x9c\x0c\x1c{\xa2\x15VI\xb0\x13\x89\xde\x889\xdc\x15_\xc8\\\x97\x06\xa7\xde\xc0p\xf9o\t\xd3_\x9d\xa7@.\x81\xed\xdd\x13\x9b m9\xf5\x1bV\xc3\xe0\xd4@\x99\xa2\x8aGr\x04\xff\x05\xedIs\x15\t0\x98G\x87O\x9c\xa1\xd2\tcS\xb3\x1eI\xf5\xe3Qp\xe0\xd0m\xbf;\xfb\x856\xa7\\\xb8\xad\x19\xc1\xa3\xaf+\xd4\x08\xd5Y4\x87p|p`dQ\x1c|>is\x17;\xa6\x8d\xa2\xa4\xdc\xe0\xd6\xaf\xc3\x93\xf59\x9a[\x19J\xc88\xb8\xfd/\xe4\xc6J\x8c\xddCY&\x8f'
# _KNOWN_BAD_DATA = b'\xe9F{\x17\xc2\x118\xe4\x0c\xbd\x07\xf2\x07\x03:\xee%\xabx<\xc3\xb5\x98\x7f\xa6[\xc53+Y]t'
# _KNOWN_DATA_MD5 = b'\x0f\xd3\xc3|\xb2d\x16U\xfd\xc2<\x98\x0b\xf1\x91\xde'
#
#
# @pytest.mark.parametrize(
#     ["stream_data", "eigen", "md5_checksum"],
#     [(_KNOWN_DATA, _KNOWN_EIGEN, _KNOWN_DATA_MD5)]
# )
# def test_gen_md5_checksum(stream_data: bytes, eigen: bytes, md5_checksum: bytes, buffer_sizes: List[int] = None, ptr: Ptr = None):
#     buffer_sizes = [KiB, MiB, GiB] if buffer_sizes is None else buffer_sizes
#     ptr = WindowPtr(0, len(stream_data)) if ptr is None else ptr
#     for buffer_size in buffer_sizes:
#         with BytesIO(stream_data) as stream:
#             result = gen_md5_checksum(stream, eigen, buffer_size, ptr)
#         assert md5_checksum == result
#
#
# @pytest.mark.parametrize(
#     ["stream_data", "eigen", "md5_checksum", "fail_expected"],
#     [(_KNOWN_DATA, _KNOWN_EIGEN, _KNOWN_DATA_MD5, False),
#      (_KNOWN_BAD_DATA, _KNOWN_EIGEN, _KNOWN_DATA_MD5, True)]
# )
# def test_validate_md5_checksum(stream_data: bytes, eigen: bytes, md5_checksum: bytes, fail_expected: bool, ptr: WindowPtr = None, buffer_sizes: List[int] = None, ):
#     buffer_sizes = [KiB, MiB, GiB] if buffer_sizes is None else buffer_sizes
#     ptr = WindowPtr(0, len(stream_data)) if ptr is None else ptr
#     for _assert in TF:
#         for buffer_size in buffer_sizes:
#             try:
#                 with BytesIO(stream_data) as stream:
#                     result = validate_md5_checksum(stream, ptr, eigen, md5_checksum, buffer_size, _assert)
#                 # Own lines to make assertions clearer
#             except AssertionError as e:
#                 if not fail_expected:  # MD5 mismatch; if fail_expected we
#                     raise e
#             else:
#                 if fail_expected:
#                     # Invalid and should have asserted
#                     assert not result and not _assert
#                 else:
#                     assert result
#
#
# # Not garunteed to be a valid header
#
# def fast_dow1_archive_header(name, toc_pos, bad_magic: bytes):
#     _AB = 0, 120  # Random values
#     return DowI.gen_archive_header(name, *_AB, toc_pos=toc_pos), DowI.gen_archive_header_buffer(name, *_AB), DowI.gen_archive_header_buffer(name, *_AB, magic=bad_magic)
#
#
# DOW1_HEADER, DOW1_HEADER_DATA, DOW1_HEADER_DATA_BAD_MAGIC = fast_dow1_archive_header("Dawn Of War 1 Test Header", 180, b"deadbeef")
# # By not writing Magic/Archive TOC-Pos must be changed in the generated DowIIArchiveHeader; the buffers (should be) identical given the same input
# DOW1_HEADER_INNER, DOW1_HEADER_INNER_DATA, _ = fast_dow1_archive_header("Dawn Of War 1 Test Header (Inner Pack)", 168, b"deaddead")
# DOW1_ARCHIVE_BUFFER = DowI.gen_sample_archive_buffer("Dawn Of War 1 Test Archive", "Tests", "Dow1 Header Tests.txt", b"You thought this was a test, but it was me, DIO!")
#
# HDR_START = 12  # Most logic now doesn't handle Magic + Version
#
#
# class TestDowIArchiveHeader(ArchiveHeaderTests):
#     @pytest.mark.parametrize(
#         ["archive", "cls"],
#         [(DOW1_ARCHIVE_BUFFER, v2.ArchiveHeader)])
#     def test_validate_checksums(self, archive: bytes, cls: Type[v2.ArchiveHeader]):
#         super().test_validate_checksums(archive, cls)
#
#     @pytest.mark.parametrize(
#         ["expected", "inst"],
#         [(DOW1_HEADER_INNER_DATA[HDR_START:], DOW1_HEADER_INNER)]
#     )
#     def test_pack(self, inst: proto.ArchiveHeader, expected: bytes):
#         super().test_pack(inst, expected)
#
#     @pytest.mark.parametrize(
#         ["buffer", "expected"],
#         [(DOW1_HEADER_INNER_DATA[HDR_START:], DOW1_HEADER_INNER)]
#     )
#     def test_unpack(self, buffer: bytes, expected: proto.ArchiveHeader):
#         super().test_unpack(buffer, expected)
#
#     @pytest.mark.parametrize(["archive", "expected"], [(DOW1_HEADER, v2.version)])
#     def test_version(self, archive: proto.ArchiveHeader, expected: Version):
#         super().test_version(archive, expected)
#
#
# # Not garunteed to be a valid header
#
#
# def fast_dow2_archive_header(name):
#     _ABC = 0, 0, 0
#     return DowII.gen_archive_header(name, *_ABC), DowII.gen_archive_header_buffer(name, *_ABC)
#
#
# DOW2_HEADER, DOW2_HEADER_DATA = fast_dow2_archive_header("Dawn Of War 2 Test Header")
# DOW2_ARCHIVE_BUFFER = DowII.gen_sample_archive_buffer("Dawn Of War 2 Test Archive", "Dow2 Tests", "Imperial Propoganda.txt", b"By the Emperor, we're ready to unleash eleven barrels, m' lord, sir!")
#
#
# class TestDowIIArchiveHeader(ArchiveHeaderTests):
#     @pytest.mark.parametrize(
#         ["buffer", "expected"],
#         [(DOW2_HEADER_DATA[HDR_START:], DOW2_HEADER)],
#     )
#     def test_unpack(self, buffer: bytes, expected: proto.ArchiveHeader):
#         super().test_unpack(buffer, expected)
#
#     @pytest.mark.parametrize(
#         ["inst", "expected"],
#         [(DOW2_HEADER, DOW2_HEADER_DATA[HDR_START:])])
#     def test_pack(self, inst: proto.ArchiveHeader, expected: bytes):
#         super().test_pack(inst, expected)
#
#     @pytest.mark.parametrize(
#         ["archive", "cls"],
#         [(DOW2_ARCHIVE_BUFFER, v5.ArchiveHeader)],
#     )
#     def test_validate_checksums(self, archive: bytes, cls: Type[v5.ArchiveHeader]):
#         super().test_validate_checksums(archive, cls)
#
#     @pytest.mark.parametrize(["archive", "expected"], [(DOW2_HEADER, v5.version)])
#     def test_version(self, archive: proto.ArchiveHeader, expected: Version):
#         super().test_version(archive, expected)
#
#
# def fast_dow3_archive_header(name, bad_magic: bytes):
#     _ABCD = 0, 1, 2, 3
#     return DowIII.gen_archive_header(name, *_ABCD), DowIII.gen_archive_header_buffer(name, *_ABCD), DowIII.gen_archive_header_buffer(name, *_ABCD, magic=bad_magic)
#
#
# DOW3_HEADER, DOW3_HEADER_DATA, DOW3_HEADER_DATA_BAD_MAGIC = fast_dow3_archive_header("Dawn Of War 3 Test Header", b" Marine!")  # Big Brain Pun in ` Marine!`
#
#
# class TestDowIIIArchiveHeader(ArchiveHeaderTests):
#     @pytest.mark.parametrize(
#         ["archive", "cls"],
#         [(None, v9.ArchiveHeader)])
#     def test_validate_checksums(self, archive: bytes, cls: Type[v9.ArchiveHeader]):
#         for fast in TF:
#             for _assert in TF:
#                 # HACK but if it fails it means logic has changed
#                 assert cls.validate_checksums(None, None, fast=fast, _assert=_assert)
#
#     @pytest.mark.parametrize(
#         ["buffer", "expected"],
#         [(DOW3_HEADER_DATA[HDR_START:], DOW3_HEADER)],
#     )
#     def test_unpack(self, buffer: bytes, expected: proto.ArchiveHeader):
#         super().test_unpack(buffer, expected)
#
#     @pytest.mark.parametrize(
#         ["inst", "expected"],
#         [(DOW3_HEADER, DOW3_HEADER_DATA[HDR_START:])])
#     def test_pack(self, inst: proto.ArchiveHeader, expected: bytes):
#         super().test_pack(inst, expected)
#
#     @pytest.mark.parametrize(["archive", "expected"], [(DOW3_HEADER, v9.version)])
#     def test_version(self, archive: proto.ArchiveHeader, expected: Version):
#         super().test_version(archive, expected)
