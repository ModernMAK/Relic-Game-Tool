import zlib

from relic.chunky import RelicChunky, DataChunk, ChunkHeader, ChunkType, FolderChunk, RelicChunkyHeader
from relic.chunky.version import ChunkyVersion
from tests.helpers import lorem_ipsum


def build_sample_chunky_v1_1() -> RelicChunky:
    EXD = "EXD "
    EXDC = "EXDC"
    EXDF = "EXDF"

    lorem_ipsum_data = lorem_ipsum.encode("ascii")
    lorem_ipsum_compressed = zlib.compress(lorem_ipsum_data)

    uncomp_header = ChunkHeader(ChunkType.Data, EXD, 1, len(lorem_ipsum_data), "Lorem Ipsum")
    lorem_ipsum_uncomp = DataChunk(uncomp_header, lorem_ipsum_data)
    comp_header = ChunkHeader(ChunkType.Data, EXDC, 1, len(lorem_ipsum_compressed), "Lorem Ipsum Compressed")
    lorem_ipsum_comp = DataChunk(comp_header, lorem_ipsum_compressed)
    folder_header = ChunkHeader(ChunkType.Folder, EXDF, 1, 0, "Lorem Ipsum Test Data") # size wil be fixed when writing, and is ignored in assetions
    folder = FolderChunk([lorem_ipsum_uncomp,lorem_ipsum_comp],folder_header)

    chunky_header = RelicChunkyHeader.default(version=ChunkyVersion.v1_1.value)
    chunky = RelicChunky([folder],chunky_header)
    return chunky
