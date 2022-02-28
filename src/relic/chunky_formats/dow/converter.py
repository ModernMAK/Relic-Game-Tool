from ..convertable import ChunkyConverterFactory
from ..protocols import ConvertableChunky
from .events import EventsChunky
from .fda.chunky import FdaChunky
from .rgd import RgdChunky
from .rml import RmlChunky
from .rsh import RshChunky
from .rtx import RtxChunky
from .sgb import SgbChunky
from .sgm.sgm import SgmChunky
from .tmp import TmpChunky
from .whe import WheChunky
from .whm.whm import WhmChunky
from .wtp.wtp import WtpChunky


def add_chunky_converter(conv: ChunkyConverterFactory) -> ChunkyConverterFactory[ConvertableChunky]:
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


def generate_chunky_converter() -> ChunkyConverterFactory[ConvertableChunky]:
    conv = ChunkyConverterFactory()
    add_chunky_converter(conv)
    return conv


ChunkyConverter = generate_chunky_converter()
