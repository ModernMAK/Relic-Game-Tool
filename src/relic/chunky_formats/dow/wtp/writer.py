from pathlib import Path
from typing import BinaryIO

from relic.chunky_formats.dow.wtp.wtp import WtpChunky, WtpInfoChunk, PtldChunk
from relic.file_formats.dxt import build_dow_tga_gray_header


def create_mask_image(stream: BinaryIO, data: bytes, info: WtpInfoChunk):
    header = build_dow_tga_gray_header(info.width, info.height)
    stream.write(header)
    stream.write(data)


def write_ptld(root: str, chunk: PtldChunk, info: WtpInfoChunk, out_format: str = None, texconv_path: str = None):
    path = root + "/" + chunk.layer.name + ".tga"
    with open(path, "wb") as handle:
        create_mask_image(handle, chunk.image, info)


#
# def write_ptbn(root: str, chunk: PtbdChunk, info: WtpInfoChunk, out_format: str = None, texconv_path: str = None):
#     path = root + "/" + "Banner" + (".tga" if not out_format else "." + out_format)
#     with open(path, "wb") as handle:
#         if out_format:
#             with BytesIO() as temp:
#                 create_mask_image(temp, chunk., info)
#                 ImagConverter.ConvertStream(temp, handle, out_format=out_format, texconv_path=texconv_path)
#         else:
#             create_mask_image(handle, chunk, info)


def write_wtp(output_path: str, wtp: WtpChunky, out_format: str = None, texconv_path: str = None):
    p = Path(output_path)
    p.mkdir(parents=True, exist_ok=True)
    for ptld in wtp.tpat.ptld:
        write_ptld(str(p), ptld, wtp.tpat.info, out_format=out_format, texconv_path=texconv_path)
    # write_ptbn(str(p),wtp.tpat.ptbd,wtp.tpat.info,out_format=out_format,texconv_path=texconv_path)
