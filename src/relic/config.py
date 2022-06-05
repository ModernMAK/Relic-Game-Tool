from enum import Enum
from os import PathLike
from os.path import join, exists, abspath
from pathlib import Path, PurePath
from typing import Optional, Iterable, Tuple, Set

import serialization_tools.common_directories

dll_folder = abspath(join(__file__, "..\\..\\..\\Required EXEs"))
aifc_decoder_path = join(dll_folder, "dec.exe")
aifc_encoder_path = join(dll_folder, "enc.exe")
texconv_path = join(dll_folder, "texconv.exe")


def get_path_to_steam_library(steam_directory: PathLike = None) -> Path:
    steam_directory = (PurePath(steam_directory) if steam_directory else steam_directory) or archive_tools.common_directories.get_steam_install_dir()
    return steam_directory / "steamapps" / "common"


class DowIIIGame(Enum):
    BaseGame = 0


class DowIIGame(Enum):
    Retribution = 2
    ChaosRising = 1
    BaseGame = 0


class DowGame(Enum):
    SoulStorm = 4
    DarkCrusade = 3
    WinterAssault = 2
    Gold = 1
    BaseGame = 0


dow_game_paths = {
    DowIIIGame.BaseGame: "Dawn of War III",

    DowIIGame.Retribution: "Dawn of War II - Retribution",

    DowGame.SoulStorm: "Dawn of War Soulstorm",
    DowGame.DarkCrusade: "Dawn of War Dark Crusade",
    DowGame.WinterAssault: "Dawn of War Winter Assault",
    DowGame.Gold: "Dawn of War Gold",
    # DowGame.BaseGame:"Dawn of War", # The original dawn of war probably doesn't include 'Gold', IDK what it is specifically but this would be my first guess
}


def get_dow_root_directories() -> Iterable[Tuple[DowGame, Path]]:
    steam_path = get_path_to_steam_library()
    for game, partial_path in dow_game_paths.items():
        path = steam_path / partial_path
        if exists(path):
            yield game, path


def filter_unique_dow_game(dow_root_directories: Iterable[Tuple[DowGame, Path]]) -> Iterable[Tuple[DowGame, Path]]:
    unique: Set[DowGame] = set()
    for game, path in dow_root_directories:
        if game in unique:
            continue
        yield game, path
        unique.add(game)


# Allows us to get the most
# up-to-date dump of all assets:
#   Gold (I believe) only contains Space Marines, Orks, Chaos, & Eldar
#   Winter Assault Adds Imperial Guard
#   Dark Crusade Adds Tau & Necrons
#   SoulStorm Adds Dark Eldar & Sisters Of Battle
#       If we only want to dump ONE game; we'd want to dump the latest to get all the assets from the previous one
#           Except for campaign  assets; which are unique to each install
#           For Campaign assets, use get_unique and dump each to a separate directory (or order the dumps such that later games come after earlier games)
def filter_latest_dow_game(dow_root_directories: Iterable[Tuple[DowGame, Path]], series: Enum = DowGame) -> Optional[Tuple[DowGame, Path]]:
    latest = latest_path = None
    for game, path in dow_root_directories:
        if not isinstance(game, series):
            continue
        if latest and latest.value > game.value:
            continue
        latest = game
        latest_path = path
    if latest:
        return latest, latest_path
    return None


def get_latest_dow_game() -> Optional[Tuple[DowGame, Path]]:
    return filter_latest_dow_game(get_dow_root_directories(), series=DowGame)


def get_latest_dow2_game() -> Optional[Tuple[DowGame, Path]]:
    return filter_latest_dow_game(get_dow_root_directories(), series=DowIIGame)


def get_latest_dow3_game() -> Optional[Tuple[DowGame, Path]]:
    return filter_latest_dow_game(get_dow_root_directories(), series=DowIIIGame)


def get_unique_dow_game() -> Iterable[Tuple[DowGame, Path]]:
    return filter_unique_dow_game(get_dow_root_directories())


if __name__ == "__main__":
    print("\nAll Dirs")
    for game, path in get_dow_root_directories():
        print(game.name, ":\t", path)

    print("\nLatest")
    dirs = get_dow_root_directories()
    latest = filter_latest_dow_game(dirs)
    print(latest)
