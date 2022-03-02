from __future__ import annotations

from relic.chunky_formats.dow.whm.whm import WhmChunky

# The only tmp I found in soulstorm is a Whm Chunky, so using an alias instead of repeating it
TmpChunky = WhmChunky
# If I had to guess; TmpChunky can be any chunky type; and a better solution would be to try converting against all known conversions and relying on Errors
#   But that also requires the TmpChunky class to be aware of the converter, which I can't do without passing it in (since the converter is allowed to be an instance)
