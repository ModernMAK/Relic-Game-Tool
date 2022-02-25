import argparse
import dataclasses
import json
import os
from enum import Enum
from json import JSONEncoder
from os import path
from os.path import splitext, join, basename
from pathlib import Path
from typing import List, Any

from relic.chunky import ChunkyMagic, RelicChunky, GenericRelicChunky, FolderChunk, AbstractChunk, GenericDataChunk
from relic.chunky.serializer import read_chunky
from relic.chunky_formats.rsh import RshChunky, write_rsh


def build_parser():
    parser = argparse.ArgumentParser(prog="Relic Chunky 2 Binary", description="Convert Relic Chunkies to binary files.")
    parser.add_argument("input_path", nargs="*", type=str, help="The file(s) or directory(s) to read from.")
    parser.add_argument("-i", "--input", type=str, nargs='*', action='append', required=False, help="Additional paths or directories to read from.")
    parser.add_argument("-o", "--output", type=str, nargs='*', help="The file or directory to write to. Will only use the last directory specified, UNLESS -m or --multi is specified.")
    parser.add_argument("-m", "--multi", action='store_true', help="Writes the n-th input to the n-th output. Must provide an equal amount of inputs and outputs. (False by default.)")
    parser.add_argument("-r", "--recursive", action='store_true', required=False, help="Recursively convert files inside directories. (False by default, directories will only convert top-level files.)")
    parser.add_argument("-e", "--error", action='store_true', required=False, help="Execution will stop on an error. (False by default.)")
    parser.add_argument("-v", "--verbose", action='store_true', required=False, help="Errors will be printed to the console. (False by default.)")
    parser.add_argument("-x", "-q", "--squelch", "--quiet", action='store_true', required=False, help="Nothing will be printed, unless -v/--verbose is specified.")
    parser.add_argument("-s", "--strict", action='store_true', required=False, help="Forces all files provided to be converted. (False by default; 'non-'Relic Chunky' files are ignored.)")
    # parser.add_argument("-u", "--unimplemented", "--unk", action="store_true", help="Only dumps chunks which are not convertable")
    return parser


class DataclassJsonEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, Enum):
            return {o.name: o.value}
        else:
            return o


def dump_data_chunk(output_file: Path, chunk: GenericDataChunk):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file.with_suffix(".bin"), "wb") as handle:
        handle.write(chunk.raw_bytes)
    with open(output_file.with_suffix(".meta"), "w") as meta:
        json.dump(chunk.header, meta, cls=DataclassJsonEncoder)


def dump_folder_chunk(output_dir: Path, chunk: FolderChunk):
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_chunk_col(output_dir, chunk.chunks)
    with open(output_dir.with_suffix(".meta"), "w") as meta:
        json.dump(chunk.header, meta, cls=DataclassJsonEncoder)


def dump_chunk_col(output_dir: Path, chunks: List[AbstractChunk]):
    for i, chunk in enumerate(chunks):
        chunk_path = output_dir / f"{chunk.header.id}-{chunk.header.type.value}-[{i}]"
        if isinstance(chunk, FolderChunk):
            dump_folder_chunk(chunk_path, chunk)
        elif isinstance(chunk, GenericDataChunk):
            dump_data_chunk(chunk_path, chunk)


def dump_chunky(output_dir: Path, chunky: GenericRelicChunky):
    dump_chunk_col(output_dir, chunky.chunks)
    with open(str(output_dir)+".meta", "w") as meta:
        json.dump(chunky.header, meta, cls=DataclassJsonEncoder)


def __convert_file(input_file: str, output_file: str, strict: bool = False, quiet: bool = False, indent: int = 0) -> bool:
    with open(input_file, "rb") as in_handle:
        if not strict and not ChunkyMagic.check_magic_word(in_handle):
            return False
        if not quiet:
            _ = '\t' * indent
            print(f"{_}Reading '{input_file}'...")
        chunky = read_chunky(in_handle)
        dump_chunky(Path(output_file), chunky)
        if not quiet:
            print(f"{_}\tWrote '{output_file}'...")
    return True


def __convert_dir(input_file: str, output_file: str, recursive: bool = False, strict: bool = False, quiet: bool = False):
    for root, folders, files in os.walk(input_file):
        if not recursive:
            folders[:] = []
        for file in files:
            src = join(root, file)
            dest = src.replace(input_file, output_file)
            __convert_file(src, dest, strict, quiet, indent=1)


def run(run_args: argparse.Namespace):
    inputs = []
    if run_args.input_path:
        inputs.extend(run_args.input_path)
    if run_args.input:
        inputs.extend(*run_args.input)
    outputs = []
    if run_args.output:
        outputs.extend(run_args.output)
    map_in2out, recursive_walk, fail_on_error, print_errors, quiet, strict = run_args.multi, run_args.recursive, run_args.error, run_args.verbose, run_args.squelch, run_args.strict
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
                    __convert_file(in_path, out_path, strict, quiet)
                else:
                    if not quiet:
                        print(f"Reading '{in_path}'...")
                __convert_dir(in_path, out_path, recursive_walk, strict, quiet)
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
                    __convert_file(in_path, out_path, strict, quiet)
                else:
                    if not quiet:
                        print(f"Reading '{in_path}'...")
                    __convert_dir(in_path, out_path, recursive_walk, strict, quiet)
            except BaseException as e:
                if fail_on_error:
                    raise
                if print_errors:
                    print("ERROR:\n\t", e)


if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()
    run(args)
