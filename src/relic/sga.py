import json
import os
import struct
import zlib
from dataclasses import dataclass
from os.path import join
from typing import BinaryIO, List, Tuple

# THIS FILE CAN HANDLE SGA archives
# poorly implimented, I wanted to have a sparse windowable type but I didn't do that too well
from relic.shared import walk_ext, EnhancedJSONEncoder

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
_FILE_DATA_OFFSET_STRUCT = struct.Struct(_FILE_DATA_OFFSET_FMT)
_OFFSET_FOLDER_SECTION_FMT = "< L H"  # L + 180
_OFFSET_FOLDER_SECTION_STRUCT = struct.Struct(_OFFSET_FOLDER_SECTION_FMT)

_HEADER_FMT = "< " + (_MAGIC_FMT + _VERSION_FMT + _UNK_A_FMT + _NAME_FMT + _UNK_B_FMT + _FILE_DATA_OFFSET_FMT).replace(
    "<", "")
_HEADER_STRUCT = struct.Struct(_HEADER_FMT)
_HEADER_OFFSET = 180  # Ours includes the 24 for the OFFSET_FOLDER_SECTION and _FILE_DATA_OFFSET
assert _HEADER_STRUCT.size == _HEADER_OFFSET, (_HEADER_STRUCT.size, _HEADER_OFFSET)  # TODO move to tests

# DESCRIPTION CONSTS
_DESC_DIR_STRUCT = struct.Struct("< 64s 64s H L L")
_FOLDER_DIR_STRUCT = struct.Struct("< L H H H H")
_FOLDER_NO_SUBS = 36  # IDK what this means

_FILES_DIR_STRUCT = struct.Struct("< L L L L L")

# _FILENAME_DIR_STRUCT = Exception("_FILENAME_DIR_STRUCT is N/A") X + 1 terminal

_FILEDATA_STRUCT = struct.Struct("< 235s Q")  # + X


@dataclass
class SparseFixedPointer:
    start: int
    size: int

    def read(self, stream: BinaryIO) -> bytes:
        temp = stream.tell()
        stream.seek(self.start, 0)
        buffer = stream.read(self.size)
        stream.seek(temp, 0)
        return buffer


class SparseTerminatedPointer:
    start: int
    terminal: int = 0x00

    def read(self, stream: BinaryIO, scan_size: int = 1024, include_terminal: bool = True) -> bytes:
        temp = stream.tell()
        stream.seek(self.start, 0)
        while True:
            buffer = stream.read(scan_size)
            index = buffer.find(self.terminal)
            if index != -1:
                end = stream.tell() - scan_size + index
                if include_terminal:
                    end += 1
                break
        stream.seek(self.start)
        buffer = stream.read(end - self.start)
        stream.seek(temp, 0)
        return buffer


@dataclass
class DataOffsetInfo:
    offset_relative: int

    @property
    def start_relative(self):
        return self.offset_relative

    @property
    def start_abs(self):
        return self.offset_relative + _HEADER_STRUCT.size

    offset_absolute: int

    @property
    def end(self):
        return self.offset_absolute

    @property
    def size(self):
        return self.end - self.start_abs

    @property
    def valid(self) -> bool:
        return self.offset_relative + _HEADER_STRUCT.size == self.offset_absolute

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'DataOffsetInfo':
        buffer = stream.read(_FILE_DATA_OFFSET_STRUCT.size)
        args = _FILE_DATA_OFFSET_STRUCT.unpack(buffer)
        archive = DataOffsetInfo(*args)
        # DONE
        if validate and not archive.valid:
            raise Exception("Invalid Data Offset")

        return archive

    def pack(self, stream: BinaryIO) -> int:
        buffer: bytes = bytearray(_FILE_DATA_OFFSET_STRUCT.size)
        tuple = (self.offset_relative, self.offset_absolute)
        _FILE_DATA_OFFSET_STRUCT.pack_into(buffer, 0, tuple)
        return stream.write(buffer)


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

    data_info: DataOffsetInfo

    def _as_tuple(self):
        return (  # TODO, check for better way, I do this manually to preserve order, but dataclass may already do this
            self.magic, self.version,
            self.unk_a1, self.unk_a2, self.unk_a3, self.unk_a4,
            self.name,
            self.unk_b1, self.unk_b2, self.unk_b3, self.unk_b4
        )

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
        buffer = stream.read(_HEADER_STRUCT.size)
        args = _HEADER_STRUCT.unpack(buffer)
        data_info_args = args[-2:]
        header_args = list(args[:-1])  # we reuse the -2 index
        header_args[-1] = DataOffsetInfo(*data_info_args)  # the -2 index is now -1 because of the previous -1
        archive = Header(*header_args)
        # Cleanup ~ decode bytes to strings
        archive.magic = archive.magic.decode("ascii")
        # This is a fixed buffer, so we trim the trailing terminals
        archive.name = archive.name.decode("utf-16-le").rstrip("\x00")
        # DONE
        return archive

    def pack(self, stream: BinaryIO) -> int:
        buffer: bytes = bytearray(_HEADER_STRUCT.size)
        _HEADER_STRUCT.pack_into(buffer, 0, self._as_tuple())
        return stream.write(buffer)


