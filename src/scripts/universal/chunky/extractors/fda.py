import argparse
from typing import Dict

from relic.chunky import GenericRelicChunky
from relic.chunky_formats.dow.fda.chunky import FdaChunky
from relic.chunky_formats.dow.fda.audio_converter import FdaAudioConverter
from scripts.universal.chunky.extractors.common import get_runner
from scripts.universal.common import SharedExtractorParser


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-f", "--fmt", "--format", default="wav", choices=["aiff", "wav"], type=str.lower, help="The desired output format.")
    # parser.add_argument("-c", "-t", "--conv", "--converter", "--texconv", help="Path to texconv.exe to use.")


def build_parser():
    parser = argparse.ArgumentParser(prog="FDA 2 Audio", description="Convert Relic FDA (Audio) files to Wave/Aiffc-r.", parents=SharedExtractorParser)
    add_args(parser)
    return parser


def extract_fda(output_path: str, chunky: GenericRelicChunky, out_format: str) -> None:
    fda = FdaChunky.convert(chunky)
    with open(output_path, "wb") as output_handle:
        if out_format == "aiff":
            FdaAudioConverter.Fda2Aiffr(fda, output_handle)
        elif out_format == "wav":
            FdaAudioConverter.Fda2Wav(fda, output_handle)
        else:
            raise NotImplementedError(out_format)


def extract_args(args: argparse.Namespace) -> Dict:
    return {'out_format': args.fmt}


Runner = get_runner(extract_fda, extract_args, ["fda"], True)

if __name__ == "__main__":
    p = build_parser()
    args = p.parse_args()
    Runner(args)
