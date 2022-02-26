import argparse
from scripts.universal.chunky.extractors.extractor import add_extractor
from scripts.universal.common import func_print_help
from scripts.universal.chunky.dump import Runner as ExtractChunkyBin
from scripts.universal.chunky.extractors.common import SharedExtractorParser
ArgumentSubParser = argparse._SubParsersAction


def add_chunky_sub_commands(sub_parser: ArgumentSubParser):
    dumper_parser = sub_parser.add_parser("dump", help="Dumps Relic Chunky file contents for debugging.", parents=[SharedExtractorParser])
    dumper_parser.set_defaults(func=ExtractChunkyBin)

    unpacker_parser = sub_parser.add_parser("unpack", help="Unpacks a Relic Chunky for later repacking.")
    unpacker_parser.set_defaults(func=func_print_help(unpacker_parser))

    repacker_parser = sub_parser.add_parser("repack", help="Repacks a Relic Chunky.")
    repacker_parser.set_defaults(func=func_print_help(repacker_parser))

    add_extractor(sub_parser)


def add_chunky(sub_parser: ArgumentSubParser):
    chunky_parser = sub_parser.add_parser("chunky", prog="chunky", help="Tools for Chunky files.")
    chunky_parser.set_defaults(func=func_print_help(chunky_parser))

    chunky_subparsers = chunky_parser.add_subparsers(title="Chunky Tools", help="Tools for Chunky files.")
    add_chunky_sub_commands(chunky_subparsers)
