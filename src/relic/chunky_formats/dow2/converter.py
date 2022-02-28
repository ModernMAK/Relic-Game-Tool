from .model.model import ModelChunky
from ..convertable import ChunkyConverterFactory
from ..protocols import ConvertableChunky


def add_chunky_converter(conv: ChunkyConverterFactory) -> ChunkyConverterFactory[ConvertableChunky]:
    conv.register(ModelChunky)
    return conv


def generate_chunky_converter() -> ChunkyConverterFactory[ConvertableChunky]:
    conv = ChunkyConverterFactory()
    add_chunky_converter(conv)
    return conv


ChunkyConverter = generate_chunky_converter()
