from abc import abstractmethod
from io import BytesIO

import pytest

from relic.common import VersionLike
from relic.sga import FileHeader, ArchiveVersion
from tests.relic.sga.datagen import DowI


class FileHeaderTests:
    @abstractmethod
    def test_pack(self, header: FileHeader, expected: bytes):
        with BytesIO() as stream:
            written = header.pack(stream)
            assert written == len(expected)
            stream.seek(0)
            assert stream.read() == expected

    @abstractmethod
    def test_inner_pack(self, header: FileHeader, expected: bytes):
        with BytesIO() as stream:
            written = header._pack(stream)
            assert written == len(expected)
            stream.seek(0)
            assert stream.read() == expected

    @abstractmethod
    def test_inner_unpack(self, data_stream: bytes, expected: FileHeader):
        with BytesIO(data_stream) as stream:
            header = expected.__class__._unpack(stream)
            assert header == expected

    @abstractmethod
    def test_unpack(self, data_stream: bytes, expected: FileHeader, version: VersionLike):
        with BytesIO(data_stream) as stream:
            header = FileHeader.unpack(stream, version)
            assert header == expected


DOW1_HEADER, DOW1_HEADER_BUFFER = DowI.gen_file_header(0, 0, 0), DowI.gen_file_header_buffer(0, 0, 0)


class TestDowIFileHeader(FileHeaderTests):
    @pytest.mark.parametrize(["header", "expected"], [(DOW1_HEADER, DOW1_HEADER_BUFFER)])
    def test_pack(self, header: FileHeader, expected: bytes):
        super().test_pack(header, expected)

    @pytest.mark.parametrize(["header", "expected"], [(DOW1_HEADER, DOW1_HEADER_BUFFER)])
    def test_inner_pack(self, header: FileHeader, expected: bytes):
        super().test_pack(header, expected)

    @pytest.mark.parametrize(["expected", "data_stream", "version"], [(DOW1_HEADER, DOW1_HEADER_BUFFER, ArchiveVersion.Dow)])
    def test_unpack(self, data_stream: bytes, expected: FileHeader, version: VersionLike):
        super().test_unpack(data_stream, expected, version)

    @pytest.mark.parametrize(["expected", "data_stream"], [(DOW1_HEADER, DOW1_HEADER_BUFFER)])
    def test_inner_unpack(self, data_stream: bytes, expected: FileHeader):
        super().test_inner_unpack(data_stream, expected)


class TestDowIIFileHeader(FileHeaderTests):
    ...  # TODO


class TestDowIIIFileHeader(FileHeaderTests):
    ...  # TODO
