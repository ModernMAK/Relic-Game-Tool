# RGD's are 'attribute' information
# Basically game data for all the units? Or for research/upgrades
# My first file: 'addon_dark_eldar_list_post_2.rgd' seems to be the info for the DE's Listening Post 2nd Tier Upgrade

import zlib
from os.path import splitext

if __name__ == "__main__":
    f = r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Dark Crusade\My_Mod\Data\Attrib\addon_dark_eldar_list_post_2.rgd"
    d, _ = splitext(f)
    with open(f, "rb") as infile:
        with open(d + ".bin", "wb") as outfile:
            outfile.write(zlib.decompress(infile.read()))
