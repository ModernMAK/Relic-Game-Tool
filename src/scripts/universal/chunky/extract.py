import argparse

from scripts.universal.chunky.extractors.fda import Runner as ExtractFDA, add_args as add_fda_args
from scripts.universal.chunky.extractors.rsh import Runner as ExtractRSH, add_args as add_rsh_args
from scripts.universal.chunky.extractors.rtx import Runner as ExtractRTX, add_args as add_rtx_args
from scripts.universal.chunky.extractors.whm import Runner as ExtractWHM, add_args as add_whm_args
from scripts.universal.chunky.extractors.wtp import Runner as ExtractWTP, add_args as add_wtp_args
from scripts.universal.chunky.extractors.model import Runner as ExtractMODEL, add_args as add_model_args
from scripts.universal.common import func_print_help, SharedExtractorParser

ArgumentSubParser = argparse._SubParsersAction


def add_extract_sub_commands(sub_parser: ArgumentSubParser):
    fda_parser = sub_parser.add_parser("fda", help="Extracts FDA (Audio) Chunky files.", parents=[SharedExtractorParser])
    add_fda_args(fda_parser)
    fda_parser.set_defaults(func=ExtractFDA)

    whm_parser = sub_parser.add_parser("whm", help="Extracts WHM (Model) Chunky files.", parents=[SharedExtractorParser])
    add_whm_args(whm_parser)
    whm_parser.set_defaults(func=ExtractWHM)

    wtp_parser = sub_parser.add_parser("wtp", help="Extracts WTP (Team Textures) Chunky files.", parents=[SharedExtractorParser])
    add_wtp_args(wtp_parser)
    wtp_parser.set_defaults(func=ExtractWTP)

    rtx_parser = sub_parser.add_parser("rtx", help="Extracts RTX (Default Textures) Chunky files.", parents=[SharedExtractorParser])
    add_rtx_args(rtx_parser)
    rtx_parser.set_defaults(func=ExtractRTX)

    rsh_parser = sub_parser.add_parser("rsh", help="Extracts RSH (Campaign Textures) Chunky files.", parents=[SharedExtractorParser])
    add_rsh_args(rsh_parser)
    rsh_parser.set_defaults(func=ExtractRSH)

    model_parser = sub_parser.add_parser("model", help="Extracts MODEL Chunky files.", parents=[SharedExtractorParser])
    add_model_args(model_parser)
    model_parser.set_defaults(func=ExtractMODEL)


def add_extract(sub_parser: ArgumentSubParser):
    extractor_parser = sub_parser.add_parser("extract", help="Extracts Relic Chunky assets.")
    extractor_parser.set_defaults(func=func_print_help(extractor_parser))
    sub_parser = extractor_parser.add_subparsers(title="Extractors", help="Extractors for Chunky files.")
    add_extract_sub_commands(sub_parser)
