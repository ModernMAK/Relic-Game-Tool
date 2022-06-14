from typing import List, Dict, BinaryIO

from relic.chunky import v1_1, v3_1, protocols
from relic.chunky._core import Version, MagicWord

_APIS: List[protocols.API] = [v1_1.API, v3_1.API]
apis: Dict[Version, protocols.API] = {api.version: api for api in _APIS}


def read(stream: BinaryIO, lazy: bool = False, api_lookup: Dict[Version, protocols.API] = None):
    api_lookup = api_lookup if api_lookup is not None else apis
    start = stream.tell()
    MagicWord.read_magic_word(stream)
    version = Version.unpack(stream)
    api = api_lookup[version]
    stream.seek(start)
    return api.read(stream, lazy)
