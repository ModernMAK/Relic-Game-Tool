from __future__ import annotations

import json
import re
from os import PathLike, walk
from collections import UserDict
from os.path import join, splitext, split
from pathlib import Path
from typing import TextIO, Optional, Iterable, Union, Mapping

# UCS probably stands for UnicodeString
#   I personally think that's a horribly misleading name for this file
from serialization_tools.walkutil import filter_by_file_extension, collapse_walk_on_files, filter_by_path

from relic.config import DowIIIGame, DowGame, DowIIGame, filter_latest_dow_game, get_dow_root_directories


class UcsDict(UserDict):
    def write_stream(self, stream: TextIO, ordered: bool = False) -> int:
        written = 0
        items = self.data.items()
        if ordered:
            items = sorted(items)
        for key, value in items:
            written += stream.write(f"{key}\t{value}\n")
        return written

    def write(self, file: PathLike, ordered: bool = False) -> int:
        with open(file, "w") as handle:
            return self.write_stream(handle, ordered)


class UnicodeStringFile(UcsDict):
    @classmethod
    def read(cls, file: PathLike) -> UnicodeStringFile:
        with open(file, "r", encoding="utf-16") as handle:
            return cls.read_stream(handle)

    @classmethod
    def read_stream(cls, stream: TextIO) -> UnicodeStringFile:
        ucs_file = UnicodeStringFile()

        # prev_num: int = None
        # prev_str: str = None
        for line in stream.readlines():
            safe_line = line.lstrip()
            parts = safe_line.split(maxsplit=1)

            if len(parts) == 0:
                continue
            assert len(parts) <= 2

            num_str = parts[0]
            line_str = parts[1].rstrip("\n") if len(parts) >= 2 else ''
            try:
                num = int(num_str)
            except ValueError:
                raise
                # num = prev_num
                # prev_str = ucs_file[num]
                # if prev_str is not None and line_str is not None:
                #     line_str = ucs_file[num] + line_str
                # else:  # at least one is None, try to use null coalescence to get a non-None
                # line_str = prev_str or line_str

            ucs_file[num] = line_str
            prev_num = num
        return ucs_file


# Alias to make me feel less butt-hurt about UnicodeStringFile's name
LangFile = UnicodeStringFile


# TODO find a better solution
def lang_code_to_name(lang_code: str) -> Optional[str]:
    lang_code = lang_code.lower()
    lookup = {
        "en": "English",
        # I could do what I did for EG and change language for get the Locale folders for each; but I won't.
        #   If somebody ever uses this; add it here
    }
    return lookup.get(lang_code)


def walk_ucs(folder: PathLike, lang_code: str = None) -> Iterable[str]:
    walk_result = walk(folder)
    walk_result = filter_by_file_extension(walk_result, ".ucs")
    walk_result = collapse_walk_on_files(walk_result)
    if lang_code:
        lang_name = lang_code_to_name(lang_code)
        if lang_name:
            walk_result = (file for file in walk_result if filter_by_path(file, whitelist=["Locale"]))  # Only files that have Locale
            walk_result = (file for file in walk_result if filter_by_path(file, whitelist=[lang_name]))  # From there, only files of the given language
    return walk_result


class LangEnvironment(UcsDict):
    def __init__(self, allow_replacement: bool = False, __dict: Mapping[int, str] = None, **kwargs):
        super().__init__(__dict, **kwargs)
        if allow_replacement:
            self.__setitem__ = self.__setitem__noreplace

    def __setitem__noreplace(self, k, v):
        try:
            existing = self.__getitem__(k)
            raise ValueError(f"Key '{k}' exists! Trying to replace '{existing}' with '{v}")
        except KeyError:
            super(UserDict, self).__setitem__(k, v)

    @classmethod
    def load_environment(cls, folder: PathLike, lang_code: str = None, allow_replacement: bool = False) -> LangEnvironment:
        lang_env = LangEnvironment(allow_replacement=allow_replacement)
        lang_env.read_all(folder, lang_code)
        return lang_env

    def read(self, file: PathLike):
        lang_file = LangFile.read(file)
        self.update(lang_file)

    def read_stream(self, stream: TextIO):
        lang_file = LangFile.read_stream(stream)
        self.update(lang_file)

    def read_all(self, folder: PathLike, lang_code: str = None):
        for ucs_path in walk_ucs(folder, lang_code):
            self.read(ucs_path)


__safe_regex = re.compile(r"[^A-Za-z0-9_\- .]")
_default_replacement = ""


def _file_safe_string(word: str, replace: str = None) -> str:
    replace = replace or _default_replacement
    replace = __safe_regex.sub(_default_replacement, replace)  # If replace is illegal, use default
    word = __safe_regex.sub(replace, word)
    return word


def get_lang_string_for_file(environment: Union[LangEnvironment, LangFile], file_path: str) -> str:
    dir_path, f_path = split(file_path)
    file_name, ext = splitext(f_path)
    try:
        # Really arbitrary 'gotcha', some speech files have a random 'b' after the VO Code
        #   This is probably due to a bug in my code, but this will fix the issue
        # TODO find out if this bug is my fault
        if file_name[-1] == "b":
            file_name = file_name[:-1]
        num = int(file_name)
    except (ValueError, IndexError):
        return file_path

    replacement = environment.get(num)
    if not replacement:
        return file_path

    # The clips are long, and while we could say 'narration' or manually do it
    #   By trimming it to at most
    MAX_LEN = 64
    MAX_TRIM = 8
    chars = ".!?"  # ;:," # ORDERED SPECIFICALLY FOR THIS
    for c in chars:
        if len(replacement) > MAX_LEN:
            replacement = replacement.split(c, 1)[0] + c
        else:
            break
    # Some brute forcing
    if len(replacement) > MAX_LEN:
        for i in range(MAX_TRIM):
            if replacement[MAX_LEN - i - 1] == " ":
                replacement = replacement[:MAX_LEN - i] + "..."
    if len(replacement) > MAX_LEN:
        replacement = replacement[:MAX_LEN] + "..."

    replacement = _file_safe_string(replacement)
    return join(dir_path, replacement + f" ~ Clip {num}" + ext)


if __name__ == "__main__":
    # A compromise between an automatic location and NOT the local directory
    #   PyCharm will hang trying to reload the files (just to update the hierarchy, not update references)
    #       To avoid that, we DO NOT use a local directory, but an external directory
    #           TODO add a persistent_data path to archive tools
    Root = Path(r"~\Appdata\Local\ModernMAK\ArchiveTools\Relic-SGA").expanduser()
    dump_type = "UCS_DUMP"
    path_lookup = {
        DowIIIGame: Root / r"DOW_III",
        DowIIGame: Root / r"DOW_II",
        DowGame: Root / r"DOW_I"
    }
    series = DowGame
    out_path = path_lookup[series] / dump_type
    r = filter_latest_dow_game(get_dow_root_directories(), series=series)
    if r:
        game, in_path = r
    else:
        raise FileNotFoundError("Couldn't find any suitable DOW games!")

    print("Loading Locale Environment...")
    lang_env = LangEnvironment.load_environment(in_path)
    print(f"\tReading from '{in_path}'")
    out_path = out_path.with_suffix(".json")
    with open(out_path, "w") as handle:
        lang_env_sorted = dict(sorted(lang_env.items()))
        json.dump(lang_env_sorted, handle, indent=4)
        print(f"\tSaved to '{out_path}'")
