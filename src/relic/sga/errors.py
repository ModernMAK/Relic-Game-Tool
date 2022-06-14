from typing import List

from relic.core.errors import MismatchError
from relic.sga._core import Version


class VersionMismatchError(MismatchError):
    def __init__(self, received: Version = None, expected: Version = None):
        super().__init__("Version", received, expected)


class MD5MismatchError(MismatchError):
    def __init__(self, received: bytes = None, expected: bytes = None):
        super().__init__("MD5", received, expected)


class VersionNotSupportedError(Exception):
    def __init__(self, received: Version, allowed: List[Version]):
        self.received = received
        self.allowed = allowed

    def __str__(self):
        def str_ver(v: Version) -> str:  # dont use str(version); too verbose
            return f"{v.major}.{v.minor}"

        allowed_str = [str_ver(_) for _ in self.allowed]
        return f"Version `{str_ver(self.received)}` is not supported. Versions supported: `{allowed_str}`"


#
__all__ = [
    "VersionMismatchError",
    "MD5MismatchError",
    "VersionNotSupportedError"
]
