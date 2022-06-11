from __future__ import annotations

from hashlib import md5
from typing import BinaryIO

from serialization_tools.ioutil import Ptr, StreamPtr, iter_read, WindowPtr
from serialization_tools.size import KiB


def gen_md5_checksum(stream: BinaryIO, eigen: bytes, buffer_size: int = 64 * KiB, ptr: Ptr = None) -> bytes:
    hasher = md5(eigen) if eigen else md5()
    ptr = ptr or StreamPtr(stream)  # Quick way to preserve stream integrity
    with ptr.stream_jump_to(stream) as handle:
        for buffer in iter_read(handle, buffer_size):
            hasher.update(buffer)
    return bytes.fromhex(hasher.hexdigest())


def validate_md5_checksum(stream: BinaryIO, ptr: WindowPtr, eigen: bytes, expected: bytes, buffer_size: int = KiB * 64, _assert: bool = True) -> bool:
    result = gen_md5_checksum(stream, eigen, buffer_size, ptr=ptr)
    if _assert:
        assert expected == result, (expected, result)
        return True
    else:
        return expected == result
