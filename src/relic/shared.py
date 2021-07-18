import json
from dataclasses import dataclass, is_dataclass, asdict
from os.path import splitext, join
from struct import Struct
from typing import Tuple, List, BinaryIO, Iterable, Any


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

    # Pass in the os.walk() generator
    # Root and Folders will remain unchanged
    # Files will be replaced with files starting with the proper magic word
    def walk(self, walk: Iterable[WALK_RESULT]) -> Iterable[WALK_RESULT]:
        for root, _, files in walk:
            chunky_files = [file for file in files if self.check_file(join(root, file))]
            yield root, _, chunky_files


# Appends '.' if necessary and lowers the extension case
def fix_ext_list(exts: List[str]) -> List[str]:
    return [(f".{x.lower()}" if x[0] != "." else x.lower()) for x in exts]


def has_ext(path: str, exts: List[str]) -> bool:
    _, ext = splitext(path)
    return ext.lower() in exts


# Pass in the os.walk() generator
# Root and Folders will remain unchanged
# Files will be filtered to match the given extensions
def walk_ext(walk: Iterable[WALK_RESULT], whitelist: List[str] = None, blacklist: List[str] = None) -> Iterable[WALK_RESULT]:
    def validate_path(p: str) -> bool:
        if blacklist and has_ext(p, blacklist):
            return False
        if whitelist and not has_ext(p, whitelist):
            return False
        return True

    for root, _, files in walk:
        valid_files = [f for f in files if validate_path(f)]
        yield root, _, valid_files


def get_stream_size(stream: BinaryIO) -> int:
    origin = stream.tell()
    stream.seek(0, 2)
    terminal = stream.tell()
    stream.seek(origin, 0)
    return terminal

#
# def fix_exts(ext: Union[str, List[str]]) -> List[str]:
#     if isinstance(ext, str):
#         ext = [ext]
#
#     ext = [x.lower() for x in ext]
#     ext = [f".{x}" if x[0] != '.' else x for x in ext]
#     return ext


# def walk_ext(folder: str, ext: Union[str, List[str]]) -> Tuple[str, str]:
#     ext = fix_exts(ext)
#     if os.path.isfile(folder):
#         root, file = dirname(folder), basename(folder)
#         _, x = splitext(file)
#         if x.lower() not in ext:
#             return
#         yield root, file
#
#     for root, _, files in os.walk(folder):
#         for file in files:
#             _, x = splitext(file)
#             if x.lower() not in ext:
#                 continue
#             yield root, file


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
