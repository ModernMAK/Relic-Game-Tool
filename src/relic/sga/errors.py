from typing import List, Any

from relic.sga._core import Version


def _print_mismatch(name: str, received, expected):
    msg = f"Unexpected {name}"
    if received or expected:
        msg += ";"
    if received:
        msg += f" got `{str(received)}`"
    if received and expected:
        msg += ","
    if expected:
        msg += f" expected `{str(expected)}`"
    return msg + "!"


class MismatchError(Exception):
    def __init__(self, name: str, received: Any = None, expected: Any = None):
        self.name = name
        self.received = received
        self.expected = expected

    def __str__(self):
        return _print_mismatch(self.name, self.received, self.expected)


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
    "_print_mismatch",
    "MismatchError",
    "VersionMismatchError",
    "MD5MismatchError",
    "VersionNotSupportedError"
]
