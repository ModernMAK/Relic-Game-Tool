from struct import Struct

from relic.shared import Magic, MagicWalker

__MAGIC_WORD = "Relic Chunky"
__MAGIC_LAYOUT = Struct("< 12s")

RELIC_CHUNKY_MAGIC = Magic(__MAGIC_LAYOUT, __MAGIC_WORD)
RELIC_CHUNKY_MAGIC_WALKER = MagicWalker(RELIC_CHUNKY_MAGIC)

