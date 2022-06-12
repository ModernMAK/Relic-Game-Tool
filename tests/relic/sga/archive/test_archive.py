import json
from abc import abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Union, Iterable, Tuple

import pytest
import serialization_tools.magic

from relic.sga import v2, v5, v9, MagicWord, Version, v7
from relic.sga.protocols import API
from tests.relic.sga.datagen import DowII, DowI, DowIII


# def _ARCHIVE_WALK_SAMPLE(a: Archive) -> ArchiveWalk:
#     d = a.drives[0]
#     sfs = d.folders
#     dfs = d.files
#     yield d, None, sfs, dfs
#     yield d, sfs[0], [], sfs[0].files


class APITests:
    @abstractmethod
    def test_read(self, buffer: Union[bytes, str], api: API):
        if isinstance(buffer, str):
            with open(buffer, "rb") as stream:
                api.read(stream, True)
        else:
            with BytesIO(buffer) as stream:
                api.read(stream, True)
    # def assert_equal(self, expected: Archive, result: Archive, sparse: bool):
    #     assert expected.meta == result.meta
    #     if sparse:
    #         assert result._sparse
    #     # TODO

    # @abstractmethod
    # def test_walk(self, archive: Archive, expected: ArchiveWalk):
    #     archive_walk = archive.walk()
    #     for (a_vdrive, a_folder, a_folders, a_files), (e_vdrive, e_folder, e_folders, e_files) in zip(archive_walk, expected):
    #         assert a_vdrive == e_vdrive
    #         assert a_folder == e_folder
    #         assert a_folders == e_folders
    #         assert a_files == e_files

    # @abstractmethod
    # def test_unpack(self, stream_data: bytes, expected: Archive):
    #     for sparse in TF:
    #         with BytesIO(stream_data) as stream:
    #             archive = expected.__class__.unpack(stream, expected.header, sparse)
    #             assert expected.__class__ == archive.__class__
    #             self.assert_equal(expected, archive, sparse)
    #
    # @abstractmethod
    # def test_pack(self, archive: Archive, expected: bytes):
    #     for write_magic in TF:
    #         try:
    #             with BytesIO() as stream:
    #                 packed = archive.pack(stream, write_magic)
    #         except NotImplementedError:
    #             pass  # Currently not implemented; we'll expect this for now
    #         else:
    #             assert expected == packed


def scan_directory(root_dir: str, desired_version: Version) -> Iterable[str]:
    root_directory = Path(root_dir)
    for path_object in root_directory.glob('**/*.sga'):
        with path_object.open("rb") as stream:
            if not MagicWord.check_magic_word(stream, advance=True):
                continue
            version = Version.unpack(stream)
            if version != desired_version:
                continue
        yield str(path_object)


def fast_gen_dow1_archive(*args):
    return None, DowI.gen_sample_archive_buffer(*args)
    # return DowI.gen_sample_archive(*args),\
    #        DowI.gen_sample_archive_buffer(*args)


def buffer_paramefy(files: Iterable[str]) -> Iterable[Tuple[str]]:
    return [(_,) for _ in files]


try:
    path = Path(__file__)
    path = path.parent / "file_sources.json"
    with path.open() as stream:
        file_sources = json.load(stream)
except IOError as e:
    file_sources = {}


def _helper(src_key: str, version: Version):
    try:
        return buffer_paramefy(scan_directory(file_sources[src_key], version))
    except:
        return tuple()


v2Files = _helper("v2", v2.version)
v5Files = _helper("v5", v5.version)
v7Files = _helper("v7", v7.version)
v9Files = _helper("v9", v9.version)

DOW1_ARCHIVE, DOW1_ARCHIVE_PACKED = fast_gen_dow1_archive("Dow1 Test Archive", "Tests", "And Now For Something Completely Different.txt", b"Just kidding, it's Monty Python.")


