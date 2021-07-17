from typing import TextIO, Dict, BinaryIO


def read_ucs_file(input_filename: str) -> Dict[int, str]:
    with open(input_filename, "r", encoding="utf-16") as handle:
        return read_ucs(handle)


def read_ucs(stream: TextIO) -> Dict[int, str]:
    lookup = {}
    for line in stream.readlines():
        num_str, line_str = line.split("\t")
        num = int(num_str)
        line_str = line_str.rstrip("\n")
        lookup[num] = line_str
    return lookup

def print_ucs(ucs:Dict[int, str]):
    for num, text in ucs.items():
        print(f"{num} : {text}")

if __name__ == "__main__":
    ucs = read_ucs_file(r"G:\Clients\Steam\Launcher\steamapps\common\Dawn of War Soulstorm\W40k\Locale\English\W40k.ucs")
    print_ucs(ucs)