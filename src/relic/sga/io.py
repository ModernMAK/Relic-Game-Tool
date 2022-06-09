from __future__ import annotations

from typing import Dict, Type, BinaryIO

from relic.common import VersionLike
from relic.sga.vX import APIvX
from relic.sga.abc_ import ArchiveABC
from relic.sga.common import ArchiveMagicWord, ArchiveVersion
from relic.sga.protocols import ArchiveHeader, Archive


def unpack_archive_header(versions: Dict[VersionLike, Type[ArchiveHeader]], stream: BinaryIO, read_magic: bool = True) -> ArchiveHeader:
    if read_magic:
        ArchiveMagicWord.assert_magic_word(stream, True)

    version = ArchiveVersion.unpack_version(stream)
    try:
        header_class = versions[version]
    except KeyError as e:
        raise NotImplementedError(version) from e

    return header_class.unpack(stream)


def pack_archive_header(header: ArchiveHeader, stream: BinaryIO, write_magic: bool = True) -> int:
    written = 0

    if write_magic:
        written += ArchiveMagicWord.write_magic_word(stream)

    written += ArchiveVersion.pack_version(stream, header.version)
    written += header.pack(stream)
    return written


def pack_archive(archive: Archive, stream: BinaryIO, write_magic: bool = True) -> int:
    raise NotImplementedError


def unpack_archive(stream: BinaryIO, sparse: bool = True, versions: Dict[VersionLike, APIvX] = None, *, validate: bool = True) -> ArchiveABC:
    ArchiveMagicWord.assert_magic_word(stream, True)
    version = ArchiveVersion.unpack_version(stream)
    api = versions[version]
    header = api.ArchiveHeader.unpack(stream)
    if validate:
        header.validate_checksums(stream)
    return api.Archive.unpack(stream, header, sparse)  # Defer to subclass (ensures packing works as expected)


