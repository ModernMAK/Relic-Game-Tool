import argparse
from typing import Callable


def func_print_help(arg_parser: argparse.ArgumentParser, exit_code: int = 0) -> Callable[[argparse.Namespace], None]:
    def wrapper(_: argparse.Namespace):
        arg_parser.print_help()
        exit(exit_code)

    return wrapper


def func_not_implemented(arg_parser: argparse.ArgumentParser = None):
    def wrapper(_: argparse.Namespace) -> None:
        raise NotImplementedError(arg_parser.prog if arg_parser else None)
    return wrapper
