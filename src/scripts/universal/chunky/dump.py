import argparse
import dataclasses
import json
from enum import Enum
from json import JSONEncoder
from pathlib import Path
from typing import Dict, Any, List

from relic.chunky import read # GenericRelicChunky, GenericDataChunk, FolderChunk, AbstractChunk
from relic.chunky._abc import RawDataChunk
from relic.chunky.protocols import DataChunk, FolderChunk, ChunkContainer, Chunky
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


def dump_data_chunk(output_file: Path, chunk: RawDataChunk):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file.with_suffix(".bin"), "wb") as handle:
        handle.write(chunk.data)
    with open(output_file.with_suffix(".meta"), "w") as metadata_handle:
        full_meta = {'cc':chunk.fourCC,'cc_path':chunk.fourCC_path,'type':chunk.type,'metadata':chunk.metadata}
        json.dump(full_meta, metadata_handle, cls=DataclassJsonEncoder)


def dump_folder_chunk(output_dir: Path, chunk: FolderChunk):
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_chunk_col(output_dir, chunk)
    with open(output_dir.with_suffix(".meta"), "w") as metadata_handle:
        full_meta = {'cc':chunk.fourCC,'cc_path':chunk.fourCC_path,'type':chunk.type,'metadata':chunk.metadata}
        json.dump(full_meta, metadata_handle, cls=DataclassJsonEncoder)


def dump_chunk_col(output_dir: Path, chunk_col:ChunkContainer):
    for i, fchunk in enumerate(chunk_col.folders):
        chunk_path = output_dir / f"{i}-{fchunk.type.value}-{fchunk.fourCC}"
        dump_folder_chunk(chunk_path, fchunk)
    max_i = len(chunk_col.folders)
    for j, dchunk in enumerate(chunk_col.data_chunks):
        k = j + max_i
        chunk_path = output_dir / f"{k}-{dchunk.type.value}-{dchunk.fourCC}"
        dump_data_chunk(chunk_path, dchunk)

def add_args(_: argparse.ArgumentParser):
    pass
    # parser.add_argument("-f", "--fmt", "--format", default="bin", choices=["bin"], type=str.lower, help="Choose what format to convert audio to.")
    # parser.add_argument("-c", "-t", "--conv", "--converter", "--texconv", help="Path to texconv.exe to use.")


def build_parser():
    parser = argparse.ArgumentParser(prog="Relic 2 Binary", description="Convert Relic Chunky files to Binary.", parents=[SharedExtractorParser])
    add_args(parser)
    return parser


def dump_chunky(output_path: str, chunky: Chunky) -> None:
    p = Path(output_path)
    dump_chunk_col(p, chunky)
    with open(str(p) + ".meta", "w") as metadata_handle:
        json.dump(chunky.metadata, metadata_handle, cls=DataclassJsonEncoder)


def extract_args(_: argparse.Namespace) -> Dict:
    # return {'out_format': args.fmt}
    return {}


Runner = get_runner(dump_chunky, extract_args, None, True)

if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()
    Runner(args)
