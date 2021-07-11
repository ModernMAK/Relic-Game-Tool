import os
from os.path import splitext
from typing import Tuple, List, Union


def walk_ext(folder: str, ext: Union[str, List[str]]) -> Tuple[str, str]:
    if isinstance(ext, str):
        ext = [ext]
    ext = [x.lower() for x in ext]

    for root, _, files in os.walk(folder):
        for file in files:
            _, x = splitext(file)
            if x.lower() not in ext:
                continue
            yield root, file
