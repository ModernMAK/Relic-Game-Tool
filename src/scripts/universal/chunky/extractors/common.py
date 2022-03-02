import argparse
import os
from os import path
from os.path import splitext, join
from typing import List, Union, Dict, Callable, Protocol

from relic.chunky import ChunkyMagic, GenericRelicChunky
from relic.chunky.serializer import read_chunky
from scripts.universal.common import print_reading, print_wrote, print_error, PrintOptions


def is_chunky(input_file: str, ext: Union[str, List[str]] = None, magic: bool = False) -> bool:
    if not ext and not magic:
        return True
    # Make sure file has extension
    if ext:
        _, x = splitext(input_file)
        x = x.lstrip(".")  # Drop '.'
        if isinstance(ext, List):
            if x not in ext:
                return False
        else:
            if x != ext:
                return False
    # Make sure magic word is present
    if magic:
        with open(input_file, "rb") as check_handle:
            return ChunkyMagic.check_magic_word(check_handle)
    return True


class ChunkyExtractor(Protocol):
    def __call__(self, output_path: str, chunky: GenericRelicChunky, **kwargs) -> float: ...  # Neat ... works as pass?


def extract_file(input_file: str, output_path: str, extractor: ChunkyExtractor, extractor_args: Dict = None, print_opts: PrintOptions = None, indent_level: int = 0, exts: Union[str, List[str]] = None, magic: bool = False):
    if not print_opts.strict:
        if not is_chunky(input_file, exts, magic):
            return
    extractor_args = extractor_args or {}
    print_reading(input_file, indent_level, print_opts)
    try:
        with open(input_file, "rb") as in_handle:
            chunky = read_chunky(in_handle)
        extractor(output_path, chunky, **extractor_args)
        print_wrote(input_file, indent_level + 1, print_opts)
    except KeyboardInterrupt:
        raise  # NEVER BLOCK KEYBOARD INTERRUPT
    except BaseException as e:
        if not print_opts or print_opts.error_fail:
            raise
        print_error(e, print_opts=print_opts, indent=indent_level + 1)


def extract_dir(input_path: str, output_path: str, extractor: ChunkyExtractor, extractor_args: Dict = None, print_opts: PrintOptions = None, recursive: bool = False, exts: Union[str, List[str]] = None, magic: bool = False):
    for root, folders, files in os.walk(input_path):
        if not recursive:
            folders[:] = []
        for file in files:
            src = join(root, file)
            dest = src.replace(input_path, output_path)
            dest = splitext(dest)[0]
            extract_file(src, dest, extractor, extractor_args=extractor_args, indent_level=1, print_opts=print_opts, exts=exts, magic=magic)


def get_runner(extractor: ChunkyExtractor, extractor_args_getter: Callable[[argparse.Namespace], Dict], exts: Union[str, List[str]] = None, magic: bool = True):
    def run_extract(run_args: argparse.Namespace):
        inputs = []
        if run_args.input_path:
            inputs.extend(run_args.input_path)
        if run_args.input:
            inputs.extend(*run_args.input)
        outputs = []
        if run_args.output:
            outputs.extend(run_args.output)

        print_opts = PrintOptions(run_args.strict, run_args.squelch, run_args.error, run_args.verbose)
        map_in2out = run_args.multi
        recursive = run_args.recursive
        extractor_args = extractor_args_getter(run_args)

        def do(i_path: str, o_path: str):
            try:
                if path.isfile(i_path):
                    extract_file(i_path, o_path, extractor, extractor_args, print_opts, exts=exts, magic=magic)
                else:
                    if not print_opts.quiet:
                        print_reading(i_path)
                    extract_dir(i_path, o_path, extractor, extractor_args, print_opts, recursive=recursive, exts=exts, magic=magic)
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                if not print_opts or print_opts.error_fail:
                    raise
                print_error(e, print_opts=print_opts)

        main_output = None
        if map_in2out:
            if len(outputs) != len(inputs):
                raise ValueError(f"Multi specified but Inputs ({len(inputs)}) and Outputs ({len(outputs)}) don't match!")
        elif len(outputs) >= 1:
            main_output = outputs[-1]
        else:
            main_output = os.path.abspath("")

        if not print_opts.quiet:
            print(f"Operating on '{len(inputs)}' files/directories, please wait...")

        if map_in2out:
            for in_path, out_path in zip(inputs, outputs):
                do(in_path, out_path)
        else:
            for in_path in inputs:
                do(in_path, main_output)

        if not print_opts.quiet:
            print(f"\tDone!")

    return run_extract
