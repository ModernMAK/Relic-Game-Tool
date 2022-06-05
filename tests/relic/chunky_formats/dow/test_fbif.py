from relic.chunky import GenericDataChunk, ChunkHeader, ChunkType
from relic.chunky_formats.dow.common_chunks.fbif import FbifChunk


def test_fbif():
    default = FbifChunk.default()
    packed = default.LAYOUT.struct_pack(default.plugin, default.version, default.name, default.timestamp)
    generic = GenericDataChunk(ChunkHeader(ChunkType.Data, "FBIF", FbifChunk.VERSIONS[0], len(packed), "FileBurnInfo"), packed)
    converted = FbifChunk.convert(generic)
    assert default == converted
