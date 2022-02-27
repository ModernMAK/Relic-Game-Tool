import argparse

from scripts.universal.common import func_print_help
from .common import SharedSgaParser
from .unpack import Runner as UnpackSGA, add_args as add_unpack_args
ArgumentSubParser = argparse._SubParsersAction


def add_sga_sub_commands(sub_parser: ArgumentSubParser):
    dump_parser = sub_parser.add_parser("dump", help="Dumps SGA archive contents for debugging.")
    dump_parser.set_defaults(func=func_print_help(dump_parser))

    unpack_parser = sub_parser.add_parser("unpack", help="Unpacks a SGA archive for later repacking.", parents=[SharedSgaParser])
    add_unpack_args(unpack_parser)
    unpack_parser.set_defaults(func=UnpackSGA)

    repack_parser = sub_parser.add_parser("repack", help="Repacks an SGA archive.")
    repack_parser.set_defaults(func=func_print_help(repack_parser))

    extract_parser = sub_parser.add_parser("extract", help="Extracts assets from internal Relic Chunk assets.")
    extract_parser.set_defaults(func=func_print_help(extract_parser))


def add_sga(sub_parser: ArgumentSubParser):
    sga_parser = sub_parser.add_parser("sga", prog="sga", help="Tools for SGA archives.")
    sga_parser.set_defaults(func=func_print_help(sga_parser))

    sga_subparsers = sga_parser.add_subparsers(title="SGA Tools", help="Tools for SGA archives.")
    add_sga_sub_commands(sga_subparsers)
