# from typing import Dict, BinaryIO
#
# from relic.sga import ov2, v5, v7, v9, vX
# from relic.sga.core import Version, ArchiveABC, VersionNotSupportedError
#
# __APIS = [ov2.API, v5.API, v7.API, v9.API]
# APIS: Dict[Version, vX.APIvX] = {api.version: api for api in __APIS}
#
#
# def read_archive(stream: BinaryIO, sparse: bool = False, apis: Dict[Version, vX.APIvX] = None) -> ArchiveABC:
#     apis = APIS if apis is None else apis
#     ArchiveABC.MAGIC.read_magic_word(stream)
#     version = Version.unpack(stream)
#     try:
#         api = apis[version]
#     except KeyError:
#         raise VersionNotSupportedError(version,list(apis.keys()))
#     version.assert_version_matches(api.version)
#     return api.Archive._read(stream, sparse)
