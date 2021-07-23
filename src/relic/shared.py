import json
import struct
from dataclasses import dataclass, is_dataclass, asdict
from enum import Enum
from functools import partial
from os.path import splitext, join
from struct import Struct
from typing import Tuple, List, BinaryIO, Iterable, Any, Optional, Union, Callable


def unpack_from_stream(layout: Struct, stream: BinaryIO) -> Tuple[Any, ...]:
    buffer = stream.read(layout.size)
    return layout.unpack_from(buffer)


def pack_into_stream(layout: Struct, stream: BinaryIO, *args) -> int:
    buffer = layout.pack(*args)
    return stream.write(buffer)


class MagicUtil:
    @classmethod
    def read_magic_word(cls, stream: BinaryIO, layout: Struct, advance: bool = True) -> str:
        origin = stream.tell()
        try:
            return unpack_from_stream(layout, stream)[0].decode("ascii")
        except (struct.error, UnicodeDecodeError):
            return None
        finally:
            if not advance:  # Useful for checking the header before reading it
                stream.seek(origin)

    @classmethod
    def assert_magic_word(cls, stream: BinaryIO, layout: Struct, word: str, advance: bool = True):
        magic = cls.read_magic_word(stream, layout=layout, advance=advance)
        assert magic == word, (magic, word)

    @classmethod
    def check_magic_word(cls, stream: BinaryIO, layout: Struct, word: str, advance: bool = True) -> bool:
        magic = cls.read_magic_word(stream, layout=layout, advance=advance)
        return magic == word

    @classmethod
    def write_magic_word(cls, stream: BinaryIO, layout: Struct, word: str) -> int:
        return pack_into_stream(layout, stream,
                                word.encode("ascii"))  # We could just as easily write the word directly, but we don't


@dataclass
class Magic:
    layout: Struct
    word: str

    def read_magic_word(self, stream: BinaryIO, advance: bool = True) -> str:
        return MagicUtil.read_magic_word(stream, self.layout, advance)

    def write_magic_word(self, stream: BinaryIO) -> int:
        return MagicUtil.write_magic_word(stream, self.layout, self.word)

    def assert_magic_word(self, stream: BinaryIO, advance: bool = True):
        MagicUtil.assert_magic_word(stream, self.layout, self.word, advance)

    def check_magic_word(self, stream: BinaryIO, advance: bool = False) -> bool:
        return MagicUtil.check_magic_word(stream, self.layout, self.word, advance)


WalkResult = Tuple[str, List[str], List[str]]


@dataclass
class MagicWalker:
    magic: Magic

    def check_stream(self, stream: BinaryIO, advance_stream: bool = False) -> bool:
        return self.magic.check_magic_word(stream, advance=advance_stream)

    def check_file(self, file: str) -> bool:
        with open(file, "rb") as handle:
            # we set advance to true to avoid pointlessly fixing the stream, since we are just going to close it
            return self.check_stream(handle, True)

    # Pass in the os.walk() generator
    # Root and Folders will remain unchanged
    # Files will be replaced with files starting with the proper magic word
    def walk(self, walk: Iterable[WalkResult]) -> Iterable[WalkResult]:
        for root, _, files in walk:
            chunky_files = (file for file in files if self.check_file(join(root, file)))
            yield root, _, chunky_files


# Appends '.' if necessary and lowers the extension case
def fix_ext_list(exts: List[str]) -> List[str]:
    return [(f".{x.lower()}" if x[0] != "." else x.lower()) for x in exts]


# Appends '.' if necessary and lowers the extension case

KW_LIST = Union[None, str, List[str]]
VALID_KW_LIST = Optional[List[str]]


def fix_extension_list(exts: KW_LIST) -> VALID_KW_LIST:
    if exts is None:
        return None
    if isinstance(exts, str):
        exts = [exts]
    return [(f".{x.lower()}" if x[0] != "." else x.lower()) for x in exts]


def fix_keyword_list(kws: KW_LIST) -> VALID_KW_LIST:
    if kws is None:
        return None
    if isinstance(kws, str):
        kws = [kws]
    return kws


def filter_path_by_extension(file: str, whitelist: VALID_KW_LIST = None, blacklist: VALID_KW_LIST = None) -> bool:
    """This function does not validate whitelist and blacklist; whitelist and blacklist must be a valid List[str] of '.extension_name'"""
    _, x = splitext(file)
    x = x.lower()
    if blacklist and x in blacklist:
        return False
    if whitelist:
        return x in whitelist
    return True


def filter_path_by_keyword(file: str, whitelist: VALID_KW_LIST = None, blacklist: VALID_KW_LIST = None) -> bool:
    """This function does not validate whitelist and blacklist; whitelist and blacklist must be a valid List[str] or None"""
    if blacklist:
        for word in blacklist:
            if word in file:
                return False
    if whitelist:
        if not any(word in file for word in whitelist):
            return False
    return True


def filter_walk_by_predicate(walk: Iterable[WalkResult], predicate: Callable[[str], bool]) -> Iterable[WalkResult]:
    for root, _, files in walk:
        valid_files = (f for f in files if predicate(f))
        yield root, _, valid_files


def filter_walk_by_extension(walk: Iterable[WalkResult], whitelist: KW_LIST = None, blacklist: KW_LIST = None) -> \
        Iterable[WalkResult]:
    whitelist = fix_extension_list(whitelist)
    blacklist = fix_extension_list(blacklist)
    predicate = partial(filter_path_by_extension, whitelist=whitelist, blacklist=blacklist)
    return filter_walk_by_predicate(walk, predicate)


def filter_walk_by_keyword(walk: Iterable[WalkResult], whitelist: KW_LIST = None, blacklist: KW_LIST = None) -> \
        Iterable[WalkResult]:
    whitelist = fix_keyword_list(whitelist)
    blacklist = fix_keyword_list(blacklist)
    predicate = partial(filter_path_by_keyword, whitelist=whitelist, blacklist=blacklist)
    return filter_walk_by_predicate(walk, predicate)


def collapse_walk_on_files(walk: Iterable[WalkResult]) -> Iterable[str]:
    """Makes a walk only return an iterator for the full file path."""
    for root, _, files in walk:
        for file in files:
            yield join(root, file)


def get_stream_size(stream: BinaryIO) -> int:
    origin = stream.tell()
    stream.seek(0, 2)
    terminal = stream.tell()
    stream.seek(origin, 0)
    return terminal


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        elif isinstance(o, Enum):
            return {'name': o.name, 'value': o.value}
        elif isinstance(o, bytes):
            # return "... Bytes Not Dumped To Avoid Flooding Console ..."
            l = len(o)
            if len(o) > 16:
                o = o[0:16]
                return o.hex(sep=" ") + f" ... [+{l - 16} Bytes]"
            return o.hex(sep=" ")
        else:
            return super().default(o)