@dataclass
class FlatHeader:
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

    @classmethod
    def from_header(cls, header: Header):
        args = (
            header.version,
            header.unk_a1, header.unk_a2, header.unk_a3, header.unk_a4,
            header.name,
            header.unk_b1, header.unk_b2, header.unk_b3, header.unk_b4
        )
        return FlatHeader(*args)


@dataclass
class OffsetInfo:
    offset_relative: int
    count: int

    @property
    def offset_absolute(self) -> int:
        return _HEADER_STRUCT.size + self.offset_relative

    @offset_absolute.setter
    def offset_absolute(self, abs_offset: int):
        self.offset_relative = abs_offset - _HEADER_STRUCT.size

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'OffsetInfo':
        buffer = stream.read(_OFFSET_FOLDER_SECTION_STRUCT.size)
        args = _OFFSET_FOLDER_SECTION_STRUCT.unpack(buffer)
        archive = OffsetInfo(*args)
        # DONE
        return archive

    def pack(self, stream: BinaryIO) -> int:
        buffer: bytes = bytearray(_OFFSET_FOLDER_SECTION_STRUCT.size)
        tuple = (self.offset_relative, self.count)
        _OFFSET_FOLDER_SECTION_STRUCT.pack_into(buffer, 0, tuple)
        return stream.write(buffer)


@dataclass
class ArchiveInfo:
    header: Header
    # file_data_info: DataOffsetInfo
    descriptions_info: OffsetInfo
    folders_info: OffsetInfo
    files_info: OffsetInfo
    filenames_info: OffsetInfo

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True) -> 'ArchiveInfo':
        header = Header.unpack(stream, validate)
        # file_data = DataOffsetInfo.unpack(stream, validate)
        descriptions_info = OffsetInfo.unpack(stream)
        folders_info = OffsetInfo.unpack(stream)
        files_info = OffsetInfo.unpack(stream)
        filenames_info = OffsetInfo.unpack(stream)
        args = (header,
                # file_data,
                descriptions_info, folders_info, files_info, filenames_info)
        return ArchiveInfo(*args)


def read_until_terminal(stream: BinaryIO, chunk_size: int = 512, strip_terminal: bool = True) -> str:
    start = stream.tell()
    prev = start
    while True:
        b = stream.read(chunk_size)
        now = stream.tell()
        if prev == now:
            raise EOFError()
        prev = now
        try:
            index = b.index(0x00) + 1  # +1 to include \00
            stream.seek(start)
            s = stream.read(index).decode("ascii")
            if strip_terminal:
                s = s.rstrip("\x00")
            return s
        except ValueError:
            continue


def read_name(stream: BinaryIO, offset: OffsetInfo, name_offset: int) -> str:
    temp = stream.tell()
    stream.seek(offset.offset_absolute + name_offset)
    s = read_until_terminal(stream)
    stream.seek(temp, 0)
    return s


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

    def pack(self, stream: BinaryIO) -> int:
        buffer: bytes = bytearray(_DESC_DIR_STRUCT.size)
        tuple = (self.category, self.name, self.unk_a1, self.unk_a2, self.unk_a3)
        _DESC_DIR_STRUCT.pack_into(buffer, 0, tuple)
        return stream.write(buffer)


@dataclass
class SparseFolder:
    name_offset: int
    first_sub: int
    last_sub: int
    first_filename: int
    last_filename: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'SparseFolder':
        buffer = stream.read(_FOLDER_DIR_STRUCT.size)
        args = _FOLDER_DIR_STRUCT.unpack(buffer)
        info = SparseFolder(*args)
        return info

    def read_name(self, stream: BinaryIO, offset: OffsetInfo) -> str:
        return read_name(stream, offset, self.name_offset)


@dataclass
class SparseFile:
    name_offset: int
    unk_a: int
    file_offset: int
    decompressed_size: int
    compressed_size: int

    @property
    def compressed(self):
        return self.decompressed_size != self.compressed_size

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'SparseFile':
        buffer = stream.read(_FILES_DIR_STRUCT.size)
        args = _FILES_DIR_STRUCT.unpack(buffer)
        info = SparseFile(*args)
        return info

    def read_name(self, stream: BinaryIO, offset: OffsetInfo) -> str:
        return read_name(stream, offset, self.name_offset)

    def read_data(self, stream: BinaryIO, offset: DataOffsetInfo) -> bytes:
        stream.seek(offset.offset_absolute + self.file_offset)
        return stream.read(self.compressed_size)


