import argparse
from typing import Dict

from relic.chunky import GenericRelicChunky
from relic.chunky_formats.dow.wtp.wtp import WtpChunky
from relic.chunky_formats.dow.wtp.writer import write_wtp
from scripts.universal.chunky.extractors.common import get_runner
from scripts.universal.common import SharedExtractorParser


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-f", "--fmt", "--format", default=None, choices=["png", "tga", "dds"], type=str.lower, help="Choose what format to convert textures to.")
    parser.add_argument("-c", "-t", "--conv", "--converter", "--texconv", help="Path to texconv.exe to use.")


def build_parser():
    parser = argparse.ArgumentParser(prog="WTP 2 Image", description="Convert Relic WTP (Default Texture) files to Images.", parents=[SharedExtractorParser])
    add_args(parser)
    return parser


def extract_wtp(output_path: str, chunky: GenericRelicChunky, out_format: str, texconv_path: str) -> None:
    wtp = WtpChunky.convert(chunky)
    write_wtp(output_path, wtp, out_format=out_format, texconv_path=texconv_path)


def extract_args(args: argparse.Namespace) -> Dict:
    return {'out_format': args.fmt, 'texconv_path': args.conv}


Runner = get_runner(extract_wtp, extract_args, ["wtp"], True)

if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()
    Runner(args)
