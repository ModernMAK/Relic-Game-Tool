#
# from . import common, hierarchy, writer
# # from .common import vdrive, archive, folder, file, toc
#
# # __all__ = [
# #     "common",
# #     "hierarchy",
# #     "writer",
# # ]
#
# # __all__.extend(archive.__all__)
# # __all__.extend(file.__all__)
# # __all__.extend(folder.__all__)
# # __all__.extend(toc.__all__)
# # __all__.extend(vdrive.__all__)
from relic.sga_old.v2 import APIv2
from relic.sga_old.v5 import APIv5
from relic.sga_old.v7_old import APIv7
from relic.sga_old.v9 import APIv9

__APIS = [APIv2,APIv5,APIv7,APIv9]
APIS = {api.version:api for api in __APIS}