from typing import Dict

from .convertable import ChunkyConverterFactory, ConvertableChunky
from .fda.fda import FdaChunky
from .whm.whm import WhmChunky
from .wtp.wtp import WtpChunky


def generate_chunky_converter() -> ChunkyConverterFactory[ConvertableChunky]:
    conv = ChunkyConverterFactory()
    conv['fda'] = FdaChunky
    conv['whm'] = WhmChunky
    conv['wtp'] = WtpChunky
    return conv


ChunkyConverter = generate_chunky_converter()
