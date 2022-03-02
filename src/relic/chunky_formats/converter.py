from .convertable import ChunkyConverterFactory
from .dow.converter import add_chunky_converter as add_dow_chunky_converter
from .dow2.converter import add_chunky_converter as add_dow2_chunky_converter
from .protocols import ConvertableChunky


def add_chunky_converter(conv: ChunkyConverterFactory) -> ChunkyConverterFactory[ConvertableChunky]:
    add_dow_chunky_converter(conv)
    add_dow2_chunky_converter(conv)
    return conv


def generate_chunky_converter() -> ChunkyConverterFactory[ConvertableChunky]:
    conv = ChunkyConverterFactory()
    add_chunky_converter(conv)
    return conv


ChunkyConverter = generate_chunky_converter()
