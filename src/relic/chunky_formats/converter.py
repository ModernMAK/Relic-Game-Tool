from .convertable import ChunkyConverterFactory, ConvertableChunky
from .events import EventsChunky
from .fda.chunky import FdaChunky
from .rgd import RgdChunky
from .rml import RmlChunky
from .rsh import RshChunky
from .rtx import RtxChunky
from .sgb import SgbChunky
from .sgm import SgmChunky
from .tmp import TmpChunky
from .whe import WheChunky
from .whm.whm import WhmChunky
from .wtp.wtp import WtpChunky


def generate_chunky_converter() -> ChunkyConverterFactory[ConvertableChunky]:
    conv = ChunkyConverterFactory()
    conv['fda'] = FdaChunky
    conv['whm'] = WhmChunky
    conv['wtp'] = WtpChunky
    conv['rtx'] = RtxChunky
    conv['rsh'] = RshChunky
    conv['rgd'] = RgdChunky
    conv['rml'] = RmlChunky
    conv['events'] = EventsChunky
    conv['tmp'] = TmpChunky
    conv['sgb'] = SgbChunky
    conv['sgm'] = SgmChunky
    conv['whe'] = WheChunky
    return conv


ChunkyConverter = generate_chunky_converter()
