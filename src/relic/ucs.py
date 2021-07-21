import os
import re
from os.path import join, basename, splitext, split
from typing import TextIO, Dict, BinaryIO, Optional, Iterable

from relic.shared import filter_walk_by_extension, filter_walk_by_keyword, WalkResult, collapse_walk_on_files, \
    filter_path_by_keyword


def read_ucs_file(input_filename: str) -> Dict[int, str]:
    with open(input_filename, "r", encoding="utf-16") as handle:
        return read_ucs(handle)


def read_ucs(stream: TextIO) -> Dict[int, str]:
    lookup = {}
    for line in stream.readlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 0:
            continue

        num_str = parts[0]
        line_str = parts[1] if len(parts) >= 2 else "No Localisation"

        num = int(num_str)
        line_str = line_str.rstrip("\n")
        lookup[num] = line_str
    return lookup


# TODO find a better solution
def lang_code_to_name(lang_code: str) -> Optional[str]:
    lang_code = lang_code.lower()
    lookup = {
        "en": "English",
        # I could do what I did for EG and change language for get the Locale folders for each; but I wont.
        #   If somebody ever uses this; add it here
    }
    return lookup.get(lang_code)




def walk_ucs(folder: str, lang_code: str = None) -> Iterable[str]:
    walk = os.walk(folder)
    walk = filter_walk_by_extension(walk, ".ucs")
    walk = collapse_walk_on_files(walk)
    # for r, _, files in walk:
    #     for file in files:
    #         print(r + "\\" + file)
    # raise NotImplementedError()

    if lang_code:
        lang_name = lang_code_to_name(lang_code)
        if lang_name:
            walk = (file for file in walk if filter_path_by_keyword(file, whitelist=["Locale"])) # Only files that have Locale
            walk = (file for file in walk if filter_path_by_keyword(file, whitelist=[lang_name])) # From there, only files of the given language

    return walk


def build_locale_environment(folder: str, lang_code: str = "en") -> Dict[int, str]:
    master = {}
    # for file in collapse_walk_on_files(walk_ucs(folder, lang_code)):
    for path in walk_ucs(folder, lang_code):
        # for file in files:
        # path = join(root, file)
        mapping = read_ucs_file(path)
        master.update(mapping)
    return master


__safe_regex = re.compile(r"[^A-Za-z0-9_\- .]")
_default_replacement = ""

def _file_safe_string(word: str, replace: str = None) -> str:
    replace = replace or _default_replacement
    replace = __safe_regex.sub(_default_replacement, replace)  # If replace is illegal, use default
    word = __safe_regex.sub(replace, word)
    return word


def get_lang_string_for_file(environment: Dict[int, str], file_path: str) -> str:
    dir_path, f_path = split(file_path)
    file_name, ext = splitext(f_path)
    try:
        # Really arbitrary 'gotcha', some speech files have a random 'b' after the VO Code
        #   This is probably due to a bug in my code, but this will fix the issue
        # TODO find out if this bug is my fault
        if file_name[-1] == "b":
            file_name = file_name[:-1]
        num = int(file_name)
    except ValueError:
        return file_path

    replacement = environment.get(num)
    if not replacement:
        return file_path

    # The clips are long, a nd while we could say 'narration' or manually do it
    #   By trimming it to at most
    MAX_LEN = 64
    MAX_TRIM = 8
    chars = ".!?"#;:," # ORDERED SPECIFICALLY FOR THIS
    for c in chars:
        if len(replacement) > MAX_LEN:
            replacement = replacement.split(c, 1)[0] + c
        else:
            break
    # Some brute forcing
    if len(replacement) > MAX_LEN:
        for i in range(MAX_TRIM):
            if replacement[MAX_LEN-i-1] == " ":
                replacement = replacement[:MAX_LEN-i] + "..."
    if len(replacement) > MAX_LEN:
        replacement = replacement[:MAX_LEN] + "..."

    replacement = _file_safe_string(replacement)
    return join(dir_path, replacement + f" ~ Clip {num}" + ext)


def print_ucs(ucs: Dict[int, str]):
    for num, text in ucs.items():
        print(f"{num} : {text}")


if __name__ == "__main__":
    ucs = read_ucs_file(
        r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Soulstorm\W40k\Locale\English\W40k.ucs")
    print_ucs(ucs)
