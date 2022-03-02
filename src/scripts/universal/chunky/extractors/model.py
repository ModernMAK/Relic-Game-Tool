import argparse
from pathlib import Path
from typing import Dict

from relic.chunky import GenericRelicChunky
from relic.chunky_formats.dow2.model.obj_writer import write_model as write_model_obj
from relic.chunky_formats.dow2.model.json_writer import write_model as write_model_json
from relic.chunky_formats.dow2.model.model import ModelChunky
from scripts.universal.chunky.extractors.common import get_runner
from scripts.universal.common import SharedExtractorParser


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-f", "--fmt", "--format", default="obj", choices=["obj", "json", "raw"], type=str.lower, help="Choose what format to convert models to.")
    # parser.add_argument("-c", "-t", "--conv", "--converter", "--texconv", help="Path to texconv.exe to use.")


def build_parser():
    parser = argparse.ArgumentParser(prog="MODEL 2 Mesh", description="Convert Relic Model files to Meshes.", parents=[SharedExtractorParser])
    add_args(parser)
    return parser


def extract_model(output_path: str, chunky: GenericRelicChunky, out_format: str) -> None:
    p = Path(output_path)
    model = ModelChunky.convert(chunky)
    if out_format == "obj":
        p.parent.mkdir(parents=True, exist_ok=True)
        write_model_obj(output_path, model)
    elif out_format == "json":
        with open(output_path + ".meshdata.json", "w") as in_handle:
            write_model_json(in_handle, model)
    else:
        raise NotImplementedError(out_format)


def extract_args(args: argparse.Namespace) -> Dict:
    return {'out_format': args.fmt}
    # return {'out_format': args.fmt, 'texconv_path': args.conv}


Runner = get_runner(extract_model, extract_args, ["model"], True)

if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()
    Runner(args)
