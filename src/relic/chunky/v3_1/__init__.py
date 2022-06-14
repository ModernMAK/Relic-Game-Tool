from relic.chunky import _abc, protocols
from relic.chunky.v3_1._serializer import api_serializer
from relic.chunky.v3_1.core import Chunky, DataChunk, ChunkMeta, RawChunky, ChunkyMetadata, FolderChunk, version


def _create_api():
    return _abc.API(version, Chunky, FolderChunk, DataChunk, ChunkyMetadata, ChunkMeta, api_serializer)


API: protocols.API[Chunky, FolderChunk, DataChunk, ChunkyMetadata, ChunkMeta] = _create_api()
