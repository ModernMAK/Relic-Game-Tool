import dataclasses
import json
import struct
from dataclasses import dataclass
from os.path import join
from typing import BinaryIO, List, Optional

__HEADER = "_ARCHIVE"
# STOLEN FROM http://wiki.xentax.com/index.php/Dawn_Of_War_SGA
# While i trust this is probably right, I dont believe the info on EG was 100% perfect (adimttedly it was info for sniper elite, but same format)

# HEADER CONSTS
_MAGIC_FMT = "< 8s"
_MAGIC_WORD = "_ARCHIVE"
_MAGIC_STRUCT = struct.Struct(_MAGIC_FMT)

_VERSION_FMT = "< L"
_UNK_A_FMT = "< 4L"
_NAME_FMT = "< 128s"
_UNK_B_FMT = "< 4L"
_FILE_DATA_OFFSET_FMT = "< L L"  # 1st L + 180
_OFFSET_FOLDER_SECTION_FMT = "< L H"  # L + 180

_FULL_FMT = "< " + (_MAGIC_FMT + _VERSION_FMT +
                    _UNK_A_FMT + _NAME_FMT + _UNK_B_FMT +
                    _FILE_DATA_OFFSET_FMT +
                    _OFFSET_FOLDER_SECTION_FMT +
                    _OFFSET_FOLDER_SECTION_FMT +
                    _OFFSET_FOLDER_SECTION_FMT +
                    _OFFSET_FOLDER_SECTION_FMT).replace("<", "")
_FULL_STRUCT = struct.Struct(_FULL_FMT)
_HEADER_OFFSET = 180  # Ours includes the 24 for the OFFSET_FOLDER_SECTION and _FILE_DATA_OFFSET


@dataclass
class Header:
    magic: str
    version: int

    unk_a1: int
    unk_a2: int
    unk_a3: int
    unk_a4: int

    name: str

    unk_b1: int
    unk_b2: int
    unk_b3: int
    unk_b4: int

    file_data_offset_relative: int
    file_data_offset_absolute: int

    desc_dir_offset_relative: int
    desc_count: int

    folder_dir_offset_relative: int
    folder_count: int

    file_dir_offset_relative: int
    file_count: int

    filename_dir_offset_relative: int
    filename_count: int

    @staticmethod
    def check_magic(stream: BinaryIO, peek: bool = True) -> bool:
        buffer = stream.read(_MAGIC_STRUCT.size)  # Cache result
        if peek:  # Peek mode, dont advance stream
            stream.seek(-_MAGIC_STRUCT.size, 1)  # Seek to original position
        result = _MAGIC_STRUCT.unpack(buffer)[0].decode("ascii")  # Decode bytes to string
        return result == _MAGIC_WORD  # ASSERT MAGIC WORD!

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'Header':
        if validate and not cls.check_magic(stream):
            raise Exception()
        buffer = stream.read(_FULL_STRUCT.size)
        args = _FULL_STRUCT.unpack(buffer)
        archive = Header(*args)
        # Cleanup ~ decode bytes to strings
        archive.magic = archive.magic.decode("ascii")
        # This is a fixed buffer, so we trim the trailing terminals
        archive.name = archive.name.decode("utf-16-le").rstrip("\x00")
        # DONE
        return archive


# DESCRIPTION CONSTS
_DESC_DIR_STRUCT = struct.Struct("< 64s 64s H L L")
_FOLDER_DIR_STRUCT = struct.Struct("< L H H H H")
_FOLDER_NO_SUBS = 36

_FILES_DIR_STRUCT = struct.Struct("< L L L L L")

# _FILENAME_DIR_STRUCT = Exception("_FILENAME_DIR_STRUCT is N/A") X + 1 terminal

_FILEDATA_STRUCT = struct.Struct("< 235s Q")  # + X


