from dataclasses import dataclass, is_dataclass, asdict
import json
import os
from os.path import splitext, dirname, basename, join
from struct import Struct
from typing import Tuple, List, Union, BinaryIO, Iterable, Any


def unpack_from_stream(layout: Struct, stream: BinaryIO) -> Tuple[Any, ...]:
    buffer = stream.read(layout.size)
    return layout.unpack_from(buffer)


def pack_into_stream(layout: Struct, stream: BinaryIO, *args) -> int:
    buffer = layout.pack(*args)
    return stream.write(buffer)


class MagicUtil:
    @classmethod
    def read_magic_word(cls, stream: BinaryIO, layout: Struct, advance: bool = True) -> str:
        magic = unpack_from_stream(layout, stream)[0].decode("ascii")
        if not advance:  # Useful for checking the header before reading it
            stream.seek(-layout.size, 1)
        return magic

    @classmethod
    def assert_magic_word(cls, stream: BinaryIO, layout: Struct, word: str, advance: bool = True):
        magic = cls.read_magic_word(stream, layout=layout, advance=advance)
        assert magic == word, (magic, word)

    @classmethod
    def check_magic_word(cls, stream: BinaryIO, layout: Struct, word: str, advance: bool = True) -> bool:
        magic = cls.read_magic_word(stream, layout=layout, advance=advance)
        return magic == word


@dataclass
class Magic:
    layout: Struct
    word: str

    def read_magic_word(self, stream: BinaryIO, advance: bool = True) -> str:
        return MagicUtil.read_magic_word(stream, self.layout, advance)

    def assert_magic_word(self, stream: BinaryIO, advance: bool = True):
        MagicUtil.assert_magic_word(stream, self.layout, self.word, advance)

    def check_magic_word(self, stream: BinaryIO, advance: bool = False) -> bool:
        return MagicUtil.check_magic_word(stream, self.layout, self.word, advance)


WALK_RESULT = Tuple[str, List[str], List[str]]


@dataclass
class MagicWalker:
    magic: Magic

    def check_stream(self, stream: BinaryIO, advance_stream: bool = False) -> bool:
        return self.magic.check_magic_word(stream, advance=advance_stream)

    def check_file(self, file: str) -> bool:
        with open(file, "rb") as handle:
            # we set advance to true to avoid pointlessly fixing the stream, since we are just going to close it
            return self.check_stream(handle, True)

    # Pass in os.walk(); this will filter the results to only relic chunkies VIA opening and checking for the magic word
    # Folders will always be an empty list
    def walk(self, walk: Iterable[WALK_RESULT]) -> Iterable[WALK_RESULT]:
        for root, _, files in walk:
            chunky_files = [file for file in files if self.check_file(join(root, file))]
            yield root, [], chunky_files


def get_stream_size(stream: BinaryIO) -> int:
    origin = stream.tell()
    stream.seek(0, 2)
    terminal = stream.tell()
    stream.seek(origin, 0)
    return terminal


def fix_exts(ext: Union[str, List[str]]) -> List[str]:
    if isinstance(ext, str):
        ext = [ext]

    ext = [x.lower() for x in ext]
    ext = [f".{x}" if x[0] != '.' else x for x in ext]
    return ext


def walk_ext(folder: str, ext: Union[str, List[str]]) -> Tuple[str, str]:
    ext = fix_exts(ext)
    if os.path.isfile(folder):
        root, file = dirname(folder), basename(folder)
        _, x = splitext(file)
        if x.lower() not in ext:
            return
        yield root, file

    for root, _, files in os.walk(folder):
        for file in files:
            _, x = splitext(file)
            if x.lower() not in ext:
                continue
            yield root, file


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, bytes):
            # return "... Bytes Not Dumped To Avoid Flooding Console ..."
            l = len(o)
            if len(o) > 16:
                o = o[0:16]
                return o.hex(sep=" ") + f" ... [+{l - 16} Bytes]"
            return o.hex(sep=" ")
        return super().default(o)
