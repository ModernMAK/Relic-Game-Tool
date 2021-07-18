from struct import Struct

from relic.shared import Magic, MagicWalker

__MAGIC_LAYOUT = Struct("< 8s")
__MAGIC_WORD = "_ARCHIVE"

ARCHIVE_MAGIC = Magic(__MAGIC_LAYOUT, __MAGIC_WORD)
ARCHIVE_MAGIC_WALKER = MagicWalker(ARCHIVE_MAGIC)