@dataclass
class File:
    info: SparseFile
    name: str
    data: bytes
    _folder: 'Folder' = None

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: SparseFile) -> 'File':
        name = info.read_name(stream, archive_info.filenames_info)
        data = info.read_data(stream, archive_info.header.data_info)
        args = (info, name, data)
        return File(*args)

    def decompress(self) -> bytes:
        if self.info.compressed:
            return zlib.decompress(self.data)
        else:
            return self.data


@dataclass
class FlatFile:
    unk_a: int
    name: str
    data: bytes


@dataclass
class Folder:
    _info: SparseFolder
    name: str
    folders: List['Folder']
    files: List[File]
    _folder: 'Folder' = None

    # def walk_folders(self, parent: str = None, include_self:bool=False) -> Tuple[str, str, File]:
    #     if parent is None:
    #         parent = ""
    #
    #     if include_self:
    #         f_name = self.name
    #         yield parent, f_name, self
    #         parent = join(parent, f_name)
    #
    #     for folder in self.folders:
    #         f_name = folder.name
    #         yield parent, f_name, folder
    #         parent = join(parent, f_name)
    #         for pair in folder.walk_folders(parent):
    #             yield pair
    #
    # def walk_files(self, parent: str = None) -> Tuple[str, str, File]:
    #     if parent is None:
    #         parent = ""
    #     for file in self.files:
    #         yield parent, file.name, file
    #
    # def walk_all_files(self, parent: str = None) -> Tuple[str, str, File]:
    #     for p, _, f in self.walk_folders(parent, include_self=True):
    #         for pair in f.walk_files(p):
    #             yield pair

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo, info: SparseFolder) -> 'Folder':
        name = info.read_name(stream, archive_info.filenames_info)
        folders = [None] * (info.last_sub - info.first_sub)
        files = [None] * (info.last_filename - info.first_filename)
        args = (info, name, folders, files)
        return Folder(*args)

    def load_folders(self, folders: List['Folder']):
        if self._info.first_sub < len(folders):
            for i in range(self._info.first_sub, self._info.last_sub):
                i_0 = i - self._info.first_sub
                self.folders[i_0] = folders[i]
                if self == folders[i]:
                    raise Exception("Cyclic Folder!")
                if folders[i]._folder is not None:
                    raise Exception("File matches multiple folders!")
                folders[i]._folder = self

    def load_files(self, files: List['File']):
        if self._info.first_filename < len(files):
            for i in range(self._info.first_filename, self._info.last_filename):
                i_0 = i - self._info.first_filename
                self.files[i_0] = files[i]
                if files[i]._folder is not None:
                    raise Exception("File matches multiple folders!")
                files[i]._folder = self


@dataclass
class SparseArchive:
    info: ArchiveInfo
    descriptions: List[Description]
    folders: List[SparseFolder]
    files: List[SparseFile]

    # names: List[str]

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True):
        info = ArchiveInfo.unpack(stream, validate)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive_info: ArchiveInfo) -> 'SparseArchive':
        info = archive_info
        descriptions: List[Description] = [None] * info.descriptions_info.count

        stream.seek(info.descriptions_info.offset_absolute, 0)
        for i in range(info.descriptions_info.count):
            descriptions[i] = Description.unpack(stream)

        stream.seek(info.folders_info.offset_absolute, 0)
        folders: List[SparseFolder] = [None] * info.folders_info.count
        for j in range(info.folders_info.count):
            folders[j] = SparseFolder.unpack(stream)

        stream.seek(info.files_info.offset_absolute, 0)
        files: List[SparseFile] = [None] * info.files_info.count
        for k in range(info.files_info.count):
            files[k] = SparseFile.unpack(stream)

        # stream.seek(info.filenames_info.offset_absolute, 0)
        # names: List[str] = [None] * info.filenames_info.count
        # for k in range(info.filenames_info.count):
        #     names[k] = read_until_terminal(stream)

        return SparseArchive(info, descriptions, folders, files
                             # , names
                             )


@dataclass
class FullArchive:
    info: ArchiveInfo
    descriptions: List[Description]
    folders: List[Folder]
    files: List[File]

    # names: List[str]

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = True):
        info = SparseArchive.unpack(stream, validate)
        return cls.create(stream, info)

    @classmethod
    def create(cls, stream: BinaryIO, archive: SparseArchive) -> 'FullArchive':
        info = archive.info
        desc = archive.descriptions
        folders = [Folder.create(stream, info, f) for f in archive.folders]
        files = [File.create(stream, info, f) for f in archive.files]
        for f in folders:
            f.load_folders(folders)
            f.load_files(files)

        folders = [f for f in folders if f._folder is None]
        files = [f for f in files if f._folder is None]

        # for f in folders:
        #     del f._info
        #     del f._child
        # for f in files:
        #     del f._loose

        # names = archive.names

        return FullArchive(info, desc, folders                           , files
                           )


