from dataclasses import dataclass
from io import BytesIO
from typing import Optional, Iterator, BinaryIO
from struct import Struct

from relic.shared import Magic, MagicWalker
from relic.util.struct_util import unpack_from_stream

__MAGIC_LAYOUT = Struct("< 8s")
__MAGIC_WORD = "_ARCHIVE"

ARCHIVE_MAGIC = Magic(__MAGIC_LAYOUT, __MAGIC_WORD)
ARCHIVE_MAGIC_WALKER = MagicWalker(ARCHIVE_MAGIC)


@dataclass
class Version:
    major: int
    minor: Optional[int] = 0

    def __str__(self) -> str:
        return f"Version {self.major}.{self.minor}"

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplementedError
        return self.major == other.major and self.minor == other.minor

    @classmethod
    def DowI_Version(cls):
        return cls(2)

    @classmethod
    def DowII_Version(cls):
        return cls(5)

    @classmethod
    def DowIII_Version(cls):
        return cls(9)


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

@dataclass
class OffsetInfo:
    __v2_LAYOUT = Struct("< L H")  # 6 bytes
    __v5_LAYOUT = __v2_LAYOUT
    __v9_LAYOUT = Struct("< L L")  # 8 bytes

    toc_offset: int
    offset_relative: int
    count: int

    @property
    def offset_absolute(self) -> int:
        return self.toc_offset + self.offset_relative

    @offset_absolute.setter
    def offset_absolute(self, abs_offset: int):
        self.offset_relative = abs_offset - self.toc_offset

    @classmethod
    def unpack(cls, stream: BinaryIO, toc_offset: int, version: Version) -> 'OffsetInfo':
        if version == version.DowIII_Version():
            return OffsetInfo(toc_offset, *unpack_from_stream(cls.__v9_LAYOUT, stream))
        elif version in [version.DowII_Version(), version.DowI_Version()]:
            return OffsetInfo(toc_offset, *unpack_from_stream(cls.__v2_LAYOUT, stream))
        else:
            raise NotImplementedError(version)
    # def pack(self, stream: BinaryIO) -> int:
    #     args = (self.offset_relative, self.count)
    #     return pack_into_stream(self.__v9_LAYOUT, stream, *args)


@dataclass
class FilenameOffsetInfo(OffsetInfo):
    count: Optional[int] = None
    byte_size: Optional[int] = None

    @classmethod
    def read_string(cls, stream: BinaryIO, chunk_size: int = 512, strip_terminal: bool = True) -> str:
        start = stream.tell()
        prev = start
        while True:
            b = stream.read(chunk_size)
            now = stream.tell()
            if prev == now:
                raise EOFError()
            try:
                index = b.index(0x00) + 1  # +1 to include \00
                offset = prev - start
                stream.seek(start)
                s = stream.read(offset+index).decode("ascii")
                if strip_terminal:
                    s = s.rstrip("\x00")
                return s
            except ValueError:
                prev = now
                continue

    def get_name_lookup(self, stream: BinaryIO, use_absolute:bool=True) -> Dict[int,str]:
        temp = stream.tell()
        start = self.toc_offset + self.offset_relative
        stream.seek(start)
        d = {}
        if self.byte_size:
            buffer = stream.read(self.byte_size)
            with BytesIO(buffer) as reader:
                while reader.tell() != len(buffer):
                    offset = reader.tell()
                    if use_absolute:
                        offset += start
                    name = self.read_string(reader)
                    d[offset] = name
        elif self.count:
            for _ in range(self.count):
                offset = stream.tell()
                if use_absolute:
                    offset += start
                name = self.read_string(stream)
                d[offset] = name
        else:
            raise NotImplementedError
        stream.seek(temp)
        return d




    @classmethod
    def unpack(cls, stream: BinaryIO, toc_offset: int, version: Version) -> 'FilenameOffsetInfo':
        basic = OffsetInfo.unpack(stream, toc_offset, version)
        if version == Version.DowIII_Version():
            return FilenameOffsetInfo(basic.toc_offset, basic.offset_relative, None, basic.count)
        else:
            return FilenameOffsetInfo(basic.toc_offset, basic.offset_relative, basic.count, None)