class TestV2(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v2.API

    @pytest.mark.parametrize(["buffer"], [(DOW1_ARCHIVE_PACKED,), *v2Files])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV2, self).test_read(buffer, api)
    # @pytest.mark.parametrize(["stream_data", "expected"],
    #                          [(DOW1_ARCHIVE_PACKED, DOW1_ARCHIVE)])
    # def test_unpack(self, stream_data: bytes, expected: Archive):
    #     super().test_unpack(stream_data, expected)
    #
    # @pytest.mark.parametrize(["archive", "expected"],
    #                          [(DOW1_ARCHIVE, DOW1_ARCHIVE_PACKED)])
    # def test_pack(self, archive: Archive, expected: bytes):
    #     super().test_pack(archive, expected)
    #
    # @pytest.mark.parametrize(["archive", "expected"],
    #                          [(DOW1_ARCHIVE, _ARCHIVE_WALK_SAMPLE(DOW1_ARCHIVE))])
    # def test_walk(self, archive: Archive, expected: ArchiveWalk):
    #     super().test_walk(archive, expected)


def fast_gen_dow2_archive(*args):
    return None, DowII.gen_sample_archive_buffer(*args)
    # return DowII.gen_sample_archive(*args),\
    #        DowII.gen_sample_archive_buffer(*args)


DOW2_ARCHIVE, DOW2_ARCHIVE_PACKED = fast_gen_dow2_archive("Dow2 Test Archive", "Tests", "A Favorite Guardsmen VL.txt", b"Where's that artillery!?")


class TestV5(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v5.API

    @pytest.mark.parametrize(["buffer"], [*v5Files, (DOW2_ARCHIVE_PACKED,)])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV5, self).test_read(buffer, api)
    # @pytest.mark.parametrize(["stream_data", "expected"],
    #                          [(DOW2_ARCHIVE_PACKED, DOW2_ARCHIVE)])
    # def test_unpack(self, stream_data: bytes, expected: Archive):
    #     super().test_unpack(stream_data, expected)
    #
    # @pytest.mark.parametrize(["archive", "expected"],
    #                          [(DOW2_ARCHIVE, DOW2_ARCHIVE_PACKED)])
    # def test_pack(self, archive: Archive, expected: bytes):
    #     super().test_pack(archive, expected)
    #
    # @pytest.mark.parametrize(["archive", "expected"],
    #                          [(DOW2_ARCHIVE, _ARCHIVE_WALK_SAMPLE(DOW2_ARCHIVE))])
    # def test_walk(self, archive: Archive, expected: ArchiveWalk):
    #     super().test_walk(archive, expected)


def fast_gen_dow3_archive(*args):
    return None, DowIII.gen_sample_archive_buffer(*args)
    # return DowIII.gen_sample_archive(*args), \
    #        DowIII.gen_sample_archive_buffer(*args)


DOW3_ARCHIVE, DOW3_ARCHIVE_PACKED = fast_gen_dow3_archive("Dow3 Test Archive", "Tests", "Some Witty FileName.txt", b"NGL; I'm running out of dumb/clever test data.")


class TestV9(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v9.API

    @pytest.mark.parametrize(["buffer"], [*v9Files, (DOW3_ARCHIVE_PACKED,)])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV9, self).test_read(buffer, api)
    # @pytest.mark.parametrize(["stream_data", "expected"],
    #                          [(DOW3_ARCHIVE_PACKED, DOW3_ARCHIVE)])
    # def test_unpack(self, stream_data: bytes, expected: Archive):
    #     super().test_unpack(stream_data, expected)
    #
    # @pytest.mark.parametrize(["archive", "expected"],
    #                          [(DOW3_ARCHIVE, DOW3_ARCHIVE_PACKED)])
    # def test_pack(self, archive: Archive, expected: bytes):
    #     super().test_pack(archive, expected)
    #
    # @pytest.mark.parametrize(["archive", "expected"],
    #                          [(DOW3_ARCHIVE, _ARCHIVE_WALK_SAMPLE(DOW3_ARCHIVE))])
    # def test_walk(self, archive: Archive, expected: ArchiveWalk):
    #     super().test_walk(archive, expected)


class TestV7(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v7.API

    @pytest.mark.parametrize(["buffer"], [*v7Files])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV7, self).test_read(buffer, api)
