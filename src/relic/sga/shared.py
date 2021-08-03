from typing import BinaryIO


ARCHIVE_HEADER_OFFSET = 180


def read_name(stream: BinaryIO, info: 'ArchiveInfo', name_offset: int) -> str:
    temp = stream.tell()
    stream.seek(info.sub_header.toc_offset + info.table_of_contents.filenames_info.offset_relative + name_offset)
    s = read_until_terminal(stream)
    stream.seek(temp, 0)
    return s


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
