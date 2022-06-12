from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, List, Dict, Optional, Callable, Tuple, Iterable

from serialization_tools.structx import Struct

from relic.sga import _abc
from relic.sga._abc import DriveDef, FolderDef, FileDefABC as FileDef, _FileLazyInfo, FileDefABC
from relic.sga.protocols import TFileMetadata, IOContainer, StreamSerializer, T, TFile, TDrive


@dataclass
class TocHeader:
    drive_info: Tuple[int, int]
    folder_info: Tuple[int, int]
    file_info: Tuple[int, int]
    name_info: Tuple[int, int]


class TocHeaderSerializer(StreamSerializer[TocHeader]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> TocHeader:
        drive_pos, drive_count, folder_pos, folder_count, file_pos, file_count, name_pos, name_count = self.layout.unpack_stream(stream)
        return TocHeader((drive_pos, drive_count), (folder_pos, folder_count), (file_pos, file_count), (name_pos, name_count))

    def pack(self, stream: BinaryIO, value: TocHeader) -> int:
        args = value.drive_info[0], value.drive_info[1], value.folder_info[0], value.folder_info[1], value.file_info[0], value.file_info[1], value.name_info[0], value.name_info[1]
        return self.layout.pack_stream(stream, *args)


class DriveDefSerializer(StreamSerializer[DriveDef]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> DriveDef:
        alias: bytes
        name: bytes
        alias, name, folder_start, folder_end, file_start, file_end, root_folder = self.layout.unpack_stream(stream)
        alias: str = alias.rstrip(b"\0").decode("ascii")
        name: str = name.rstrip(b"\0").decode("ascii")
        folder_range = (folder_start, folder_end)
        file_range = (file_start, file_end)
        return DriveDef(alias=alias, name=name, root_folder=root_folder, folder_range=folder_range, file_range=file_range)

    def pack(self, stream: BinaryIO, value: DriveDef) -> int:
        alias: bytes = value.alias.encode("ascii")
        name: bytes = value.name.encode("ascii")
        args = alias, name, value.folder_range[0], value.folder_range[1], value.file_range[0], value.file_range[1], value.root_folder
        return self.layout.pack_stream(stream, *args)


class FolderDefSerializer(StreamSerializer[FolderDef]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> FolderDef:
        name_pos, folder_start, folder_end, file_start, file_end = self.layout.unpack_stream(stream)
        folder_range = (folder_start, folder_end)
        file_range = (file_start, file_end)
        return FolderDef(name_pos=name_pos, folder_range=folder_range, file_range=file_range)

    def pack(self, stream: BinaryIO, value: FolderDef) -> int:
        args = value.name_pos, value.folder_range[0], value.folder_range[1], value.file_range[0], value.file_range[1]
        return self.layout.pack_stream(stream, *args)


def _assemble_io_from_defs(drive_defs: List[DriveDef], folder_defs: List[FolderDef], file_defs: List[FileDef], names: Dict[int, str], data_pos: int, stream: BinaryIO, build_file_meta: Optional[Callable[[FileDef], TFileMetadata]] = None) -> Tuple[List[_abc.Drive], List[_abc.File]]:
    all_files: List[TFile] = []
    drives: List[TDrive] = []
    for drive_def in drive_defs:
        local_folder_defs = folder_defs[drive_def.folder_range[0]:drive_def.folder_range[1]]
        local_file_defs = file_defs[drive_def.file_range[0]:drive_def.file_range[1]]

        files: List[TFile] = []
        for file_def in local_file_defs:
            name = names[file_def.name_pos]
            metadata = build_file_meta(file_def) if build_file_meta is not None else None
            lazy_info = _FileLazyInfo(data_pos + file_def.data_pos, file_def.length_in_archive, file_def.length_on_disk, stream)
            file = _abc.File(name, None, file_def.storage_type, metadata, None, lazy_info)
            files.append(file)

        folders: List[_abc.Folder] = []
        for folder_def in local_folder_defs:
            folder_name = names[folder_def.name_pos]
            sub_files = files[folder_def.file_range[0]:folder_def.folder_range[1]]
            folder = _abc.Folder(folder_name, [], sub_files, None)
            folders.append(folder)

        for folder_def, folder in zip(local_folder_defs, folders):
            folder.sub_folders = folders[folder_def.folder_range[0]:folder_def.folder_range[1]]

        for folder in folders:
            _apply_self_as_parent(folder)
        root_folder = drive_def.root_folder - drive_def.folder_range[0]  # make root folder relative to our folder slice
        drive_folder = folders[root_folder]
        drive = _abc.Drive(drive_def.alias, drive_def.name, drive_folder.sub_folders, drive_folder.files)
        _apply_self_as_parent(drive)
        all_files.extend(files)
        drives.append(drive)
    return drives, all_files


def _apply_self_as_parent(collection: IOContainer):
    for folder in collection.sub_folders:
        folder.parent = collection
    for file in collection.files:
        file.parent = collection


def _unpack_helper(stream: BinaryIO, toc_info: Tuple[int, int], header_pos: int, serializer: StreamSerializer[T]) -> List[T]:
    stream.seek(header_pos + toc_info[0])
    return [serializer.unpack(stream) for _ in range(toc_info[1])]


def _read_toc_definitions(stream: BinaryIO, toc: TocHeader, header_pos: int, drive_serializer: StreamSerializer[DriveDef], folder_serializer: StreamSerializer[FolderDef], file_serializer: StreamSerializer[FileDefABC]):
    drives = _unpack_helper(stream, toc.drive_info, header_pos, drive_serializer)
    folders = _unpack_helper(stream, toc.folder_info, header_pos, folder_serializer)
    files = _unpack_helper(stream, toc.file_info, header_pos, file_serializer)
    return drives, folders, files


def _read_toc_names_as_count(stream: BinaryIO, toc_info: Tuple[int, int], header_pos: int, buffer_size: int = 256) -> Dict[int, str]:
    stream.seek(header_pos + toc_info[0])

    names: Dict[int, str] = {}
    running_buffer = bytearray()
    offset = 0
    while len(names) < toc_info[1]:
        buffer = stream.read(buffer_size)
        if len(buffer) == 0:
            raise Exception("Ran out of data!")  # TODO, proper exception
        terminal_null = buffer[-1] == b"\0"
        parts = buffer.split(b"\0")
        if len(parts) > 1:
            parts[0] = running_buffer + parts[0]
            running_buffer.clear()
            if not terminal_null:
                running_buffer.extend(parts[-1])
                parts = parts[:-1]
        else:
            if not terminal_null:
                running_buffer.extend(parts[0])
                offset += len(buffer)
                continue

        remaining = toc_info[1] - len(names)
        available = min(len(parts), remaining)
        for _ in range(available):
            name = parts[_]
            names[offset] = name.decode("ascii")
            offset += len(name) + 1
    return names


def _read_toc_names_as_size(stream: BinaryIO, toc_info: Tuple[int, int], header_pos: int) -> Dict[int, str]:
    stream.seek(header_pos + toc_info[0])
    name_buffer = stream.read(toc_info[1])
    parts = name_buffer.split(b"\0")
    names: Dict[int, str] = {}
    offset = 0
    for part in parts:
        names[offset] = part.decode("ascii")
        offset += len(part) + 1
    return names


def _chunked_read(stream: BinaryIO, size: Optional[int] = None, chunk_size: Optional[int] = None) -> Iterable[bytes]:
    if size is None and chunk_size is None:
        yield stream.read()
    elif size is None and chunk_size is not None:
        while True:
            buffer = stream.read(chunk_size)
            yield buffer
            if len(buffer) != chunk_size:
                break
    elif size is not None and chunk_size is None:
        yield stream.read(size)
    else:
        chunks = size // chunk_size
        for _ in range(chunks):
            yield stream.read(chunk_size)
        total_read = chunk_size * chunks
        if total_read < size:
            yield stream.read(size - total_read)
