from dataclasses import dataclass
from os.path import split, splitext, join
from typing import List, BinaryIO, Tuple, Iterable

from relic.sga.archive_header import ArchiveHeader
from relic.sga.description import Description
from relic.sga.flat_file import FlatFile
from relic.sga.full_archive import FullArchive
from relic.shared import fix_exts


@dataclass
class FlatArchive:
    header: ArchiveHeader
    descriptions: List[Description]
    files: List[FlatFile]

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic:bool=True) -> 'FlatArchive':
        archive = FullArchive.unpack(stream, read_magic)
        return cls.create(archive)

    @classmethod
    def create(cls, archive: FullArchive) -> 'FlatArchive':
        files = []
        for folder in archive.folders:
            for p, n, f in folder.walk_files():
                full_name = join(p, n)
                decomp = f.decompress()
                n_f = FlatFile(f.info.unk_a, full_name, decomp)
                files.append(n_f)

        return FlatArchive(archive.info.header, archive.descriptions, files)

    def walk_files(self, exts: List[str] = None) -> Iterable[Tuple[str, str, 'File']]:
        if exts:
            exts = fix_exts(exts)

        for f in self.files:
            dirname, fname = split(f.name)
            if exts:
                _, ext = splitext(fname)
                if ext.lower() not in exts:
                    continue
            yield dirname, fname, f
