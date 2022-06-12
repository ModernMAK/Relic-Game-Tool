import json
from abc import abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Union, Iterable, Tuple

import pytest

from relic.sga import v2, v5, v9, MagicWord, Version, v7
from relic.sga.protocols import API
from tests.relic.sga.datagen import DowII, DowI, DowIII


class APITests:
    @abstractmethod
    def test_read(self, buffer: Union[bytes, str], api: API):
        if isinstance(buffer, str):
            with open(buffer, "rb") as stream:
                api.read(stream, True)
        else:
            with BytesIO(buffer) as stream:
                api.read(stream, True)


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


def prepare_for_parametrize(files: Iterable[str]) -> Iterable[Tuple[str]]:
    return [(_,) for _ in files]


try:
    path = Path(__file__)
    path = path.parent / "sources.json"
    with path.open() as stream:
        file_sources = json.load(stream)
except IOError as e:
    file_sources = {}


def _helper(src_key: str, version: Version):
    try:
        local_sources = file_sources.get(src_key,{})
        files = set()
        for src_dir in local_sources.get("dirs",[]):
            for f in scan_directory(src_dir, version):
                files.add(f)
        for src_file in local_sources.get("files",[]):
            files.add(src_file)
        return prepare_for_parametrize(files)
    except Exception as e:
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


def fast_gen_dow2_archive(*args):
    return None, DowII.gen_sample_archive_buffer(*args)


DOW2_ARCHIVE, DOW2_ARCHIVE_PACKED = fast_gen_dow2_archive("Dow2 Test Archive", "Tests", "A Favorite Guardsmen VL.txt", b"Where's that artillery!?")


class TestV5(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v5.API

    @pytest.mark.parametrize(["buffer"], [*v5Files, (DOW2_ARCHIVE_PACKED,)])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV5, self).test_read(buffer, api)


def fast_gen_dow3_archive(*args):
    return None, DowIII.gen_sample_archive_buffer(*args)


DOW3_ARCHIVE, DOW3_ARCHIVE_PACKED = fast_gen_dow3_archive("Dow3 Test Archive", "Tests", "Some Witty FileName.txt", b"NGL; I'm running out of dumb/clever test data.")


class TestV9(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v9.API

    @pytest.mark.parametrize(["buffer"], [*v9Files, (DOW3_ARCHIVE_PACKED,)])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV9, self).test_read(buffer, api)


class TestV7(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v7.API

    @pytest.mark.parametrize(["buffer"], [*v7Files])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV7, self).test_read(buffer, api)
