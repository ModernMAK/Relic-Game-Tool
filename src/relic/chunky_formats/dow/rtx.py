from __future__ import annotations
from dataclasses import dataclass
from os.path import basename, splitext
from pathlib import Path

from relic.chunky.chunk import ChunkType
from relic.chunky.chunky import RelicChunky, GenericRelicChunky
from relic.chunky_formats.dow.common_chunks.imag import TxtrChunk
from relic.chunky_formats.dow.common_chunks.imag_writer import ImagConverter
from relic.chunky_formats.util import find_chunk


@dataclass
class RtxChunky(RelicChunky):
    txtr: TxtrChunk

    @classmethod
    def convert(cls, chunky: GenericRelicChunky) -> RtxChunky:
        txtr = find_chunk(chunky.chunks, "TXTR", ChunkType.Folder)
        txtr = TxtrChunk.convert(txtr)
        assert len(chunky.chunks) == 1
        return RtxChunky(chunky.header, txtr)


def write_rtx(output_path: str, rtx: RtxChunky, out_format: str = None, texconv_path: str = None):
    p = Path(output_path).parent
    p.mkdir(parents=True, exist_ok=True)
    name = basename(rtx.txtr.header.name)
    name, x = splitext(name)
    if out_format:
        x = "." + out_format if (out_format[0] != ".") else out_format
    elif not x:
        x = rtx.txtr.imag.attr.image_format.extension
    name += x
    with open(p / name, "wb") as handle:
        ImagConverter.Imag2Stream(rtx.txtr.imag, handle, out_format, texconv_path=texconv_path)
