from typing import Any


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
