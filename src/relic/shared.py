import dataclasses
import json
import os
from os.path import splitext, dirname, basename
from typing import Tuple, List, Union, BinaryIO


def get_stream_size(stream: BinaryIO) -> int:
    origin = stream.tell()
    stream.seek(0, 2)
    terminal = stream.tell()
    stream.seek(origin, 0)
    return terminal


def walk_ext(folder: str, ext: Union[str, List[str]]) -> Tuple[str, str]:
    if isinstance(ext, str):
        ext = [ext]

    ext = [x.lower() for x in ext]
    ext = [f".{x}" if x[0] != '.' else x for x in ext]

    if os.path.isfile(folder):
        root, file = dirname(folder), basename(folder)
        _, x = splitext(file)
        if x.lower() not in ext:
            return
        yield root, file

    for root, _, files in os.walk(folder):
        for file in files:
            _, x = splitext(file)
            if x.lower() not in ext:
                continue
            yield root, file


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, bytes):
            # return "... Bytes Not Dumped To Avoid Flooding Console ..."
            l = len(o)
            if len(o) > 16:
                o = o[0:16]
                return o.hex(sep=" ") + f" ... [+{l - 16} Bytes]"
            return o.hex(sep=" ")
        return super().default(o)
