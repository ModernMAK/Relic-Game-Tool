from typing import List, Dict

from relic.sga import v2, v5, v7, v9, protocols
from relic.sga._core import Version

_APIS: List[protocols.API] = [v2.API, v5.API, v7.API, v9.API]
apis: Dict[Version, protocols.API] = {api.version: api for api in _APIS}
