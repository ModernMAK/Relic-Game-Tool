import argparse
import sys
from typing import List

from scripts.universal.chunky.chunky import add_chunky
from scripts.universal.sga.sga import add_sga
from scripts.universal.common import func_print_help

ArgumentSubParser = argparse._SubParsersAction


def add_sub_commands(sub_parsers: ArgumentSubParser):
    add_chunky(sub_parsers)
    add_sga(sub_parsers)


def create_parser():
    relic_parser = argparse.ArgumentParser(prog="relic", description="Master tool for performing operations on Relic Chunkies and SGA archives.")
    relic_parser.set_defaults(func=func_print_help(relic_parser))
    relic_subparsers = relic_parser.add_subparsers(description="Tools for relic files and archives.", help="Tools for relic files and archives.")
    add_sub_commands(relic_subparsers)

    return relic_parser


Parser = create_parser()


def main(args: List = None):
    args = args or sys.argv[1:]
    r = Parser.parse_args(args)
    if hasattr(r, 'func') and r.func:
        r.func(r)
    else:
        raise NotImplementedError("An entry point for the command was not supplied!")


if __name__ == "__main__":
    main()

