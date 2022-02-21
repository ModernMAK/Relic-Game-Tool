from .convertable import ChunkyConverterFactory, ConvertableChunky
from .fda.fda import FdaChunky
# from .rsh import RshChunky
from .rtx import RtxChunky
from .whm.whm import WhmChunky
from .wtp.wtp import WtpChunky


def generate_chunky_converter() -> ChunkyConverterFactory[ConvertableChunky]:
    conv = ChunkyConverterFactory()
    conv['fda'] = FdaChunky
    conv['whm'] = WhmChunky
    conv['wtp'] = WtpChunky
    conv['rtx'] = RtxChunky
    # conv['rsh'] = RshChunky
    unsupported = [
        'events', 'rgd', 'rml', 'sgb', 'sgm', 'tmp', 'whe'
    ]
    return conv


ChunkyConverter = generate_chunky_converter()
