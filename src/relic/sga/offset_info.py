from dataclasses import dataclass
from io import BytesIO
from struct import Struct
from typing import BinaryIO, Optional, Dict

from relic.sga.shared import ARCHIVE_HEADER_OFFSET
from relic.sga.version import Version
from relic.shared import unpack_from_stream, pack_into_stream


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