@dataclass
class FlatArchive:
    info: FlatHeader
    descriptions: List[Description]
    files: List[FlatFile]

    # names: List[str]

    @classmethod
    def unpack(cls, stream: BinaryIO, validate: bool = False) -> 'FlatArchive':
        archive = FullArchive.unpack(stream, validate)
        return cls.create(archive)

    @classmethod
    def create(cls, archive: FullArchive) -> 'FlatArchive':
        def walk_archive(folder: Folder) -> Tuple[str, str, File]:
            for f in folder.files:
                yield folder.name, f.name, f
            for f in folder.folders:
                for p in walk_archive(f):
                    yield p

        files = []
        for folder in archive.folders:
            # for full_name, f in walk(folder):
            for p, n, f in walk_archive(folder):
                # for p, n, f in folder.walk_all_files():
                full_name = join(p, n)
                decomp = f.decompress()
                n_f = FlatFile(f.info.unk_a, full_name, decomp)
                files.append(n_f)

        info = FlatHeader.from_header(archive.info.header)
        return FlatArchive(info, archive.descriptions, files)


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


# def walk_ext(folder: str, ext: str) -> Tuple[str, str]:
#     ext = ext.lower()
#     for root, _, files in os.walk(folder):
#         for file in files:
#             _, x = splitext(file)
#             if x.lower() != ext:
#                 continue
#             yield root, file


def shared_dump(file: str, out_dir: str = None, verbose: bool = False):
    out_dir = out_dir or "gen/sga/shared_dump"
    with open(file, "rb") as handle:
        archive = FlatArchive.unpack(handle)
        for f in archive.files:
            shared_path = join(out_dir, f.name)
            dir_path = os.path.dirname(shared_path)
            try:
                os.makedirs(dir_path)
            except FileExistsError:
                pass
            if verbose:
                print("\t", shared_path)
            with open(shared_path, "wb") as writer:
                writer.write(f.data)


def run():
    root = r"G:\Clients\Steam\Launcher\steamapps\common"
    game = r"Dawn of War Soulstorm\W40k"
    files = [
        r"Locale\English\W40kDataKeys.sga",
        r"Locale\English\W40kDataLoc.sga",
        r"Locale\English\W40kData-Sound-Speech.sga",

        "W40kData-Sound-Low.sga",
        "W40kData-Sound-Med.sga",
        "W40kData-Sound-Full.sga",

        "W40kData-Whm-Low.sga",
        "W40kData-Whm-Medium.sga",
        "W40kData-Whm-High.sga",

        "W40kData.sga",

        "W40kData-SharedTextures-Full.sga",
    ]
    root = "gen/sga/"
    shared_dump = root + "shared_dump"
    single_dump = root + "dump"
    meta_dump = root + "meta"

    for i, file in enumerate(files):
        full = join(root, game, file)
        print(full)
        print("\tUnpacking...")
        with open(full, "rb") as handle:
            # archive = SGArchive.unpack(handle)
            archive = FlatArchive.unpack(handle)
            # print("\t", archive)
            meta = json.dumps(archive, indent=4, cls=EnhancedJSONEncoder)
            print("\t\t", meta)

            print("\tWriting Assets...")
            for f in archive.files:
                shared_path = join(shared_dump, f.name)
                dir_path = os.path.dirname(shared_path)
                try:
                    os.makedirs(dir_path)
                except FileExistsError:
                    pass
                with open(shared_path, "wb") as writer:
                    writer.write(f.data)

                own_path = join(single_dump, file, f.name)
                dir_path = os.path.dirname(own_path)
                try:
                    os.makedirs(dir_path)
                except FileExistsError:
                    pass
                with open(own_path, "wb") as writer:
                    writer.write(f.data)

            print("\tWriting Meta...")
            meta_path = join(meta_dump, file + ".json")
            dir_path = os.path.dirname(meta_path)
            try:
                os.makedirs(dir_path)
            except FileExistsError:
                pass
            with open(meta_path, "w") as writer:
                writer.write(meta)


def dump_all_sga(folder: str, out_dir: str = None, blacklist: List[str] = None, verbose: bool = False):
    blacklist = blacklist or []
    for root, file in walk_ext(folder, ".sga"):
        full = join(root, file)

        skip = False
        for word in blacklist:
            if word in full:
                skip = True
                break

        if skip:
            continue
        if verbose:
            print(full)
        shared_dump(full, out_dir, verbose)


if __name__ == "__main__":
    dump_all_sga(r"D:\Steam\steamapps\common\Dawn of War Soulstorm", blacklist=[r"-Low", "-Med"],
                 out_dir=r"D:/Dumps/DOW I/sga", verbose=True)
