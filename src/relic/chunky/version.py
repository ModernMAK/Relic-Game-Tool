from enum import Enum

from relic.shared import Version, VersionEnum


class RelicChunkyVersion(VersionEnum):
    Unsupported = None
    v1_1 = Version(1, 1)
    v3_1 = Version(3, 1)
    v4_1 = Version(4, 1)


# Alias
ChunkyVersion = RelicChunkyVersion
