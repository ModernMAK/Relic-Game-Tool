from typing import List, Dict

from relic.sga import protocols, v2, v5, v7
from relic.sga.core import Version

_APIS: List[protocols.API] = [v2.API, v5.API, v7.API]
apis: Dict[Version, protocols.API] = {api.version: api for api in _APIS}

__all__ = [
    "v2",
    "v5",
    "v7",
    "v9",
    "protocols",
    "core",
    "apis"
]
