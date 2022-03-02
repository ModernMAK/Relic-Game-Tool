import argparse
from dataclasses import dataclass
from typing import Callable


def build_shared_extractor_parser():
    parser = argparse.ArgumentParser(description="Shared extractor arguments. This should never be seen.", add_help=False)
    parser.add_argument("input_path", nargs="*", type=str, help="The file(s) or directory(s) to read from.")
    parser.add_argument("-i", "--input", type=str, nargs='*', action='append', required=False, help="Additional paths or directories to read from.")
    parser.add_argument("-o", "--output", type=str, nargs='*', help="The file or directory to write to. Will only use the last directory specified, UNLESS -m or --multi is specified.")
    parser.add_argument("-m", "--multi", action='store_true', help="Writes the n-th input to the n-th output. Must provide an equal amount of inputs and outputs. (False by default.)")
    parser.add_argument("-r", "--recursive", action='store_true', required=False, help="Recursively convert files inside directories. (False by default, directories will only convert top-level files.)")
    parser.add_argument("-e", "--error", action='store_true', required=False, help="Execution will stop on an error.")
    parser.add_argument("-v", "--verbose", action='store_true', required=False, help="Errors will be printed to the console.")
    parser.add_argument("-x", "-q", "--squelch", "--quiet", action='store_true', required=False, help="Nothing will be printed, unless -v/--verbose is specified.")
    parser.add_argument("-s", "--strict", action='store_true', required=False, help="Forces all files provided to be converted, no filtering on extension/magic words will be done.")
    return parser


SharedExtractorParser = build_shared_extractor_parser()


@dataclass
class PrintOptions:
    strict: bool = False
    quiet: bool = False
    error_fail: bool = True
    verbose: bool = False


def print_any(f: str, indent: int = 0, print_opts: PrintOptions = None):
    if not print_opts or not print_opts.quiet:
        indent = '\t' * indent
        print(f"{indent}{f}")


def print_reading(f: str, indent: int = 0, print_opts: PrintOptions = None):
    if not print_opts or not print_opts.quiet:
        indent = '\t' * indent
        print(f"{indent}Reading \"{f}\"...")


def print_wrote(f: str, indent: int = 0, print_opts: PrintOptions = None):
    if not print_opts or not print_opts.quiet:
        indent = '\t' * indent
        print(f"{indent}Wrote \"{f}\"...")


def print_error(e: BaseException, indent: int = 0, print_opts: PrintOptions = None):
    if not print_opts or not print_opts.quiet or print_opts.verbose:
        indent = '\t' * indent
        print(f"{indent}ERROR \"{e}\"...")


def func_print_help(arg_parser: argparse.ArgumentParser, exit_code: int = 0) -> Callable[[argparse.Namespace], None]:
    def wrapper(_: argparse.Namespace):
        arg_parser.print_help()
        exit(exit_code)

    return wrapper


def func_not_implemented(arg_parser: argparse.ArgumentParser = None):
    def wrapper(_: argparse.Namespace) -> None:
        raise NotImplementedError(arg_parser.prog if arg_parser else None)

    return wrapper
