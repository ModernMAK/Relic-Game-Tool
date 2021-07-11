import dataclasses
import json
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