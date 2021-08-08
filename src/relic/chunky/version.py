from enum import Enum

from relic.shared import Version


class RelicChunkyVersion(Enum):
    Unsupported = None
    v1_1 = Version(1, 1)
    v3_1 = Version(3, 1)

    def __eq__(self, other):
        # Special Case; allow comparison to Version implicitly
        if isinstance(other, Version):
            return self.value == other
        else:
            return super.__eq__(self, other)

    def __ne__(self, other):
        return not (self == other)


# Alias
ChunkyVersion = RelicChunkyVersion
