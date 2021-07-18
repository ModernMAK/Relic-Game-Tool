from dataclasses import dataclass


@dataclass
class FlatFile:
    unk_a: int
    name: str
    data: bytes