def read_until_terminal(stream: BinaryIO, chunk_size: int = 512) -> str:
    start = stream.tell()
    while True:
        b = stream.read(chunk_size)
        if b == "":
            raise EOFError()
        try:
            index = b.index(0x00)  # +1 to include \00
            stream.seek(start)
            return stream.read(index).decode("ascii")
        except ValueError:
            continue


def read_name(stream: BinaryIO, origin: int, dir_offset: int, name_offset: int) -> str:
    return read_until_terminal(stream, origin + dir_offset + name_offset)


@dataclass
class Description:
    category: str
    name: str
    unk_a1: int
    unk_a2: int
    unk_a3: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Description':
        buffer = stream.read(_DESC_DIR_STRUCT.size)
        args = _DESC_DIR_STRUCT.unpack(buffer)
        desc = Description(*args)
        # Cleanup ~ decode bytes to strings
        desc.category = desc.category.decode("ascii").rstrip("\x00")
        # This is a fixed buffer, so we trim the trailing terminals
        desc.name = desc.name.decode("ascii").rstrip("\x00")
        # DONE
        return desc


@dataclass
class Folder:
    name_offset: int
    first_sub: int
    last_sub: int
    first_filename: int
    last_filename: int
    name: Optional[str] = None

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Folder':
        buffer = stream.read(_FOLDER_DIR_STRUCT.size)
        args = _FOLDER_DIR_STRUCT.unpack(buffer)
        info = Folder(*args)
        return info

    def read_name(self, stream: BinaryIO, origin: int, header: Header):
        self.name = read_name(stream, origin, header.folder_dir_offset_relative, self.name_offset)


@dataclass
class File:
    name_offset: int
    unk_a: int
    file_offset: int
    decompressed_size: int
    compressed_size: int

    name: Optional[str] = None
    data: Optional[bytes] = None

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'File':
        buffer = stream.read(_FILES_DIR_STRUCT.size)
        args = _FILES_DIR_STRUCT.unpack(buffer)
        info = File(*args)
        return info

    def read_name(self, stream: BinaryIO, origin: int, header: Header):
        self.name = read_name(stream, origin, header.file_dir_offset_relative, self.name_offset)

    def read_data(self, stream: BinaryIO, origin: int, header: Header):
        stream.seek(origin + header.file_data_offset_relative + self.file_offset)
        self.data = stream.read(self.compressed_size)


@dataclass
class SGArchive:
    header: Header
    descriptions: List[Description]
    folders: List[Folder]
    files: List[File]

    @staticmethod
    def check_magic(stream: BinaryIO, peek: bool = True) -> bool:
        return Header.check_magic(stream, peek)

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'SGArchive':
        origin = stream.tell()
        header = Header.unpack(stream, validate)

        stream.seek(origin + header.desc_dir_offset_relative + _HEADER_OFFSET)
        descriptions = [Description.unpack(stream) for _ in range(header.desc_count)]

        stream.seek(origin + header.folder_dir_offset_relative + _HEADER_OFFSET)
        folders = [Folder.unpack(stream) for _ in range(header.folder_count)]

        stream.seek(origin + header.file_dir_offset_relative + _HEADER_OFFSET)
        files = [File.unpack(stream) for _ in range(header.file_count)]

        for f in folders:
            f.read_name(stream, origin, header)
        for f in files:
            f.read_name(stream, origin, header)
            f.read_data(stream, origin, header)

        return SGArchive(header, descriptions, folders, files)


if __name__ == "__main__":
    class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            if isinstance(o,bytes):
                return o.hex(sep=" ")
            return super().default(o)

    root = r"G:\Clients\Steam\Launcher\steamapps\common"
    game = r"Dawn of War Soulstorm\W40k"
    files = [
        "Locale\English\W40kDataKeys.sga",
        "W40kData-Sound-Low.sga"
    ]

    for file in files:
        full = join(root, game, file)
        with open(full, "rb") as handle:
            archive = SGArchive.unpack(handle)
            print(full)
            print("\t", archive)
            print("\t", json.dumps(archive, indent=4, cls=EnhancedJSONEncoder))
