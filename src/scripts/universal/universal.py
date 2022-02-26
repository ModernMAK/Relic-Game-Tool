import argparse

from scripts.universal.chunky.chunky import add_chunky
from scripts.universal.sga.sga import add_sga

ArgumentSubParser = argparse._SubParsersAction


def add_sub_commands(sub_parsers: ArgumentSubParser):
    add_chunky(sub_parsers)
    add_sga(sub_parsers)


def create_parser():
    relic_parser = argparse.ArgumentParser()

    relic_subparsers = relic_parser.add_subparsers(description="Tools for relic files and archives.")
    add_sub_commands(relic_subparsers)

    return relic_parser


Parser = create_parser()

if __name__ == "__main__":
    args = ["chunky", "dump", "-h"]
    r = Parser.parse_args(args)
    if r.func:
        r.func(r)
    else:
        raise NotImplementedError(args)
