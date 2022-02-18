from archive_tools.structx import Struct

from relic.shared import Magic, MagicWalker

__MAGIC_WORD = "Relic Chunky"
__MAGIC_LAYOUT = Struct("< 12s")

RelicChunkyMagic = Magic(__MAGIC_LAYOUT, __MAGIC_WORD)
RELIC_CHUNKY_MAGIC_WALKER = MagicWalker(RelicChunkyMagic)

