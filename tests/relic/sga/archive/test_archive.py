from abc import abstractmethod
from io import BytesIO

import pytest

from relic.sga.archive import Archive, ArchiveMagicWord
from relic.sga.hierarchy import ArchiveWalk
from tests.helpers import TF
from tests.relic.sga.datagen import DowII, DowI, DowIII


class ArchiveTests:
    def assert_equal(self, expected: Archive, result: Archive, sparse: bool):
        assert expected.header == result.header
        if sparse:
            assert result._sparse
        # TODO

    @abstractmethod
    def test_walk(self, archive: Archive, expected: ArchiveWalk):
        archive_walk = archive.walk()
        for (a_vdrive, a_folder, a_folders, a_files), (e_vdrive, e_folder, e_folders, e_files) in zip(archive_walk, expected):
            assert a_vdrive == e_vdrive
            assert a_folder == e_folder
            assert a_folders == e_folders
            assert a_files == e_files

    @abstractmethod
    def test_inner_unpack(self, stream_data: bytes, expected: Archive):
        for sparse in TF:
            with BytesIO(stream_data) as stream:
                archive = expected.__class__._unpack(stream, expected.header, sparse)
                assert expected.__class__ == archive.__class__
                self.assert_equal(expected, archive, sparse)

    @abstractmethod
    def test_unpack(self, stream_data: bytes, expected: Archive, valid_checksums: bool):
        for read_magic in TF:
            for sparse in TF:
                for validate in ([False] if not valid_checksums else TF):
                    with BytesIO(stream_data) as stream:
                        if not read_magic:
                            stream.seek(ArchiveMagicWord.layout.size)
                        archive = Archive.unpack(stream, read_magic, sparse, validate=validate)
                        assert expected.__class__ == archive.__class__
                        self.assert_equal(expected, archive, sparse)

    @abstractmethod
    def test_pack(self, archive: Archive, expected: bytes):
        for write_magic in TF:
            try:
                with BytesIO() as stream:
                    packed = archive.pack(stream, write_magic)
            except NotImplementedError:
                pass  # Currently not implemented; we'll expect this for now
            else:
                assert expected == packed


def fast_gen_dow1_archive(*args):
    return DowI.gen_sample_archive(*args), DowI.gen_sample_archive_buffer(*args)


DOW1_ARCHIVE, DOW1_ARCHIVE_PACKED = fast_gen_dow1_archive("Dow1 Test Archive", "Tests", "And Now For Something Completely Different.txt", b"Just kidding, it's Monty Python.")


def DOW1_ARCHIVE_WALK() -> ArchiveWalk:
    a = DOW1_ARCHIVE
    d = a.drives[0]
    sfs = d.sub_folders
    yield d, None, sfs, []
    yield d, sfs[0], [], sfs[0].files


class TestDowIArchive(ArchiveTests):
    @pytest.mark.parametrize(["stream_data", "expected"],
                             [(DOW1_ARCHIVE_PACKED, DOW1_ARCHIVE)])
    def test_inner_unpack(self, stream_data: bytes, expected: Archive):
        super().test_inner_unpack(stream_data, expected)

    @pytest.mark.parametrize(["stream_data", "expected", "valid_checksums"],
                             [(DOW1_ARCHIVE_PACKED, DOW1_ARCHIVE, True)])
    def test_unpack(self, stream_data: bytes, expected: Archive, valid_checksums: bool):
        super().test_unpack(stream_data, expected, valid_checksums)

    @pytest.mark.parametrize(["archive", "expected"],
                             [(DOW1_ARCHIVE, DOW1_ARCHIVE_PACKED)])
    def test_pack(self, archive: Archive, expected: bytes):
        super().test_pack(archive, expected)

    @pytest.mark.parametrize(["archive", "expected"],
                             [(DOW1_ARCHIVE, DOW1_ARCHIVE_WALK())])
    def test_walk(self, archive: Archive, expected: ArchiveWalk):
        super().test_walk(archive, expected)


def fast_gen_dow2_archive(*args):
    return DowII.gen_sample_archive(*args), DowII.gen_sample_archive_buffer(*args)


DOW2_ARCHIVE, DOW2_ARCHIVE_PACKED = fast_gen_dow2_archive("Dow2 Test Archive", "Tests", "A Favorite Guardsmen VL.txt", b"Where's that artillery!?")


def DOW2_ARCHIVE_WALK() -> ArchiveWalk:
    a = DOW2_ARCHIVE
    d = a.drives[0]
    sfs = d.sub_folders
    yield d, None, sfs, []
    yield d, sfs[0], [], sfs[0].files


class TestDowIIArchive(ArchiveTests):
    @pytest.mark.parametrize(["stream_data", "expected"],
                             [(DOW2_ARCHIVE_PACKED, DOW2_ARCHIVE)])
    def test_inner_unpack(self, stream_data: bytes, expected: Archive):
        super().test_inner_unpack(stream_data, expected)

    @pytest.mark.parametrize(["stream_data", "expected", "valid_checksums"],
                             [(DOW2_ARCHIVE_PACKED, DOW2_ARCHIVE, True)])
    def test_unpack(self, stream_data: bytes, expected: Archive, valid_checksums: bool):
        super().test_unpack(stream_data, expected, valid_checksums)

    @pytest.mark.parametrize(["archive", "expected"],
                             [(DOW2_ARCHIVE, DOW2_ARCHIVE_PACKED)])
    def test_pack(self, archive: Archive, expected: bytes):
        super().test_pack(archive, expected)

    @pytest.mark.parametrize(["archive", "expected"],
                             [(DOW2_ARCHIVE, DOW2_ARCHIVE_WALK())])
    def test_walk(self, archive: Archive, expected: ArchiveWalk):
        super().test_walk(archive, expected)


def fast_gen_dow3_archive(*args):
    return DowIII.gen_sample_archive(*args), DowIII.gen_sample_archive_buffer(*args)


DOW3_ARCHIVE, DOW3_ARCHIVE_PACKED = fast_gen_dow3_archive("Dow3 Test Archive", "Tests", "Some Witty FileName.txt", b"NGL; I'm running out of dumb/clever test data.")


def DOW3_ARCHIVE_WALK() -> ArchiveWalk:
    a = DOW3_ARCHIVE
    d = a.drives[0]
    sfs = d.sub_folders
    yield d, None, sfs, []
    yield d, sfs[0], [], sfs[0].files


class TestDowIIIArchive(ArchiveTests):
    @pytest.mark.parametrize(["stream_data", "expected"],
                             [(DOW3_ARCHIVE_PACKED, DOW3_ARCHIVE)])
    def test_inner_unpack(self, stream_data: bytes, expected: Archive):
        super().test_inner_unpack(stream_data, expected)

    @pytest.mark.parametrize(["stream_data", "expected", "valid_checksums"],
                             [(DOW3_ARCHIVE_PACKED, DOW3_ARCHIVE, True)])
    def test_unpack(self, stream_data: bytes, expected: Archive, valid_checksums: bool):
        super().test_unpack(stream_data, expected, valid_checksums)

    @pytest.mark.parametrize(["archive", "expected"],
                             [(DOW3_ARCHIVE, DOW3_ARCHIVE_PACKED)])
    def test_pack(self, archive: Archive, expected: bytes):
        super().test_pack(archive, expected)

    @pytest.mark.parametrize(["archive", "expected"],
                             [(DOW3_ARCHIVE, DOW3_ARCHIVE_WALK())])
    def test_walk(self, archive: Archive, expected: ArchiveWalk):
        super().test_walk(archive, expected)
