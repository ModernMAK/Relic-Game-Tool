import argparse
import dataclasses
import json
from enum import Enum
from json import JSONEncoder
from pathlib import Path
from typing import Dict, Any, List

from relic.chunky import GenericRelicChunky, GenericDataChunk, FolderChunk, AbstractChunk
from scripts.universal.chunky.extractors.common import get_runner
from scripts.universal.common import SharedExtractorParser


class DataclassJsonEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, Enum):
            return {o.name: o.value}
        else:
            return super().default(o)


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
        chunk_path = output_dir / f"{i}-{chunk.header.type.value[0]}-{chunk.header.id}"
        if isinstance(chunk, FolderChunk):
            dump_folder_chunk(chunk_path, chunk)
        elif isinstance(chunk, GenericDataChunk):
            dump_data_chunk(chunk_path, chunk)
        else:
            raise NotImplementedError(chunk)


def add_args(_: argparse.ArgumentParser):
    pass
    # parser.add_argument("-f", "--fmt", "--format", default="bin", choices=["bin"], type=str.lower, help="Choose what format to convert audio to.")
    # parser.add_argument("-c", "-t", "--conv", "--converter", "--texconv", help="Path to texconv.exe to use.")


def build_parser():
    parser = argparse.ArgumentParser(prog="Relic 2 Binary", description="Convert Relic Chunky files to Binary.", parents=[SharedExtractorParser])
    add_args(parser)
    return parser


def dump_chunky(output_path: str, chunky: GenericRelicChunky) -> None:
    p = Path(output_path)
    dump_chunk_col(p, chunky.chunks)
    with open(str(p) + ".meta", "w") as meta:
        json.dump(chunky.header, meta, cls=DataclassJsonEncoder)


def extract_args(_: argparse.Namespace) -> Dict:
    # return {'out_format': args.fmt}
    return {}


Runner = get_runner(dump_chunky, extract_args, None, True)

if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()
    Runner(args)
