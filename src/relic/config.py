from collections import Iterable
from os.path import join, exists

aifc_decoder_path = r"../dll/dec.exe"
aifc_encoder_path = r"../dll/enc.exe"

steam_dir = r"D:\Steam"
path_to_steam_library = join(steam_dir, "steamapps", "common")

dow_paths = [
    "Dawn of War Gold",
    "Dawn of War Dark Crusade",
    "Dawn of War Winter Assault",
    "Dawn of War Soulstorm"
]


def get_dow_root_directories() -> Iterable[str]:
    for part in dow_paths:
        path = join(path_to_steam_library, part)
        if exists(path):
            yield path
