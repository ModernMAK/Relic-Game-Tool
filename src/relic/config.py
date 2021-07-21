from enum import Enum
from os.path import join, exists, abspath
from typing import Optional, Iterable, Tuple, Set

# Todo, move all winreg operations to a specific windows only block
from winreg import HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx

dll_folder = abspath(join(__file__, "..\\..\\dll"))
aifc_decoder_path = join(dll_folder, "dec.exe")
aifc_encoder_path = join(dll_folder, "enc.exe")
texconv_path = join(dll_folder, "texconv.exe")

window_steam_registry_keys = {
    32: (HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    64: (HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
}


def read_install_path_from_registry(bit_mode: int = 32) -> Optional[str]:
    key_mode, key_path = window_steam_registry_keys[bit_mode]
    with OpenKey(HKEY_LOCAL_MACHINE, key_path) as key_handle:
        return QueryValueEx(key_handle, "InstallPath")[0]


# Allows me to manually specify steam_dirs
steam_dirs = [
    # r"D:\Steam"
]


def get_path_to_steam_library(steam_directory: str) -> str:
    return join(steam_directory, "steamapps", "common")


def get_all_steam_dirs() -> Iterable[str]:
    dirs = {d for d in steam_dirs}
    for bit_mode in window_steam_registry_keys.keys():
        try:
            dirs.add(read_install_path_from_registry(bit_mode))
        except OSError:
            continue
    return (get_path_to_steam_library(d) for d in dirs)


# Absolute paths to DOW installations directories (sans "Dawn of War
root_dirs = [

]


class DowGame(Enum):
    Soulstorm = 4
    DarkCrusade = 3
    WinterAssault = 2
    Gold = 1
    BaseGame = 0


dow_game_paths = {
    DowGame.Soulstorm: "Dawn of War Soulstorm",
    DowGame.DarkCrusade: "Dawn of War Dark Crusade",
    DowGame.WinterAssault: "Dawn of War Winter Assault",
    DowGame.Gold: "Dawn of War Gold",
    # DowGame.BaseGame:"Dawn of War", # The original dawn of war probably doesn't include 'Gold', IDK what it is specifically but this would be my first guess
}


def get_dow_root_directories() -> Iterable[Tuple[DowGame, str]]:
    for steam_path in get_all_steam_dirs():
        for game, path in dow_game_paths.items():
            path = join(steam_path, path)
            if exists(path):
                yield game, path


def get_unique_dow_game(dow_root_directories: Iterable[Tuple[DowGame, str]]) -> Iterable[Tuple[DowGame, str]]:
    unique: Set[DowGame] = set()
    for game, path in dow_root_directories:
        if game in unique:
            continue
        yield game, path
        unique.add(game)


# Allows us to get the most up to date dump of all assets:
#   Gold (I believe) only contains Space Marines, Orks, Chaos, & Eldar
#   Winter Assualt Adds Imperial Guard
#   Dark Crudade Adds Tau & Necrons
#   Soulstorm Adds Dark Eldar & Sisters Of Battle
#       If we only want to dump ONE game; we'd want to dump the latest to get all the assets from the previous one
#           With the exception of campaign  assets; which are unique to each install
#           For Campaign assets, use get_unique and dump each to a seperate directory (or order the dumps such that later games come after earlier games)
def get_latest_dow_game(dow_root_directories: Iterable[Tuple[DowGame, str]]) -> Optional[Tuple[DowGame, str]]:
    latest = latest_path = None
    for game, path in dow_root_directories:
        if latest and latest.value > game.value:
            continue
        latest = game
        latest_path = path
    return latest, latest_path


if __name__ == "__main__":
    print("\nAll Dirs")
    for game, path in get_dow_root_directories():
        print(game.name, ":\t", path)

    print("\nLatest")
    dirs = get_dow_root_directories()
    latest = get_latest_dow_game(dirs)
    print(latest)
