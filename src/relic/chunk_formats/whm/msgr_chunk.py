from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, List

from relic.chunk_formats.whm.mslc_chunk import MslcChunk
from relic.chunk_formats.whm.shared import num_layout, _UNK_STRUCT
from relic.chunky import DataChunk, FolderChunk

_NUM = num_layout

@dataclass
class MsgrName:
    name: str
    unk_a: int
    unk_b: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MsgrName':
        buffer = stream.read(_NUM.size)
        count = _NUM.unpack(buffer)[0]
        name = stream.read(count).decode("ascii")
        buffer = stream.read(_UNK_STRUCT.size)
        unk_a, unk_b = _UNK_STRUCT.unpack(buffer)
        return MsgrName(name, unk_a, unk_b)


@dataclass
class MsgrChunk:
    parts: List[MsgrName]
    sub_meshes: List['MslcChunk']

    @classmethod
    def convert(cls, chunk: FolderChunk) -> 'MsgrChunk':
        # the id is DATA not the type (alhough it is coincidentally, a ChunkType.Data)
        data: DataChunk = chunk.get_chunk(id="DATA", recursive=False)
        with BytesIO(data.data) as stream:
            buffer = stream.read(_NUM.size)
            count = _NUM.unpack(buffer)[0]
            parts = [MsgrName.unpack(stream) for _ in range(count)]
        submeshes = [MslcChunk.create(mscl) for mscl in chunk.get_chunks(id="MSLC")]

        return MsgrChunk(parts, submeshes)
