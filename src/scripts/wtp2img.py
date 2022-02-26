import argparse
import os
from os import path
from os.path import splitext, join, basename

from relic.chunky import ChunkyMagic
from relic.chunky.chunk.header import ChunkTypeError, ChunkError
from relic.chunky.serializer import read_chunky
from relic.chunky_formats.wtp.wtp import WtpChunky
from relic.chunky_formats.wtp.writer import write_wtp


def build_parser():
    parser = argparse.ArgumentParser(prog="WTP 2 Image", description="Convert Relic WTP (Texture) files to Images.")
    parser.add_argument("input_path", nargs="*", type=str, help="The file(s) or directory(s) to read from.")
    parser.add_argument("-i", "--input", type=str, nargs='*', action='append', required=False, help="Additional paths or directories to read from.")
    parser.add_argument("-o", "--output", type=str, nargs='*', help="The file or directory to write to. Will only use the last directory specified, UNLESS -m or --multi is specified.")
    parser.add_argument("-m", "--multi", action='store_true', help="Writes the n-th input to the n-th output. Must provide an equal amount of inputs and outputs. (False by default.)")
    parser.add_argument("-r", "--recursive", action='store_true', required=False, help="Recursively convert files inside directories. (False by default, directories will only convert top-level files.)")
    parser.add_argument("-e", "--error", action='store_true', required=False, help="Execution will stop on an error. (False by default.)")
    parser.add_argument("-v", "--verbose", action='store_true', required=False, help="Errors will be printed to the console. (False by default.)")
    parser.add_argument("-x", "-q", "--squelch", "--quiet", action='store_true', required=False, help="Nothing will be printed, unless -v/--verbose is specified.")
    parser.add_argument("-s", "--strict", action='store_true', required=False, help="Forces all files provided to be converted. (False by default; both non-'.wtp' and 'non-'Relic Chunky' files are ignored.)")
    parser.add_argument("-f", "--fmt", "--format", default=None, choices=["png", "tga", "dds"], help="Choose what format to convert textures to.")
    parser.add_argument("-c", "-t", "--conv", "--converter", "--texconv", help="Path to texconv.exe to use.")
    return parser


def __convert_file(input_file: str, output_file: str, strict: bool = False, quiet: bool = False, indent: int = 0, out_format: str = None, texconv_path: str = None) -> bool:
    _, ext = splitext(input_file)
    if ext != ".wtp" and not strict:
        return False
    #
    # _, ext = splitext(output_file)
    # if out_format:
    #     ext = ext or f".{out_format}"
    # output_file = _ + ext
    # p = Path(output_file)
    with open(input_file, "rb") as in_handle:
        if not strict and not ChunkyMagic.check_magic_word(in_handle):
            return False
        if not quiet:
            _ = '\t' * indent
            print(f"{_}Reading '{input_file}'...")
        try:
            chunky = read_chunky(in_handle)
        except ChunkError:
            if strict:
                raise
            else:
                return False
        wtp = WtpChunky.convert(chunky)
        # p.parent.mkdir(exist_ok=True, parents=True)
        # if out_format is not None:
        #     x, _ = splitext(output_file)
        #     x += wtp.shrf.texture.imag.attr.img.extension
        #     output_file = ext
        # with open(output_file, "wb") as out_handle:
        write_wtp(output_file, wtp, out_format=out_format, texconv_path=texconv_path)
        if not quiet:
            print(f"{_}\tWrote '{output_file}'...")
    return True


def __convert_dir(input_file: str, output_file: str, recursive: bool = False, strict: bool = False, quiet: bool = False, out_format: str = None, texconv_path: str = None):
    for root, folders, files in os.walk(input_file):
        if not recursive:
            folders[:] = []
        for file in files:
            src = join(root, file)
            dest = src.replace(input_file, output_file)
            dest = splitext(dest)[0]
            __convert_file(src, dest, strict, quiet, indent=1, out_format=out_format, texconv_path=texconv_path)


def run(run_args: argparse.Namespace):
    inputs = []
    if run_args.input_path:
        inputs.extend(run_args.input_path)
    if run_args.input:
        inputs.extend(*run_args.input)
    outputs = []
    if run_args.output:
        outputs.extend(run_args.output)
    map_in2out, recursive_walk, fail_on_error, print_errors, quiet, strict, fmt, conv = run_args.multi, run_args.recursive, run_args.error, run_args.verbose, run_args.squelch, run_args.strict, run_args.fmt, run_args.conv
    main_output = None

    if map_in2out:
        if len(outputs) != len(inputs):
            raise ValueError(f"Multi specified but Inputs ({len(inputs)}) and Outputs ({len(outputs)}) don't match!")
    elif len(outputs) >= 1:
        main_output = outputs[-1]
    else:
        main_output = os.path.abspath("")

    if map_in2out:
        for in_path, out_path in zip(inputs, outputs):
            try:
                if path.isfile(in_path):
                    __convert_file(in_path, out_path, strict, quiet, out_format=fmt, texconv_path=conv)
                else:
                    if not quiet:
                        print(f"Reading '{in_path}'...")
                __convert_dir(in_path, out_path, recursive_walk, strict, quiet, out_format=fmt, texconv_path=conv)
            except BaseException as e:
                if fail_on_error:
                    raise
                if print_errors:
                    print("ERROR:\n\t", e)
    else:
        output_is_dir = (len(inputs) > 1)
        for in_path in inputs:
            try:
                out_path = main_output
                if path.isfile(in_path):
                    if output_is_dir:
                        out_path = join(out_path, basename(in_path))
                    __convert_file(in_path, out_path, strict, quiet,  out_format=fmt,texconv_path=conv)
                else:
                    if not quiet:
                        print(f"Reading '{in_path}'...")
                    __convert_dir(in_path, out_path, recursive_walk, strict, quiet, out_format=fmt, texconv_path=conv)
            except BaseException as e:
                if fail_on_error:
                    raise
                if print_errors:
                    print("ERROR:\n\t", e)


if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()
    run(args)