from typing import Union

from relic.chunky._core import ChunkType, Version
from relic.core.errors import MismatchError


class ChunkError(Exception):
    pass


class ChunkTypeError(ChunkError):
    def __init__(self, chunk_type: Union[bytes, str] = None, *args):
        super().__init__(*args)
        self.chunk_type = chunk_type

    def __str__(self):
        msg = f"ChunkType must be {repr(ChunkType.Folder.value)} or {repr(ChunkType.Data.value)}"
        if not self.chunk_type:
            return msg + "!"
        else:
            return msg + f"; got {repr(self.chunk_type)}!"


class ChunkNameError(ChunkError):
    def __init__(self, name: Union[bytes, str] = None, *args):
        super().__init__(*args)
        self.name = name

    def __str__(self):
        msg = f"Chunk name was not parsable ascii text"
        if not self.name:
            return msg + "!"
        else:
            return msg + f"; got {repr(self.name)}!"


class VersionMismatchError(MismatchError):
    def __init__(self, received: Version = None, expected: Version = None):
        super().__init__("Version", received, expected)
