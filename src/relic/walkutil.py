import json
from dataclasses import is_dataclass, asdict
from enum import Enum


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        elif isinstance(o, Enum):
            return {'name': o.name, 'value': o.value}
        elif isinstance(o, bytes):
            # return "... Bytes Not Dumped To Avoid Flooding Console ..."
            l = len(o)
            if len(o) > 16:
                o = o[0:16]
                return o.hex(sep=" ") + f" ... [+{l - 16} Bytes]"
            return o.hex(sep=" ")
        else:
            return super().default(o)
