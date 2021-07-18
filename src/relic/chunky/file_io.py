from os.path import join
from typing import BinaryIO, List, Tuple, Iterable
from relic.chunky.relic_chunky import RelicChunky


def is_stream_relic_chunky(stream: BinaryIO, advance_stream: bool = False) -> bool:
    return RelicChunky.check_magic_word(stream, advance=advance_stream)


def is_file_relic_chunky(file: str) -> bool:
    with open(file, "rb") as handle:
        # we set advance to true to avoid pointlessly fixing the stream, since we are just going to close it
        return is_stream_relic_chunky(handle, True)


WALK_RESULT = Tuple[str, List[str], List[str]]


# Pass in os.walk(); this will filter the results to only relic chunkies VIA opening and checking for the magic word
# Folders will always be an empty list
def walk_relic_chunky(walk: Iterable[WALK_RESULT]) -> Iterable[WALK_RESULT]:
    for root, _, files in walk:
        chunky_files = [file for file in files if is_file_relic_chunky(join(root, file))]
        yield root, [], chunky_files
