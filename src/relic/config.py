from collections import Iterable
from os.path import join, exists, abspath
from typing import Optional
from winreg import HKEY_LOCAL_MACHINE, OpenKey, CloseKey, QueryValue

dll_folder = abspath(join(__file__, "..\\dll"))
aifc_decoder_path = join(dll_folder, "dec.exe")
aifc_encoder_path = join(dll_folder, "enc.exe")
texconv_path = join(dll_folder, "texconv.exe")

window_steam_registry_keys = {
    32: (HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    64: (HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Valve\Steam"),
}


def read_install_path_from_registry(bit_mode: int = 32) -> Optional[str]:
    key_mode, key_path = window_steam_registry_keys.get(bit_mode)
    try:
        key_handle = OpenKey(key_mode, key_path)
        return QueryValue(key_handle, "InstallPath")
    finally:
        CloseKey(key_handle)


# Allows me to manually specify steam_dirs
steam_dirs = [
    r"D:\Steam"
]


def get_path_to_steam_library(steam_directory: str) -> str:
    return join(steam_directory, "steamapps", "common")


def get_all_steam_dirs() -> Iterable[str]:
    dirs = {d for d in steam_dirs}
    for bit_mode in window_steam_registry_keys.keys():
        try:
            path = read_install_path_from_registry(bit_mode)
            dirs.add(path)
        except OSError:
            continue
    dirs = (get_path_to_steam_library(d) for d in dirs)
    return dirs


# Absolute paths to DOW installations
root_dirs = [

]

dow_paths = [
    "Dawn of War Gold",
    "Dawn of War Dark Crusade",
    "Dawn of War Winter Assault",
    "Dawn of War Soulstorm"
]


def get_dow_root_directories() -> Iterable[str]:
    for steam_path in get_all_steam_dirs():
        for part in dow_paths:
            path = join(steam_path, part)
            if exists(path):
                yield path
