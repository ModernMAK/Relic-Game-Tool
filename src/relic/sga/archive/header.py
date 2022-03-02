from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from typing import BinaryIO, Dict, Type, Tuple

from serialization_tools.ioutil import WindowPtr, Ptr, iter_read, StreamPtr
from serialization_tools.magic import MagicWordIO
from serialization_tools.size import KiB
from serialization_tools.structx import Struct

from ..common import ArchiveVersion
from ...common import VersionLike

ArchiveMagicWord = MagicWordIO(Struct("< 8s"), "_ARCHIVE".encode("ascii"))

_NAME_CHAR_COUNT = 64  # 64 characters max
_NAME_CHAR_SIZE = 2  # UTF-16-le ~ 2 bytes per character
_NAME_BYTE_SIZE = _NAME_CHAR_COUNT * _NAME_CHAR_SIZE


@dataclass
class ArchiveHeader:
    name: str

    toc_ptr: Ptr
    data_ptr: WindowPtr

    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True) -> bool:
        """
        Validates header checksums against the content's of the stream.

        The stream should return to its original position when it was passed in.

        :param stream: The binary stream to read from
        :param fast: When true, slow checksums may be skipped
        :param _assert: When true, an assertion is raised instead of returning False
        :returns: True if all checksums match (or the type does not have checksums to validate)
        :raises AssertionError: if a checksum does not match and _assert is True
        """
        raise NotImplementedError

    @property
    def version(self) -> VersionLike:
        raise NotImplementedError

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> 'ArchiveHeader':
        raise NotImplementedError

    def _pack(self, stream: BinaryIO) -> int:
        raise NotImplementedError

    @classmethod
    def unpack(cls, stream: BinaryIO, read_magic: bool = True) -> 'ArchiveHeader':
        # TODO move read_magic and unpack out of unpack
        if read_magic:
            ArchiveMagicWord.assert_magic_word(stream, True)

        version = ArchiveVersion.unpack_version(stream)
        header_class = _HEADER_VERSION_MAP.get(version)

        if not header_class:
            raise NotImplementedError(version)

        return header_class._unpack(stream)

    def pack(self, stream: BinaryIO, write_magic: bool = True) -> int:
        written = 0

        if write_magic:
            written += ArchiveMagicWord.write_magic_word(stream)

        written += ArchiveVersion.pack_version(stream, self.version)
        written += self._pack(stream)
        return written


def _gen_md5_checksum(stream: BinaryIO, eigen: bytes, buffer_size: int = 64 * KiB, ptr: Ptr = None):
    hasher = md5(eigen) if eigen else md5()
    ptr = ptr or StreamPtr(stream)  # Quick way to preserve stream integrity
    with ptr.stream_jump_to(stream) as handle:
        for buffer in iter_read(handle, buffer_size):
            hasher.update(buffer)
    return hasher.hexdigest()


def _validate_md5_checksum(stream: BinaryIO, ptr: WindowPtr, eigen: bytes, expected: bytes, buffer_size: int = 1024 * 64, _assert: bool = True) -> bool:
    result = _gen_md5_checksum(stream, eigen, buffer_size, ptr=ptr)
    if _assert:
        assert expected == result, (expected, result)
        return True
    else:
        return expected == result


@dataclass
class DowIArchiveHeader(ArchiveHeader):
    # hash, name, hash (repeated), TOC_SIZE, DATA_OFFSET
    LAYOUT = Struct(f"< 16s {_NAME_BYTE_SIZE}s 16s 2L")
    # The eigen value is a guid? also knew that layout looked familiar
    MD5_EIGENVALUES = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))
    toc_ptr: WindowPtr
    checksums: Tuple[bytes, bytes]

    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True):
        ptrs = [Ptr(self.toc_ptr.offset), self.toc_ptr]
        valid = True
        indexes = (1,) if fast else (0, 1)
        for i in indexes:
            valid &= _validate_md5_checksum(stream, ptrs[i], self.MD5_EIGENVALUES[i], self.checksums[i], _assert=_assert)
        return valid

    @property
    def version(self) -> VersionLike:
        return ArchiveVersion.Dow

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> 'DowIArchiveHeader':
        csum_a, name, csum_b, toc_size, data_offset = cls.LAYOUT.unpack_stream(stream)
        csum_a, csum_b = csum_a.hex(), csum_b.hex()

        name = name.decode("utf-16-le").rstrip("\0")
        toc_ptr = WindowPtr(offset=stream.tell(), size=toc_size)

        data_ptr = WindowPtr(offset=data_offset, size=None)

        return cls(name, toc_ptr, data_ptr, (csum_a, csum_b))

    def _pack(self, stream: BinaryIO) -> int:
        args = self.checksums[0], self.name, self.checksums[1]
        return self.LAYOUT.pack_stream(stream, *args)


