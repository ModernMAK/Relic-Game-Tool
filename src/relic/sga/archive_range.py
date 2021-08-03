from dataclasses import dataclass
from typing import Iterable, Optional, Iterator


@dataclass
class ArchiveRange:
    start: int
    end: int
    __iterable: Optional[Iterator] = None

    @property
    def size(self) -> int:
        return self.end - self.start

    # We don't use iterable to avoid x
    def __iter__(self) -> 'ArchiveRange':
        self.__iterable = iter(range(self.start, self.end))
        return self

    def __next__(self) -> int:
        return next(self.__iterable)
