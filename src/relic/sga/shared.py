from dataclasses import dataclass
from io import BytesIO
from struct import Struct
from typing import Optional, Iterator, BinaryIO, Dict

from relic.shared import Magic, MagicWalker, Version, VersionEnum
from relic.util.struct_util import unpack_from_stream, pack_into_stream

__MAGIC_LAYOUT = Struct("< 8s")
__MAGIC_WORD = "_ARCHIVE"

ARCHIVE_MAGIC = Magic(__MAGIC_LAYOUT, __MAGIC_WORD)
ARCHIVE_MAGIC_WALKER = MagicWalker(ARCHIVE_MAGIC)


class SgaVersion(VersionEnum):
    Unsupported = None
    Dow = Version(2)
    Dow2 = Version(5)
    Dow3 = Version(9)


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
    __LAYOUT = {SgaVersion.Dow3: __v9_LAYOUT, SgaVersion.Dow2: __v5_LAYOUT, SgaVersion.Dow: __v2_LAYOUT}
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

        if version in cls.__LAYOUT:
            layout = cls.__LAYOUT[version]
            args = unpack_from_stream(layout, stream)
            return OffsetInfo(toc_offset, *args)
        else:
            raise NotImplementedError(version)

    def pack(self, stream: BinaryIO, version: Version) -> int:
        if version in self.__LAYOUT:
            layout = self.__LAYOUT[version]
            args = (self.offset_relative, self.count)
            return pack_into_stream(layout, stream, *args)
        else:
            raise NotImplementedError(version)


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
                s = stream.read(offset + index).decode("ascii")
                if strip_terminal:
                    s = s.rstrip("\x00")
                return s
            except ValueError:
                prev = now
                continue

    def get_name_lookup(self, stream: BinaryIO, use_absolute: bool = True) -> Dict[int, str]:
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
                        offset += start  # Add because offset is relative to the start position
                    name = self.read_string(reader)
                    d[offset] = name
        elif self.count:
            for _ in range(self.count):
                offset = stream.tell()
                if not use_absolute:
                    offset -= start  # Subtract because offset is already abosolute
                name = self.read_string(stream)
                d[offset] = name
        else:
            raise NotImplementedError
        stream.seek(temp)
        return d

    @classmethod
    def unpack(cls, stream: BinaryIO, toc_offset: int, version: Version) -> 'FilenameOffsetInfo':
        basic = OffsetInfo.unpack(stream, toc_offset, version)
        if version == SgaVersion.Dow3:
            return FilenameOffsetInfo(basic.toc_offset, basic.offset_relative, None, basic.count)
        elif version in [SgaVersion.Dow2, SgaVersion.Dow]:
            return FilenameOffsetInfo(basic.toc_offset, basic.offset_relative, basic.count, None)

    def pack(self, stream: BinaryIO, version: Version) -> int:
        if version in self.__LAYOUT:
            layout = self.__LAYOUT[version]
            if version == SgaVersion.Dow3:
                args = self.offset_relative, self.byte_size
            elif version in [SgaVersion.Dow2, SgaVersion.Dow]:
                args = self.offset_relative, self.count
            else:
                raise NotImplementedError(version)

            return pack_into_stream(layout, stream, *args)
        else:
            raise NotImplementedError(version)
