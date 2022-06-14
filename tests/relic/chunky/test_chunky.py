import json
from abc import abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Union, Iterable, Tuple, List

import pytest

from relic.chunky import v1_1, v3_1, MagicWord, Version
from relic.chunky.protocols import API


class APITests:
    @abstractmethod
    def test_read(self, buffer: Union[bytes, str], api: API):
        if isinstance(buffer, str):
            with open(buffer, "rb") as stream:
                api.read(stream, True)
        else:
            with BytesIO(buffer) as stream:
                api.read(stream, True)


def scan_directory(root_dir: str, desired_version: Version, *exts: str, max_read: int = None) -> Iterable[str]:
    root_directory = Path(root_dir)
    _read = 0
    for ext in exts:
        if max_read is not None and _read >= max_read:
            break
        for path_object in root_directory.glob(f'**/*.{ext}'):
            if max_read is not None and _read >= max_read:
                break
            with path_object.open("rb") as stream:
                if not MagicWord.check_magic_word(stream, advance=True):
                    continue
                version = Version.unpack(stream)
                if version != desired_version:
                    continue
            yield str(path_object)
            _read += 1


def prepare_for_parametrize(files: Iterable[str]) -> Iterable[Tuple[str]]:
    return [(_,) for _ in files]


_path = Path(__file__).parent
# Explicit path locations
try:
    path = _path / "sources.json"
    with path.open() as stream:
        file_sources = json.load(stream)
except IOError as e:
    file_sources = {}


# Implicit path locations
def _update_implicit_file_sources(src_key: str):
    if src_key not in file_sources:
        file_sources[src_key] = {}
    if "dirs" not in file_sources[src_key]:
        file_sources[src_key]["dirs"] = []
    dirs: List[str] = file_sources[src_key]["dirs"]
    dirs.append(str(_path / "test_data" / src_key))


def _helper(src_key: str, version: Version, exts: List[str], max_tests: int = None):
    local_sources = file_sources.get(src_key, {})
    any_sources = file_sources.get("any", {})
    files = set()
    try:
        for sources in [any_sources, local_sources]:
            if max_tests is not None and len(files) >= max_tests:
                break

            for src_dir in sources.get("dirs", []):
                if max_tests is not None and  len(files) >= max_tests:
                    break

                max_read = max_tests-len(files) if max_tests is not  None else None
                for f in scan_directory(src_dir, version, *exts, max_read=max_read):
                    files.add(f)
    except IOError as e:
        pass
    try:
        for sources in [any_sources, local_sources]:
            if max_tests is not None and len(files) >= max_tests:
                break

            for src_file in sources.get("files", []):
                if max_tests is not None and  len(files) > max_tests:
                    break

                files.add(src_file)
    except IOError as e:
        pass
    return prepare_for_parametrize(files)


KNOWN_EXTS = ["fda", "sgm", "whm", "wtp", "rgd", "rml", "rsh", "rtx", "sgb", "tmp", "whe", "model"]
_update_implicit_file_sources("v1_1")
_update_implicit_file_sources("v3_1")
v1_1Files = _helper("v1_1", v1_1.version, KNOWN_EXTS, max_tests=32)
v3_1Files = _helper("v3_1", v3_1.version, KNOWN_EXTS, max_tests=0) # TODO find files that use v3_1 format


class TestV1_1(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v1_1.API

    @pytest.mark.parametrize(["buffer"], [*v1_1Files])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV1_1, self).test_read(buffer, api)


class TestV3_1(APITests):
    @pytest.fixture()
    def api(self) -> API:
        return v3_1.API

    @pytest.mark.parametrize(["buffer"], [*v3_1Files])
    def test_read(self, buffer: Union[bytes, str], api: API):
        super(TestV3_1, self).test_read(buffer, api)