@dataclass
class DowIIArchiveHeader(ArchiveHeader):
    # hash, name, hash (repeated), TOC_SIZE, DATA_OFFSET, TOC_POS, RESERVED:1, RESERVED:0?, UNK???
    LAYOUT = Struct(f"< 16s {_NAME_BYTE_SIZE}s 16s 3L 3L")
    # Copied from DowI, may be different; praying it isn't
    # UGH THIER DIFFERENT! Or the way to calculate them is different
    # First, let's try no eigen # (None, None)  # HAH TROLLED MYSELF, forgot to conert checksum to hex
    MD5_EIGENVALUES = ("E01519D6-2DB7-4640-AF54-0A23319C56C3".encode("ascii"), "DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF".encode("ascii"))
    toc_ptr: WindowPtr
    checksums: Tuple[bytes, bytes]
    unk: int

    # This may not mirror DowI one-to-one, until it's verified, it stays here
    # noinspection DuplicatedCode
    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True):
        # return True
        ptrs = [Ptr(self.toc_ptr.offset), self.toc_ptr]
        valid = True
        indexes = (1,) if fast else (0, 1)
        for i in indexes:
            valid &= _validate_md5_checksum(stream, ptrs[i], self.MD5_EIGENVALUES[i], self.checksums[i], _assert=_assert)
        return valid

    @property
    def version(self) -> VersionLike:
        return ArchiveVersion.Dow2

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> 'DowIIArchiveHeader':
        csum_a, name, csum_b, toc_size, data_offset, toc_pos, rsv_1, rsv_0, unk = cls.LAYOUT.unpack_stream(stream)
        csum_a, csum_b = csum_a.hex(), csum_b.hex()

        assert rsv_1 == 1
        assert rsv_0 == 0

        name = name.decode("utf-16-le").rstrip("\0")
        toc_ptr = WindowPtr(offset=toc_pos, size=toc_size)
        data_ptr = WindowPtr(offset=data_offset)

        return cls(name, toc_ptr, data_ptr, (csum_a, csum_b), unk)

    def _pack(self, stream: BinaryIO) -> int:
        args = self.checksums[0], self.name, self.checksums[1], self.toc_ptr.size, self.data_ptr.offset, self.toc_ptr.offset, 1, 0, self.unk
        return self.LAYOUT.pack_stream(stream, *args)


@dataclass
class DowIIIArchiveHeader(ArchiveHeader):
    # name, TOC_POS, TOC_SIZE, DATA_POS, DATA_SIZE, RESERVED:0?, RESERVED:1, RESERVED:0?, UNK???
    LAYOUT = Struct(f"<{_NAME_BYTE_SIZE}s Q L Q 4L 256s")
    toc_ptr: WindowPtr
    data_ptr: WindowPtr

    unk: bytes

    def validate_checksums(self, stream: BinaryIO, *, fast: bool = True, _assert: bool = True) -> bool:
        """
        Dawn of War III does not contain any checksums, and so will always return true.

        :param stream: Ignored
        :param fast: Ignored
        :param _assert: Ignored
        :returns: True
        """
        return True

    @property
    def version(self) -> VersionLike:
        return ArchiveVersion.Dow2

    @classmethod
    def _unpack(cls, stream: BinaryIO) -> ArchiveHeader:
        name, toc_pos, toc_size, data_pos, data_size, rsv_0_a, rsv_1, rsv_0_b, unk = cls.LAYOUT.unpack_stream(stream)[0]

        assert rsv_1 == 1
        assert rsv_0_a == 0
        assert rsv_0_b == 0

        toc_ptr = WindowPtr(offset=toc_pos, size=toc_size)
        data_ptr = WindowPtr(offset=data_pos, size=data_size)
        name = name.decode("utf-16-le").rstrip("\0")

        return cls(name, toc_ptr, data_ptr, unk)

    def _pack(self, stream: BinaryIO) -> int:
        args = (self.name, self.toc_ptr.offset, self.toc_ptr.size, self.data_ptr.offset, self.data_ptr.size, 0, 1, self.unk)
        return self.LAYOUT.pack_stream(stream, *args)


_HEADER_VERSION_MAP: Dict[VersionLike, Type[ArchiveHeader]] = {
    ArchiveVersion.Dow: DowIArchiveHeader,
    ArchiveVersion.Dow2: DowIIArchiveHeader,
    ArchiveVersion.Dow3: DowIIIArchiveHeader
}
