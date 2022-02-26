import argparse
from typing import Dict

from relic.chunky import GenericRelicChunky
from relic.chunky_formats.whm.whm import WhmChunky
from relic.chunky_formats.whm.obj_writer import write_whm as write_whm_obj
from relic.chunky_formats.whm.json_writer import write_whm as write_whm_json
from scripts.universal.chunky.extractors.common import SharedExtractorParser, get_runner


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-f", "--fmt", "--format", default="obj", choices=["obj", "json", "raw"], type=str.lower,  help="Choose what format to convert models to.")
    # parser.add_argument("-c", "-t", "--conv", "--converter", "--texconv", help="Path to texconv.exe to use.")


def build_parser():
    parser = argparse.ArgumentParser(prog="WHM 2 Mesh", description="Convert Relic WHM files to Meshes.", parents=SharedExtractorParser)
    add_args(parser)
    return parser


def extract_whm(output_path: str, chunky: GenericRelicChunky, out_format: str) -> None:
    whm = WhmChunky.convert(chunky)
    if out_format == "obj":
        write_whm_obj(output_path, whm)
    elif out_format == "json":
        with open(output_path, "w") as in_handle:
            write_whm_json(in_handle, whm)
    else:
        raise NotImplementedError(out_format)


def extract_args(args: argparse.Namespace) -> Dict:
    return {'out_format': args.fmt}
    # return {'out_format': args.fmt, 'texconv_path': args.conv}


Runner = get_runner(extract_whm, extract_args, ["whm"], True)

if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()
    Runner(args)
